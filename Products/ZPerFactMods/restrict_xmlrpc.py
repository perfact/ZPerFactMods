#
# Restrict Zope's built-in XML-RPC support to callers on the local machine.
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
# request, and only admit calls coming from the machine itself. Should an
# external caller turn up after all, add its address to the configuration
# below until it can be moved to a REST interface.
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
#
# Write addresses in their plain IPv4 form, '192.168.5.7' and not
# '::ffff:192.168.5.7'. Incoming addresses are unwrapped from the IPv4-mapped
# IPv6 form before they are matched (see normalize_addr) but the configured
# ranges are not, so a mapped range would never match anything. This is worth
# watching out for because the address logged for a refused request can be in
# the mapped form, and is then copied into the configuration verbatim.
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

import ipaddress
import logging
import os

import zope.component
from zope.interface import implementer
from ZPublisher.interfaces import IXmlrpcChecker

logger = logging.getLogger("Products.ZPerFactMods.restrict_xmlrpc")

LOOPBACK = (ipaddress.ip_network("127.0.0.0/8"), ipaddress.ip_network("::1/128"))

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


@implementer(IXmlrpcChecker)
class XmlrpcChecker:
    """
    Admit built-in XML-RPC only for callers in one of the allowed networks.

    The configuration is read and frozen at construction time, so the checker
    holds no mutable state and can be shared by all worker threads without
    locking. Reading it at import time is safe: the <environment> section of
    zope.conf is applied by Zope2.Startup.handlers.root_wsgi_handler, which
    runs before Zope2.startup_wsgi() initializes the products. A broken
    configuration therefore shows up while starting up rather than on the first
    XML-RPC request.
    """

    def __init__(self, networks=None, proxies=None, forwarded_header=None):
        if networks is None:
            networks = parse_networks(os.environ.get("PERFACT_XMLRPC_NETWORKS", ""))
        if proxies is None:
            proxies = parse_networks(os.environ.get("PERFACT_XMLRPC_PROXIES", ""))
        if forwarded_header is None:
            forwarded_header = os.environ.get(
                "PERFACT_XMLRPC_FORWARDED_HEADER",
                DEFAULT_FORWARDED_HEADER,
            )

        self.networks = LOOPBACK + tuple(networks)
        self.proxies = LOOPBACK + tuple(proxies)
        self.forwarded_header = forwarded_header
        self.environ_key = header_key(forwarded_header)
        logger.info(
            "Allowing XML-RPC from %s, behind %s, taken from %s",
            ", ".join(str(network) for network in self.networks),
            ", ".join(str(proxy) for proxy in self.proxies),
            forwarded_header,
        )

    def __call__(self, request):
        addr = client_addr(request, self.proxies, self.environ_key)
        if addr is not None and any(addr in net for net in self.networks):
            return True
        logger.info(
            "REFUSED XML-RPC for %s (REMOTE_ADDR %s, %s %s)",
            request.environ.get("PATH_INFO", ""),
            request.environ.get("REMOTE_ADDR", ""),
            self.forwarded_header,
            request.environ.get(self.environ_key, "-"),
        )
        return False


checker = XmlrpcChecker()

zope.component.provideUtility(checker, IXmlrpcChecker)
