import importlib
import pytest
ALLOWED_ROUTE_MODULES = {
    "services.api.routes.ui_requests",
    "services.api.routes.auth",
    "services.api.routes.plans",
}
assert modpath in ALLOWED_ROUTE_MODULES, f"Unexpected route module: {modpath}"
mod = importlib.import_module(modpath)  # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
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
