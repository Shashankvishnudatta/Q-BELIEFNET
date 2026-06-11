from app.services.mock_data import generate_mock_stock_data, generate_mock_trending_data


def test_generate_mock_trending_data_shape():
    stocks = generate_mock_trending_data()

    assert len(stocks) >= 10
    assert {"ticker", "beliefScore", "sentiment", "sparkline"}.issubset(stocks[0])
    assert 0 <= stocks[0]["beliefScore"] <= 100


def test_generate_mock_stock_data_shape():
    stock = generate_mock_stock_data("NVDA")

    assert stock["ticker"] == "NVDA"
    assert {"coherence", "velocity", "fragility"}.issubset(stock["metrics"])
    assert stock["chartData"]
    assert stock["clusters"]
