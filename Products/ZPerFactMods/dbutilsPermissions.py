#
# Add permissions needed in DB_Utils
#

from Acquisition import Implicit
from AccessControl.SecurityInfo import ClassSecurityInfo 
import AccessControl.class_init
import logging
logger = logging.getLogger('Products.ZPerFactMods.dbutilsPermissions')

class DBUtilsPermissions(Implicit):
    def update(self):
        return
    def insert(self):
        return
    def delete(self):
        return
    def export(self):
        return
    def translate(self):
        return
    def edit_docs(self):
        return

    security = ClassSecurityInfo()

    dbuperms = [
        ('zDB_Delete_Records', 'delete'),
        ('zDB_Update_Records', 'update'),
        ('zDB_Insert_Records', 'insert'),
        ('zDB_Export_Records', 'export'),
        ('zI18N_Translate_Entries', 'translate'), # DEPRECATED
        ('zLayout_Edit_Docs', 'edit_docs')
    ]

    security = ClassSecurityInfo()
    for p, m in dbuperms:
        logger.info('Adding Permission %s' % p)
        security.declareProtected(p, m)

AccessControl.class_init.InitializeClass(DBUtilsPermissions)

