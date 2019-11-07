#
# Change behavior of ZServer so it does not tell the client which server version is running
#

# On Zope4/Python3, there is no ZServer.
# TODO: WSGI equivalent
try:
    import ZServer
    ZServer.zhttp_server.SERVER_IDENT = ''
except ImportError:
    pass
