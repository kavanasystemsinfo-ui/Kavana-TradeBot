"""Tests del módulo de exchange (ccxt mockeado)."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pandas as pd
from src.exchange import Exchange, ExchangeError


@pytest.fixture
def mock_ccxt():
    """Crea un exchange simulado sin conexión real."""
    with patch("src.exchange.ccxt") as mock:
        exchange_instance = MagicMock()
        mock.kucoin.return_value = exchange_instance
        yield exchange_instance


class TestExchangeInit:
    """Al crear un Exchange se debe configurar correctamente."""

    def test_creates_exchange_with_default_id(self, mock_ccxt):
        ex = Exchange()
        assert ex.exchange_id == "kucoin"

    def test_creates_exchange_with_custom_id(self, mock_ccxt):
        ex = Exchange(exchange_id="binance")
        assert ex.exchange_id == "binance"


class TestFetchOHLCV:
    """Obtener velas debe devolver un DataFrame limpio."""

    def test_returns_dataframe_with_expected_columns(self, mock_ccxt):
        mock_ccxt.fetch_ohlcv.return_value = [
            [1000000, 50000, 51000, 49000, 50500, 100.5],
            [1000060, 50600, 51200, 50200, 51000, 150.3],
        ]

        ex = Exchange()
        df = ex.fetch_ohlcv("BTC/USDT", timeframe="5m", limit=2)

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert len(df) == 2
        assert df.iloc[0]["close"] == 50500

    def test_raises_error_on_empty_response(self, mock_ccxt):
        mock_ccxt.fetch_ohlcv.return_value = []
        ex = Exchange()

        with pytest.raises(ExchangeError, match="Sin datos"):
            ex.fetch_ohlcv("BTC/USDT")

    def test_raises_error_on_connection_failure(self, mock_ccxt):
        mock_ccxt.fetch_ohlcv.side_effect = ConnectionError("Timeout")
        ex = Exchange()

        with pytest.raises(ExchangeError, match="Error de conexión"):
            ex.fetch_ohlcv("BTC/USDT")


class TestGetTicker:
    """El ticker debe devolver el precio actual."""

    def test_returns_current_price(self, mock_ccxt):
        mock_ccxt.fetch_ticker.return_value = {"last": 51200.0, "bid": 51100, "ask": 51300}

        ex = Exchange()
        ticker = ex.get_ticker("BTC/USDT")

        assert ticker["last"] == 51200.0
        assert ticker["bid"] == 51100
        assert ticker["ask"] == 51300

    def test_raises_error_on_failure(self, mock_ccxt):
        mock_ccxt.fetch_ticker.side_effect = Exception("API limit")
        ex = Exchange()

        with pytest.raises(ExchangeError):
            ex.get_ticker("BTC/USDT")
