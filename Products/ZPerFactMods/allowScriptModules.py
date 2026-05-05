import importlib
import importlib.util
import os
import pkgutil

import perfact
from AccessControl import ClassSecurityInfo, ModuleSecurityInfo
from AccessControl.class_init import InitializeClass
from Products.PythonScripts.Utility import allow_class, allow_module


def walk_packages(path=None, prefix="", onerror=None):
    seen = set()

    # 1. First: normal pkgutil discovery (unchanged behavior)
    for module_info in pkgutil.iter_modules(path, prefix):
        name = module_info.name

        if name in seen:
            continue
        seen.add(name)

        yield module_info

        if module_info.ispkg:
            yield from _recurse(name, onerror, seen)

    # 2. Fallback: detect missing namespace packages
    if path:
        for base in path:
            if not os.path.isdir(base):
                continue

            for entry in os.scandir(base):
                if not entry.is_dir():
                    continue

                if entry.name == '__pycache__':
                    continue

                name = prefix + entry.name

                if name in seen:
                    continue

                spec = importlib.util.find_spec(name)
                if not spec or not spec.submodule_search_locations:
                    continue  # not a package

                seen.add(name)
                yield pkgutil.ModuleInfo(None, name, True)

                yield from _recurse(name, onerror, seen)


def _recurse(name, onerror, seen):
    try:
        spec = importlib.util.find_spec(name)
    except Exception:
        if onerror:
            onerror(name)
        return

    if not spec or not spec.submodule_search_locations:
        return

    yield from walk_packages(spec.submodule_search_locations, name + ".", onerror)


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
for module in walk_packages(perfact.__path__, f'{perfact.__name__}.'):
    # Allow perfact modules except test modules
    if '.tests' in module.name:
        continue

    if not module.name.endswith('.allowedclasses'):
        allow_module(module.name)
        continue

    # Special handling for allowedclasses module
    mod = importlib.import_module(module.name)
    if not hasattr(mod, "__all__"):
        raise RuntimeError(
            f"{module.name} must define __all__"
        )

    # Get names of the allowed classes
    names = mod.__all__
    objects = (getattr(mod, name, None) for name in names)
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
    from perfact.dbutils.conn import Namespace, Results, ZRDBConnectionWrapper
    allow_class(ZRDBConnectionWrapper)
    allow_class(Namespace)
    allow_class(Results)
except ImportError:
    pass
