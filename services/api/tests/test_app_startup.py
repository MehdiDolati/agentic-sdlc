import asyncio

from starlette.testclient import TestClient

from services.api.app import app, _init_schemas, lifespan


def test__init_schemas_handles_partial_failures(monkeypatch):
    import services.api.app as app_module

    sentinel_engine = object()
    plan_calls = []
    run_calls = []

    def fake_engine():
        return sentinel_engine

    def fake_ensure_plans(engine):
        plan_calls.append(engine)

    def fake_ensure_runs(engine):
        run_calls.append(engine)
        raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "_engine", fake_engine)
    monkeypatch.setattr(app_module, "ensure_plans_schema", fake_ensure_plans)
    monkeypatch.setattr(app_module, "ensure_runs_schema", fake_ensure_runs)

    # Should not raise even though ensure_runs_schema errors.
    _init_schemas()

    assert plan_calls == [sentinel_engine]
    assert run_calls == [sentinel_engine]


def test_lifespan_calls_init_schemas_once(monkeypatch):
    import services.api.app as app_module

    sentinel_engine = object()
    plan_calls = []
    run_calls = []

    def fake_engine():
        return sentinel_engine

    def fake_ensure_plans(engine):
        plan_calls.append(engine)

    def fake_ensure_runs(engine):
        run_calls.append(engine)

    monkeypatch.setattr(app_module, "_engine", fake_engine)
    monkeypatch.setattr(app_module, "ensure_plans_schema", fake_ensure_plans)
    monkeypatch.setattr(app_module, "ensure_runs_schema", fake_ensure_runs)

    async def _use_lifespan():
        async with lifespan(app):
            pass

    asyncio.run(_use_lifespan())

    assert plan_calls == [sentinel_engine]
    assert run_calls == [sentinel_engine]


def test_health_endpoint_prints_debug_info(monkeypatch, capsys):
    import services.api.app as app_module

    monkeypatch.setenv("STARTUP_DEBUG", "1")

    fake_dsn = "postgresql://fake"

    def fake_conninfo():
        return fake_dsn

    def fake_summary(dsn):
        assert dsn == fake_dsn
        return "summary"

    monkeypatch.setattr(app_module, "psycopg_conninfo_from_env", fake_conninfo)
    monkeypatch.setattr(app_module, "dsn_summary", fake_summary)

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    captured = capsys.readouterr()
    assert "[app] normalized DSN: summary" in captured.out
