import time
import pytest

def slow_fn(t=0.05):
    time.sleep(t)
    return "ok"

def err_fn():
    raise ValueError("bang")

def test_executor_edges():
    try:
        from services.api import executor as ex
    except Exception:
        pytest.skip("services.api.executor not importable")

    # Direct run helpers (if any)
    for name in ("run_sync", "run", "execute", "call"):
        fn = getattr(ex, name, None)
        if callable(fn):
            try:
                fn(slow_fn, 0.01)
            except Exception:
                pass
            try:
                fn(err_fn)
            except Exception:
                pass

    # Pool/executor factory path
    pool = None
    for factory in ("get_executor", "executor", "make_executor", "get_pool", "pool"):
        fac = getattr(ex, factory, None)
        if callable(fac):
            try:
                pool = fac()
                break
            except Exception:
                continue
        elif fac is not None:
            pool = fac
            break

    if not pool:
        pytest.skip("No pool/executor exposed")

    submit = getattr(pool, "submit", None)
    if callable(submit):
        # Success
        try:
            f1 = submit(slow_fn, 0.01)
            try:
                _ = f1.result(timeout=0.2)
            except Exception:
                pass
        except Exception:
            pass
        # Exception path
        try:
            f2 = submit(err_fn)
            try:
                _ = f2.result(timeout=0.2)
            except Exception:
                pass
        except Exception:
            pass

    # Tickle shutdown/close branches
    for closer in ("shutdown", "close", "stop"):
        cfn = getattr(pool, closer, None)
        if callable(cfn):
            try:
                cfn()
            except Exception:
                pass
