"""Tests del gestor de riesgo y paper trading."""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from src.trader import Trader, Trade, TradeStatus, RiskError


@pytest.fixture
def trader():
    """Trader con capital inicial de 1000 USD, apalancamiento 10x."""
    return Trader(initial_capital=1000.0, leverage=10)


class TestRiskValidation:
    """Las reglas de riesgo deben validarse antes de abrir una posición."""

    def test_rejects_trade_exceeding_risk_limit(self, trader):
        """Con Risk Manager, el tamaño se ajusta automáticamente al riesgo."""
        trade = trader.open_trade("BTC/USDT", 50000, "BUY", size=trader.risk.current_capital * 100)
        # Aunque pidamos un tamaño enorme, el Risk Manager lo ajusta
        assert trade.size < trader.risk.current_capital * 100
        assert trade.size > 0

    def test_accepts_valid_trade(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        assert trade.status == TradeStatus.OPEN
        assert trade.symbol == "BTC/USDT"
        assert trade.entry_price == 50000

    def test_assigns_unique_trade_id(self, trader):
        t1 = trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        t2 = trader.open_trade("ETH/USDT", 3000, "BUY", size=100)
        assert t1.id != t2.id


class TestPositionManagement:
    """Las posiciones abiertas deben gestionarse correctamente."""

    def test_tracks_open_positions(self, trader):
        trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        assert "BTC/USDT" in trader.positions
        assert trader.positions["BTC/USDT"].status == TradeStatus.OPEN

    def test_rejects_duplicate_position(self, trader):
        trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        with pytest.raises(RiskError):
            trader.open_trade("BTC/USDT", 51000, "BUY", size=100)

    def test_closes_position_and_records_pnl(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        result = trader.close_trade("BTC/USDT", 55000, reason="TP_HIT")
        assert result.status == TradeStatus.CLOSED
        assert result.pnl_usd > 0  # Compramos a 50k, vendimos a 55k
        assert result.close_reason == "TP_HIT"

    def test_records_loss_on_close(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        result = trader.close_trade("BTC/USDT", 45000, reason="SL_HIT")
        assert result.status == TradeStatus.CLOSED
        assert result.pnl_usd < 0


class TestStopLoss:
    """El stop loss debe calcularse y ejecutarse automáticamente."""

    def test_hits_stop_loss_on_decline(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        # El precio cae por debajo del SL
        result = trader.tick("BTC/USDT", 43000)
        assert result is not None
        assert result.close_reason == "SL_HIT"

    def test_does_not_close_above_sl(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        result = trader.tick("BTC/USDT", 49001)  # Justo por encima del SL
        assert result is None  # No se cerró

    def test_closes_at_sl_exactly(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        result = trader.tick("BTC/USDT", 49000)  # En el SL exacto
        assert result is not None
        assert result.close_reason == "SL_HIT"


class TestTakeProfit:
    """El take profit debe ejecutarse cuando está configurado."""

    def test_hits_tp_when_configured(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        # Configurar take profit manualmente
        trade.take_profit = 57500
        result = trader.tick("BTC/USDT", 57500)
        assert result is not None
        assert result.close_reason == "TP_HIT"


class TestPerformance:
    """El rendimiento acumulado debe calcularse correctamente."""

    def test_roi_after_winning_trade(self, trader):
        trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        trader.close_trade("BTC/USDT", 55000, reason="TP_HIT")
        perf = trader.get_performance()
        assert perf["total_trades"] == 1
        assert perf["wins"] == 1
        assert perf["losses"] == 0
        assert perf["roi_pct"] > 0

    def test_win_rate_after_mixed_trades(self, trader):
        trader.open_trade("BTC/USDT", 50000, "BUY", size=100)
        trader.close_trade("BTC/USDT", 55000, reason="TP_HIT")
        trader.open_trade("ETH/USDT", 3000, "BUY", size=100)
        trader.close_trade("ETH/USDT", 2500, reason="SL_HIT")
        perf = trader.get_performance()
        assert perf["wins"] == 1
        assert perf["losses"] == 1
        assert perf["win_rate"] == 50.0
