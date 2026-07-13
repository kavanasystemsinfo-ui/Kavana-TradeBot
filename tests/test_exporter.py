"""Tests de exportación a Google Sheets y CSV."""
import pytest
from unittest.mock import patch, MagicMock
from src.exporter import Exporter
from src.trader import Trade, TradeStatus


@pytest.fixture
def trades():
    return [
        Trade(id="t1", symbol="BTC/USDT", direction="BUY", entry_price=50000,
              size=100, status=TradeStatus.CLOSED, pnl_usd=500, pnl_pct=15.0,
              close_reason="TP_HIT", stop_loss=44000, take_profit=57500),
        Trade(id="t2", symbol="SOL/USDT", direction="BUY", entry_price=150,
              size=50, status=TradeStatus.OPEN, stop_loss=0, take_profit=0),
    ]


class TestCsvExport:
    def test_exports_trades_to_csv(self, trades):
        csv = Exporter.to_csv(trades)
        assert csv.startswith("id,symbol")
        assert "BTC/USDT" in csv
        assert csv.count("\n") == 3

    def test_exports_empty_list(self):
        csv = Exporter.to_csv([])
        assert csv.count("\n") == 1


class TestGoogleSheetsPayload:
    """El payload debe coincidir con el formato del viejo sistema."""

    def test_builds_expected_payload(self):
        t = Trade(id="x1", symbol="BTC/USDT", direction="BUY", entry_price=50000,
                  size=100, status=TradeStatus.CLOSED, pnl_usd=500, pnl_pct=15.0,
                  close_reason="TP_HIT", stop_loss=44000, take_profit=57500)
        payload = Exporter._build_payload(t, sheet="REAL", leverage=10, capital=1500, initial_capital=1000)
        assert payload["sheet"] == "REAL"
        assert payload["activo"] == "BTC/USDT"
        assert payload["resultado"] == "WIN ✅"
        assert payload["pnl_neto"] == 500
        assert payload["capital_actual"] == 1500
        assert payload["capital_inicial"] == 1000
        assert payload["apalancamiento"] == 10

    def test_open_trade_payload(self):
        t = Trade(id="x2", symbol="SOL/USDT", direction="BUY", entry_price=150,
                  size=50, status=TradeStatus.OPEN, stop_loss=0, take_profit=0)
        payload = Exporter._build_payload(t, sheet="REAL", leverage=10, capital=1000, initial_capital=1000)
        assert payload["resultado"] == "ABIERTA ⏳"
        assert payload["direccion"] == "BUY"

    def test_loss_label(self):
        t = Trade(id="x3", symbol="ETH/USDT", direction="SELL", entry_price=3000,
                  size=100, status=TradeStatus.CLOSED, pnl_usd=-200, pnl_pct=-6.0,
                  close_reason="SL_HIT", stop_loss=3360, take_profit=2550)
        payload = Exporter._build_payload(t, sheet="LABS", leverage=5, capital=800, initial_capital=1000)
        assert payload["resultado"] == "LOSE ❌"


class TestGoogleSheetsSend:
    @pytest.mark.asyncio
    async def test_requires_url(self, trades):
        result = await Exporter.to_google_sheets(trades, "", leverage=10, capital=1000, initial_capital=1000)
        assert result is False

    @pytest.mark.asyncio
    async def test_handles_connection_error(self, trades):
        result = await Exporter.to_google_sheets(trades, "https://invalid.url", leverage=10, capital=1000, initial_capital=1000)
        assert result is False

