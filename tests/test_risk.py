"""Tests del módulo de gestión de riesgo profesional."""
import pytest
from src.risk import RiskManager, RiskError


@pytest.fixture
def risk():
    return RiskManager(initial_capital=10000.0, risk_per_trade_pct=1.0)


class TestRiskManager:
    """Gestión de riesgo basada en los informes profesionales."""

    def test_calculates_position_size(self, risk):
        size = risk.calculate_position_size(entry_price=50000.0, stop_price=49000.0)
        # 1% de 10k = 100€ riesgo. Stop 2% = posición 5000€
        assert size == pytest.approx(5000.0, rel=0.1)

    def test_respects_max_risk(self, risk):
        size = risk.calculate_position_size(entry_price=100.0, stop_price=90.0)
        # Riesgo = 100€ (1%), stop = 10%, posición = 1000€ (máx 2%/10% = 2000)
        assert size <= 2000.0

    def test_risk_per_trade_limited(self, risk):
        risk.risk_per_trade_pct = 0.5  # 0.5%
        size = risk.calculate_position_size(entry_price=50000.0, stop_price=49500.0)
        assert size <= 10000.0  # No puede usar más que el capital

    def test_atr_based_stop(self, risk):
        stop = risk.atr_stop(entry_price=50000.0, atr=1000.0, multiplier=2.0)
        assert stop == pytest.approx(48000.0, rel=0.01)  # 2 ATR por debajo

    def test_kelly_fraction(self, risk):
        fraction = risk.kelly_fraction(win_rate=0.6, avg_win=100, avg_loss=50)
        # Kelly = 0.6 - 0.4/(100/50) = 0.6 - 0.2 = 0.4
        # Fractional Kelly 0.25 => 0.4 * 0.25 = 0.1
        assert fraction == pytest.approx(0.1, rel=0.1)

    def test_fractional_kelly(self, risk):
        fraction = risk.kelly_fraction(win_rate=0.6, avg_win=100, avg_loss=50, fraction=0.5)
        # Kelly = 0.4 * 0.5 = 0.2
        assert fraction == pytest.approx(0.2, rel=0.1)

    def test_rejects_zero_capital(self):
        with pytest.raises(ValueError):
            RiskManager(initial_capital=0)

    def test_daily_loss_limit(self, risk):
        risk.daily_loss_limit = 500  # Máximo 500€ pérdida diaria
        risk.daily_loss = 400
        can_trade = risk.can_trade(risk_amount=200)
        assert can_trade is False  # 400 + 200 > 500

    def test_volatility_adjustment(self, risk):
        # En mercados muy volátiles, reducir tamaño
        normal = risk.calculate_position_size(entry_price=100.0, stop_price=98.0)
        risk.atr_multiplier = 3.0
        adjusted = risk.calculate_position_size(entry_price=100.0, stop_price=98.0)
        assert adjusted <= normal
