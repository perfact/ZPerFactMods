#
# Change behavior of ZServer so it does not tell the client which server version is running
#

import ZServer
ZServer.zhttp_server.SERVER_IDENT = ''
