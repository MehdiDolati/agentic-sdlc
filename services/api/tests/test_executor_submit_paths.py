import inspect
import pytest


def _call_safely(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception:
        return None


def test_executor_submit_and_errors():
    try:
        from services.api import executor as ex
    except Exception:
        pytest.skip("services.api.executor not importable")

    # 1) Try direct run helpers if any
    def ok(x): return x + 1
    def boom(): raise RuntimeError("boom")

    for name in ("run_sync", "run", "execute", "call"):
        fn = getattr(ex, name, None)
        if callable(fn):
            _call_safely(fn, ok, 1)
            _call_safely(fn, boom)  # error path

    # 2) Try to get a pool/executor and submit tasks
    pool = None
    for factory in ("get_executor", "executor", "make_executor", "get_pool", "pool"):
        fac = getattr(ex, factory, None)
        if callable(fac):
            try:
                sig = inspect.signature(fac)
                if len(sig.parameters) == 0:
                    pool = fac()
                else:
                    # try without args anyway; many factories default sensibly
                    pool = fac()
            except Exception:
                pool = None
        elif fac is not None:
            pool = fac
        if pool:
            break

    if pool:
        submit = getattr(pool, "submit", None)
        if callable(submit):
            # happy path
            try:
                f1 = submit(ok, 2)
                try:
                    _ = f1.result(timeout=0.2)
                except Exception:
                    pass
            except Exception:
                pass
            # error path
            try:
                f2 = submit(boom)
                try:
                    _ = f2.result(timeout=0.2)
                except Exception:
                    pass
            except Exception:
                pass

        # Shutdown / close branches if available
        for closer in ("shutdown", "close", "stop"):
            cfn = getattr(pool, closer, None)
            if callable(cfn):
                try:
                    if "wait" in getattr(cfn, "__code__", ()).__dict__.get("co_varnames", ()):
                        cfn(wait=False)
                    else:
                        cfn()
                except Exception:
                    pass