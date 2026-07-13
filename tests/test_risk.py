"""Tests del gestor de riesgo — modelo KAVANA (posicion 10% capital, stop 10%)."""
import pytest
from src.risk import RiskManager, RiskError


@pytest.fixture
def risk():
    return RiskManager(initial_capital=1000.0, risk_per_trade_pct=10.0, atr_multiplier=1.0)


class TestRiskManager:
    def test_position_is_10pct_capital(self, risk):
        size = risk.calculate_position_size(entry_price=50000.0, stop_price=45000.0)
        # 10% de 1000$ = 100$ (independiente de la distancia al stop)
        assert size == pytest.approx(100.0, rel=0.05)

    def test_respects_capital_cape(self, risk):
        size = risk.calculate_position_size(entry_price=100.0, stop_price=90.0)
        assert size <= 1000.0

    def test_no_leverage_cap(self, risk):
        # Sin palanca: el tope es el capital completo
        big = RiskManager(initial_capital=1000.0, risk_per_trade_pct=100.0)
        size = big.calculate_position_size(entry_price=100.0, stop_price=90.0)
        assert size == pytest.approx(1000.0, rel=0.001)

    def test_atr_based_stop(self, risk):
        stop = risk.atr_stop(entry_price=50000.0, atr=1000.0, multiplier=1.0)
        assert stop == pytest.approx(49000.0, rel=0.01)

    def test_kelly_fraction(self, risk):
        fraction = risk.kelly_fraction(win_rate=0.6, avg_win=100, avg_loss=50)
        # Kelly = 0.6 - 0.4/(100/50) = 0.6 - 0.2 = 0.4
        # Fractional Kelly 0.25 => 0.4 * 0.25 = 0.1
        assert fraction == pytest.approx(0.1, rel=0.1)

    def test_fractional_kelly(self, risk):
        fraction = risk.kelly_fraction(win_rate=0.6, avg_win=100, avg_loss=50, fraction=0.5)
        assert fraction == pytest.approx(0.2, rel=0.1)

    def test_rejects_zero_capital(self):
        with pytest.raises(ValueError):
            RiskManager(initial_capital=0)

    def test_daily_loss_limit(self, risk):
        risk.daily_loss_limit = 100  # Max 100$ de perdida real (10% de 1000$)
        risk.daily_loss = 100
        can_trade = risk.can_trade(risk_amount=20)
        assert can_trade is False  # perdida acumulada alcanzo el limite

    def test_daily_loss_limit_ok(self, risk):
        risk.daily_loss_limit = 100
        risk.daily_loss = 50
        assert risk.can_trade(risk_amount=20) is True
