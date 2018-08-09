from Products.PythonScripts.Utility import allow_module, allow_class
from AccessControl import ModuleSecurityInfo, ClassSecurityInfo
from AccessControl.class_init import InitializeClass

# Allowing whole modules
# allow_module("module_name").

# Allow some names in modules
# ModuleSecurityInfo('module_name').declarePublic('name1', 'name2', ...)

# Allowing a class
# from <module_name> import <class>
# allow_class(<class>)

# Allow access to the exception "Redirect" in Python Scripts
ModuleSecurityInfo('zExceptions').declarePublic('Redirect')

# Allow regular expressions
allow_module("re")

# Allow the datetime module
allow_module("datetime")

# Allow the time module
allow_module("time")

# Allow access to python module "perfact" and submodules
allow_module("perfact.LDAP")
allow_module("perfact.asterisk_utils.py")
allow_module("perfact.balances")
allow_module("perfact.barcode")
allow_module("perfact.cert")
allow_module("perfact.checktarget")
allow_module("perfact.configparser_compat")
allow_module("perfact.dbconn")
allow_module("perfact.dbdaemontools")
allow_module("perfact.dbsync")
allow_module("perfact.file")
allow_module("perfact.fileassets")
allow_module("perfact.firewall")
allow_module("perfact.fwrc")
allow_module("perfact.generic")
allow_module("perfact.graphics")
allow_module("perfact.latex")
allow_module("perfact.mail")
allow_module("perfact.mod")
allow_module("perfact.modsync")
allow_module("perfact.mpr")
allow_module("perfact.network")
allow_module("perfact.ovpn")
allow_module("perfact.performancemeter")
allow_module("perfact.pfcodechg")
allow_module("perfact.printer")
allow_module("perfact.radius")
allow_module("perfact.say")
allow_module("perfact.server")
allow_module("perfact.sound")
allow_module("perfact.sql")
allow_module("perfact.ssh")
allow_module("perfact.webservice")
allow_module("perfact.winvnc")
allow_module("perfact.xls")
allow_module("perfact.zlayout")
allow_module("perfact.zopeinterface")

# This is on by default in Zope2, but not in Zope4
allow_module("Products.PythonScripts.standard")

# In order to use the central connector, we need to allow access to
# the class.
from perfact.dbconn import DBConn
allow_class(DBConn)
