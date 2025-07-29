# app/api/__init__.py
"""
Auto-import submodules so that
    from app.api import auth, servers, updates, settings
works even when they haven't been imported elsewhere.
"""

from importlib import import_module as _import

for _name in ("auth", "servers", "updates", "settings"):
    try:
        _import(f"{__name__}.{_name}")
    except ImportError:
        # the submodule may not exist yet (e.g. settings.py not implemented)
        pass

del _import, _name
