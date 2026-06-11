import asyncio

from app.services.background_refresh import refresh_symbols


def test_background_refresh_service_runs_one_cycle():
    run = asyncio.run(refresh_symbols(["AAPL"]))

    assert run.status in {"success", "partial"}
    assert run.symbols_requested == ["AAPL"]
    assert run.finished_at is not None
