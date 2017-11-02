#
# Disable the dubious auto-connecting feature in ZRDB.
#

from Shared.DC.ZRDB import Connection
Connection.Connection.connect_on_load = False
