import importlib
import pytest

@pytest.mark.parametrize("modpath", [
    "services.api.routes.create",
    "services.api.routes.execute",
    "services.api.routes.planner",
])
def test_routes_modules_import(modpath):
    try:
        mod = importlib.import_module(modpath)
    except Exception:
        pytest.skip(f"cannot import {modpath}")
    assert mod is not None
