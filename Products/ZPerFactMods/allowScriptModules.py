import pkgutil
import perfact
from Products.PythonScripts.Utility import allow_module, allow_class
from AccessControl import ModuleSecurityInfo, ClassSecurityInfo
from AccessControl.class_init import InitializeClass
import importlib


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

# Allow ZTUtils, it provides url_query which is used in db_edit_magnetic
allow_module("ZTUtils")

# Allow access to python module "perfact" and submodules, recursively
# but skip modules in perfact.tests
for module in pkgutil.walk_packages(perfact.__path__, f'{perfact.__name__}.'):
    # Allow perfact modules except test modules
    if '.tests' in module.name:
        continue
    allow_module(module.name)
    # Check if our package has an allowedclasses module by trying to import it
    allowed_mod_name = f"{module.name}.allowedclasses"
    try:
        allowed_mod = importlib.import_module(allowed_mod_name)
    except Exception:
        continue

    if not hasattr(allowed_mod, "__all__"):
        raise RuntimeError(
            f"{allowed_mod_name} must define __all__"
        )

    # Get names of the allowed classes
    names = allowed_mod.__all__
    objects = (getattr(allowed_mod, name, None) for name in names)
    # Try to allow all given classes
    for obj in objects:
        if obj is None:
            continue
        try:
            allow_class(obj)
        except Exception:
            pass

# This is on by default in Zope2, but not in Zope4
allow_module("Products.PythonScripts.standard")

# Needed for sql_quote()
allow_module("DocumentTemplate.DT_Var")

# Allow the cbor2-decoder module
allow_module("cbor2.decoder")

# In order to use the central connector, we need to allow access to
# the class.
try:
    from perfact.dbconn import DBConn
    allow_class(DBConn)
except ImportError:
    pass

try:
    from perfact.latex import HTML2Tex
    allow_class(HTML2Tex)
except ImportError:
    pass

try:
    from perfact.network import InterfacesParser
    allow_class(InterfacesParser)
except ImportError:
    pass

try:
    from perfact.dbutils.conn import ZRDBConnectionWrapper
    from perfact.dbutils.conn import Namespace
    from perfact.dbutils.conn import Results
    allow_class(ZRDBConnectionWrapper)
    allow_class(Namespace)
    allow_class(Results)
except ImportError:
    pass
