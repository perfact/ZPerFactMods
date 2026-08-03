#
# Restrict Zope's built-in XML-RPC support to trusted sources.
#
# Zope treats *any* POST request with a 'text/xml' Content-Type as an XML-RPC
# call (ZPublisher.HTTPRequest.processInputs). An empty <methodName> then makes
# the addressed object itself the published object, because the XML-RPC
# response suppresses the index_html default (ZPublisher.BaseRequest.traverse),
# and a non-callable object is returned unchanged by mapply. The XML-RPC
# marshaller dumps its public __dict__ as a struct
# (ZPublisher.xmlrpc.dump_instance), permission-checking only those attribute
# values that are ExtensionClass.Base instances. Attributes holding plain
# strings, numbers, lists or dicts are disclosed without any security check,
# which bypasses the declarative security we rely on for code and secrets kept
# in the Data.FS.
#
# We do use XML-RPC from the booking manager, so turning it off entirely via
# the 'enable-xmlrpc' directive in zope.conf is not an option. Instead we
# register an IXmlrpcChecker utility, which Zope consults for every candidate
# request, and only admit requests we recognize.
#
# Configuration is read from the environment once, while this module is being
# imported, and can be set from the <environment> section of zope.conf:
#
#     PERFACT_XMLRPC_NETWORKS   comma separated addresses/CIDRs the call may
#                               originate from, in addition to the always
#                               allowed loopback ranges
#     PERFACT_XMLRPC_PROXIES    comma separated addresses/CIDRs of the proxies
#                               whose forwarded header we believe, again in
#                               addition to the loopback ranges
#     PERFACT_XMLRPC_FORWARDED_HEADER
#                               name of that header, X-Client-IP by default
#     PERFACT_XMLRPC_PATHS      comma separated ZODB path prefixes that may be
#                               called from any source
#     PERFACT_XMLRPC_SECRET     shared secret expected in the
#                               X-PerFact-Xmlrpc header, for cluster peers
#                               whose address is not predictable
#
# Beware that the loopback ranges are trusted as proxies by default, because
# that is where our haproxy runs. A request arriving from loopback *without* the
# forwarded header is therefore treated as a local caller. This relies on
# haproxy setting the header unconditionally, which 'option forwardfor' does.
#
# Note that a refused request is not an error: Zope simply does not treat it as
# XML-RPC and publishes index_html as for any other POST. A booking manager
# pointing at the wrong host therefore receives HTML instead of an XML-RPC
# fault, so watch the log messages below when debugging.
#

import hmac
import ipaddress
import logging
import os

import zope.component
from ZODB.POSException import ConflictError
from zope.interface import implementer
from zope.publisher.http import splitport
from ZPublisher.interfaces import IXmlrpcChecker

logger = logging.getLogger("Products.ZPerFactMods.restrict_xmlrpc")

LOOPBACK = (ipaddress.ip_network("127.0.0.0/8"), ipaddress.ip_network("::1/128"))

# Number of path segments a VirtualHostBase directive occupies, namely the
# directive itself, the protocol and the host.
VIRTUAL_HOST_BASE_SEGMENTS = 3

# Header our haproxy setup uses to pass on the original client address, see
# 'option forwardfor header X-Client-IP' in haproxy.cfg. Note that we cannot
# use request.getClientAddr() to obtain the client: Zope only ever unwraps
# X-Forwarded-For (ZPublisher.HTTPRequest.HTTPRequest.__init__), so with our
# header name it always reports the proxy instead of the caller, no matter what
# the 'trusted-proxies' directive says.
DEFAULT_FORWARDED_HEADER = "X-Client-IP"


def parse_networks(spec):
    """
    Turn a comma separated list of addresses and/or CIDRs into a tuple of
    networks. Unparseable entries are logged and skipped, so a typo in
    zope.conf cannot prevent Zope from starting.
    """
    networks = []
    for raw in spec.split(","):
        entry = raw.strip()
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning("Ignoring unparseable network %r", entry)
    return tuple(networks)


def parse_paths(spec):
    """
    Turn a comma separated list of ZODB paths into a tuple of normalized
    prefixes, each starting with and not ending in a slash.
    """
    paths = []
    for raw in spec.split(","):
        entry = raw.strip().rstrip("/")
        if entry:
            paths.append(entry if entry.startswith("/") else "/" + entry)
    return tuple(paths)


def normalize_addr(addr):
    """
    Return addr as an ip_address, unwrapping IPv4-mapped IPv6 addresses so
    that '::ffff:127.0.0.1' matches a plain IPv4 network. Returns None if addr
    is not an address at all.
    """
    try:
        parsed = ipaddress.ip_address(addr)
    except ValueError:
        return None
    if isinstance(parsed, ipaddress.IPv6Address) and parsed.ipv4_mapped:
        return parsed.ipv4_mapped
    return parsed


def header_key(name):
    """
    Return the WSGI environment key a request header arrives under.
    """
    return "HTTP_" + name.upper().replace("-", "_")


def client_addr(request, proxies, environ_key):
    """
    Return the address the request really originates from, or None.

    Our haproxy connects to Zope over the loopback interface, so REMOTE_ADDR is
    useless on its own: taking it at face value would treat the entire internet
    as local. If REMOTE_ADDR is one of the proxies we know, believe the
    forwarded header instead, and pick its *last* entry that is not itself a
    proxy. haproxy appends to that header rather than replacing it, so a value
    injected by the caller ends up to the left of the address haproxy observed
    and cannot win.

    A request from a proxy without the forwarded header is one that did not
    come through the proxy, for example a call from the booking manager
    straight to the instance port, so REMOTE_ADDR is used for it.
    """
    addr = normalize_addr(request.environ.get("REMOTE_ADDR", ""))
    if addr is None:
        return None
    if not any(addr in network for network in proxies):
        return addr

    forwarded = request.environ.get(environ_key, "")
    for entry in reversed(forwarded.split(",")):
        candidate = normalize_addr(entry.strip())
        if candidate is None:
            continue
        if any(candidate in network for network in proxies):
            continue
        return candidate
    return addr


def zodb_path(path_info):
    """
    Return the ZODB path that path_info addresses, or None if it cannot be
    determined.

    We are called before traversal, so VirtualHostMonster has not rewritten
    the traversal stack yet and PATH_INFO still contains the virtual hosting
    directives. Undo them the same way
    Products.SiteAccess.VirtualHostMonster.__call__ does: strip a leading
    VirtualHostBase/<protocol>/<host>, drop VirtualHostRoot and the _vh_
    elements belonging to it, and expand '*' to the first label of the virtual
    host name. Keep this in sync with VirtualHostMonster.
    """
    segments = [segment for segment in path_info.split("/") if segment]
    host = None
    if segments[:1] == ["VirtualHostBase"]:
        if len(segments) < VIRTUAL_HOST_BASE_SEGMENTS:
            return None
        host = segments[2]
        segments = segments[VIRTUAL_HOST_BASE_SEGMENTS:]

    result = []
    for segment in segments:
        if segment == "VirtualHostRoot" or segment[:4] == "_vh_":
            continue
        if segment == "*":
            if host is None:
                return None
            result.append(splitport(host)[0].split(".")[0])
            continue
        result.append(segment)
    return "/" + "/".join(result)


class Rule:
    """
    Base class for the individual checks. A rule returns True to admit a
    request, and must not raise for untrusted input.
    """

    def __call__(self, request):
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class SourceNetworks(Rule):
    """
    Admit requests whose client address lies in one of the given networks.

    The client address is resolved by client_addr() rather than taken from
    REMOTE_ADDR, because our haproxy reaches the instances over loopback and
    would otherwise make every request look local.
    """

    def __init__(
        self,
        networks=LOOPBACK,
        proxies=LOOPBACK,
        forwarded_header=DEFAULT_FORWARDED_HEADER,
    ):
        self.networks = tuple(networks)
        self.proxies = tuple(proxies)
        self.environ_key = header_key(forwarded_header)

    def __call__(self, request):
        addr = client_addr(request, self.proxies, self.environ_key)
        if addr is None:
            return False
        return any(addr in network for network in self.networks)

    def __repr__(self):
        networks = ", ".join(str(network) for network in self.networks)
        proxies = ", ".join(str(proxy) for proxy in self.proxies)
        return f"<SourceNetworks {networks} behind {proxies}>"


class PathPrefixes(Rule):
    """
    Admit requests addressing one of the given ZODB path prefixes, regardless
    of their source.

    This guards the entry point only. The XML-RPC methodName is appended to
    PATH_INFO after we have been called, and it is not passed to us, so a call
    admitted here may traverse further down from the whitelisted object. Keep
    the prefixes as specific as possible.
    """

    def __init__(self, prefixes):
        self.prefixes = tuple(prefixes)

    def __call__(self, request):
        if not self.prefixes:
            return False
        path = zodb_path(request.environ.get("PATH_INFO", ""))
        if path is None:
            return False
        return any(
            path == prefix or path.startswith(prefix + "/") for prefix in self.prefixes
        )

    def __repr__(self):
        return f"<PathPrefixes {', '.join(self.prefixes)}>"


class SharedSecretHeader(Rule):
    """
    Admit requests carrying the expected secret in an HTTP header.

    Only sound over TLS and only for callers that cannot be impersonated by a
    browser that was tricked into sending the header. Meant as a second factor
    next to SourceNetworks, not as the only gate.
    """

    def __init__(self, secret, header="HTTP_X_PERFACT_XMLRPC"):
        self.secret = secret
        self.header = header

    def __call__(self, request):
        if not self.secret:
            return False
        return hmac.compare_digest(request.environ.get(self.header, ""), self.secret)

    def __repr__(self):
        return f"<SharedSecretHeader {self.header}>"


@implementer(IXmlrpcChecker)
class XmlrpcChecker:
    """
    Admit built-in XML-RPC when any of the configured rules matches.

    The rules are built once, at construction time, and never mutated
    afterwards, so the checker can be shared by all worker threads without
    locking. Building them lazily on first use would be a race waiting to
    happen as soon as a rule gains state of its own.

    Construction at import time is safe: the <environment> section of
    zope.conf is applied by Zope2.Startup.handlers.root_wsgi_handler, which
    runs before Zope2.startup_wsgi() initializes the products. A broken
    configuration therefore shows up while starting up rather than on the
    first XML-RPC request.
    """

    def __init__(self, rules=None):
        self.rules = tuple(self.build_rules() if rules is None else rules)

    @staticmethod
    def build_rules():
        networks = parse_networks(os.environ.get("PERFACT_XMLRPC_NETWORKS", ""))
        proxies = parse_networks(os.environ.get("PERFACT_XMLRPC_PROXIES", ""))
        rules = [
            SourceNetworks(
                LOOPBACK + networks,
                LOOPBACK + proxies,
                os.environ.get(
                    "PERFACT_XMLRPC_FORWARDED_HEADER",
                    DEFAULT_FORWARDED_HEADER,
                ),
            ),
        ]

        paths = parse_paths(os.environ.get("PERFACT_XMLRPC_PATHS", ""))
        if paths:
            rules.append(PathPrefixes(paths))

        secret = os.environ.get("PERFACT_XMLRPC_SECRET", "")
        if secret:
            rules.append(SharedSecretHeader(secret))

        logger.info("XML-RPC rules: %s", ", ".join(repr(rule) for rule in rules))
        return rules

    @staticmethod
    def apply_rule(rule, request):
        """
        Return whether rule admits request, treating a broken rule as a
        refusal so that one misconfigured rule cannot open up access. Conflict
        errors have to pass through for the publisher to retry the request.
        """
        try:
            return bool(rule(request))
        except ConflictError:
            raise
        except Exception:
            logger.exception("Rule %r failed", rule)
            return False

    def __call__(self, request):
        for rule in self.rules:
            if self.apply_rule(rule, request):
                return True
        logger.info(
            "REFUSED XML-RPC for %s (REMOTE_ADDR %s, %s %s)",
            request.environ.get("PATH_INFO", ""),
            request.environ.get("REMOTE_ADDR", ""),
            DEFAULT_FORWARDED_HEADER,
            request.environ.get(header_key(DEFAULT_FORWARDED_HEADER), "-"),
        )
        return False


checker = XmlrpcChecker()

zope.component.provideUtility(checker, IXmlrpcChecker)
