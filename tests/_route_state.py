"""Baseline/restore for web/backend route-module state (v2 - immutable baseline).

web/backend state lives in TWO places:
  * main.py's `stores` dict (seeded by init_data()),
  * ~40 routes/*.py modules' own module-level dicts/counters
    (_roles_db, _users_db, _next_id, ...) seeded at import.
The same file can be imported under two names ('web.backend.routes.roles' and
'routes.roles', each an independent instance); FastAPI handlers bind to
whichever instance the app was built from - bare 'routes.*' in practice.

The trap this design exists to avoid: suites that DELETE seeded rows
(test_all_modules deletes /api/<collection>/1 for 42 collections) must not be
able to re-baseline that polluted state. v1 stored everything in one mutable
dict, and a snapshot() call after a delete silently adopted the polluted state
as the new baseline. v2 keeps ONE immutable baseline (set at conftest import,
never overwritten) plus a secondary `_adopted` dict for instances that appear
later; restore() only ever copies FROM those INTO the modules.

tests/conftest.py: snapshot() at import time, ensure_bare_baseline() in the
first fixture setup (the bare universe is only importable once web/backend is
on sys.path), restore() around each test.
"""
from __future__ import annotations

import copy
import glob
import importlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROUTES_DIR = os.path.join(_ROOT, "web", "backend", "routes")

_baseline: dict[str, dict] = {}
_adopted: dict[str, dict] = {}


def _all_route_module_instances():
    """Every loaded module whose file lives in web/backend/routes."""
    seen = {}
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        normed = os.path.normpath(f)
        if os.sep + "web" + os.sep + "backend" + os.sep + "routes" + os.sep in normed:
            seen[name] = mod
    return sorted(seen.items())


def _state_items(mod):
    """Yield (attr, value) for module-level state.

    Two naming conventions exist across routes/*.py:
      * underscore-prefixed dicts/ints (_roles_db, _next_id, ...)
      * ALL-CAPS public lists/dicts (DEPARTMENTS_DB, EMPLOYEES_DB, ...)
        used by newer modules (hr.py, ...).
    Snapshot both; skip everything else (imports, models, routers, props).
    """
    for attr in dir(mod):
        if attr.startswith("__"):
            continue
        val = getattr(mod, attr)
        if callable(val):
            continue
        is_private_state = attr.startswith("_") and isinstance(val, (dict, list, int))
        is_public_state = (
            attr.isupper() and isinstance(val, (dict, list)) and val is not None
        )
        if is_private_state or is_public_state:
            yield attr, val


def _import_route_modules(package_prefix: str) -> None:
    """Import every routes/*.py under the given prefix, ignoring failures."""
    try:
        importlib.import_module(package_prefix)
    except Exception:
        pass
    for path in sorted(glob.glob(os.path.join(_ROUTES_DIR, "*.py"))):
        name = os.path.basename(path)[:-3]
        if name.startswith("__"):
            continue
        try:
            importlib.import_module(f"{package_prefix}.{name}")
        except Exception:
            pass


def snapshot() -> int:
    """Capture PRISTINE state into the immutable baseline (call once, early).

    Never call this after tests have run: it re-baselines whatever state
    currently exists, which is exactly the pollution being defended against.
    """
    _import_route_modules("web.backend.routes")
    for key, mod in _all_route_module_instances():
        for attr, val in _state_items(mod):
            _baseline.setdefault(f"{key}:{attr}", copy.deepcopy(val))
    _baseline.update(_extra_state())
    return len(_baseline)


def ensure_bare_baseline() -> None:
    """Import the bare-name route universe pre-mutation and baseline it.

    main.py imports its route modules as bare `routes.<name>`; those instances
    exist only after web/backend is on sys.path. Must run before any test
    mutates state so the baseline for that universe is the pristine seed.
    """
    backend_dir = os.path.join(_ROOT, "web", "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    _import_route_modules("routes")
    for key, mod in _all_route_module_instances():
        for attr, val in _state_items(mod):
            _baseline.setdefault(f"{key}:{attr}", copy.deepcopy(val))


def restore() -> None:
    """Write baseline values onto every loaded instance (never the reverse)."""
    # adopt newly loaded instances into _adopted only (NOT the baseline)
    for key, mod in _all_route_module_instances():
        for attr, val in _state_items(mod):
            k = f"{key}:{attr}"
            if k not in _baseline and k not in _adopted:
                _adopted[k] = copy.deepcopy(val)

    _restore_extra()
    for source in (_baseline, _adopted):
        for key, val in source.items():
            mod_key, _, attr = key.rpartition(":")
            mod = sys.modules.get(mod_key)
            if mod is not None and hasattr(mod, attr):
                setattr(mod, attr, copy.deepcopy(val))


def _extra_state() -> dict:
    out = {}
    for name in ("main", "web.backend.main"):
        mod = sys.modules.get(name)
        if mod is not None and hasattr(mod, "stores"):
            out[f"{name}:stores"] = copy.deepcopy(mod.stores)
    return out


def _restore_extra() -> None:
    for name in ("main", "web.backend.main"):
        val = _baseline.get(f"{name}:stores")
        if val is not None:
            mod = sys.modules.get(name)
            if mod is not None and hasattr(mod, "stores"):
                mod.stores.clear()
                mod.stores.update(copy.deepcopy(val))
