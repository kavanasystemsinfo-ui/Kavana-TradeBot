"""Tests del paper trader — modelo KAVANA (10% capital, stop 10%, 1x)."""
import pytest
from src.trader import Trader, TradeStatus, RiskError


@pytest.fixture
def trader():
    """Trader con capital 1000 USD, sin apalancamiento (1x)."""
    return Trader(initial_capital=1000.0, leverage=1, risk_per_trade_pct=10.0, daily_loss_limit=100.0)


class TestRiskValidation:
    def test_rejects_trade_exceeding_risk_limit(self, trader):
        """El Risk Manager limita el tamaño al capital disponible."""
        trade = trader.open_trade("BTC/USDT", 50000, "BUY", size=999999)
        assert trade.size <= trader.risk.current_capital
        assert trade.size > 0

    def test_accepts_valid_trade(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY")
        assert trade.status == TradeStatus.OPEN
        assert trade.symbol == "BTC/USDT"
        assert trade.entry_price == 50000
        # Posicion ~10% del capital (100$)
        assert 90 <= trade.size <= 110

    def test_assigns_unique_trade_id(self, trader):
        t1 = trader.open_trade("BTC/USDT", 50000, "BUY")
        t2 = trader.open_trade("ETH/USDT", 3000, "BUY")
        assert t1.id != t2.id


class TestPositionManagement:
    def test_tracks_open_positions(self, trader):
        trader.open_trade("BTC/USDT", 50000, "BUY")
        assert "BTC/USDT" in trader.positions
        assert trader.positions["BTC/USDT"].status == TradeStatus.OPEN

    def test_rejects_duplicate_position(self, trader):
        trader.open_trade("BTC/USDT", 50000, "BUY")
        with pytest.raises(RiskError):
            trader.open_trade("BTC/USDT", 51000, "BUY")

    def test_closes_position_and_records_pnl(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY")
        result = trader.close_trade("BTC/USDT", 55000, reason="TP_HIT")
        assert result.status == TradeStatus.CLOSED
        assert result.pnl_usd > 0  # Compramos a 50k, vendimos a 55k
        assert result.close_reason == "TP_HIT"

    def test_records_loss_on_close(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY")
        result = trader.close_trade("BTC/USDT", 45000, reason="SL_HIT")
        assert result.status == TradeStatus.CLOSED
        assert result.pnl_usd < 0


class TestStopLoss:
    def test_hits_stop_loss_on_decline(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY")
        # El precio cae un 10% (al stop) => -10% de la posicion (~10$)
        result = trader.tick("BTC/USDT", 45000)
        assert result is not None
        assert result.close_reason == "SL_HIT"
        assert result.pnl_usd <= -9.0  # ~10% de 100$

    def test_does_not_close_above_sl(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY")
        result = trader.tick("BTC/USDT", 45001)  # Justo por encima del SL (10%)
        assert result is None  # No se cerro

    def test_closes_at_sl_exactly(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY")
        result = trader.tick("BTC/USDT", 45000)  # En el SL exacto
        assert result is not None
        assert result.close_reason == "SL_HIT"


class TestTakeProfit:
    def test_hits_tp_when_configured(self, trader):
        trade = trader.open_trade("BTC/USDT", 50000, "BUY")
        trade.take_profit = 57500
        result = trader.tick("BTC/USDT", 57500)
        assert result is not None
        assert result.close_reason == "TP_HIT"


class TestPerformance:
    def test_roi_after_winning_trade(self, trader):
        trader.open_trade("BTC/USDT", 50000, "BUY")
        trader.close_trade("BTC/USDT", 55000, reason="TP_HIT")
        perf = trader.get_performance()
        assert perf["total_trades"] == 1
        assert perf["wins"] == 1
        assert perf["losses"] == 0
        assert perf["roi_pct"] > 0

    def test_win_rate_after_mixed_trades(self):
        # Limite diario amplio (200$) para permitir 2 trades de ~10% cada uno
        trader = Trader(initial_capital=1000.0, leverage=1,
                      risk_per_trade_pct=10.0, daily_loss_limit=200.0)
        trader.open_trade("BTC/USDT", 50000, "BUY")
        trader.close_trade("BTC/USDT", 55000, reason="TP_HIT")
        trader.open_trade("ETH/USDT", 3000, "BUY")
        trader.close_trade("ETH/USDT", 2700, reason="SL_HIT")
        perf = trader.get_performance()
        assert perf["wins"] == 1
        assert perf["losses"] == 1
        assert perf["win_rate"] == 50.0
