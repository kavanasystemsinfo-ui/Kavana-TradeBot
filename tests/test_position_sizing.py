"""Tests del modelo de riesgo del usuario (KAVANA):

Modelo:
- Posicion = 10% del capital actual (ej: 1000$ -> 100$)
- Stop = 10% del precio de entrada
- Apalancamiento = 1x (sin palanca)
- Perdida maxima por trade = 10% de la posicion = 10$ cuando hay 1000$
- El 10% se recalcula sobre el capital restante tras cada trade.
"""
import pytest
from src.risk import RiskManager
from src.trader import Trader


@pytest.fixture
def rm():
    return RiskManager(
        initial_capital=1000.0,
        risk_per_trade_pct=10.0,   # 10% del capital en posicion
        atr_multiplier=1.0,
    )


def test_position_is_10pct_of_capital(rm):
    size = rm.calculate_position_size(entry_price=0.1646, stop_price=0.1646 * 0.90)
    # 10% de 1000$ = 100$ ; stop al 10% => size = 100 / 0.10 = 1000? NO.
    # Con nuestro modelo: posicion fija 10% capital, stop 10% precio.
    # size debe ser ~100$ (10% de 1000$), NO 1000$.
    assert 90 <= size <= 110, f"size inesperado: {size}"


def test_max_loss_per_trade_is_10pct_of_position(rm):
    # Stop al 10% del precio => si salta, perdida = 10% de la posicion (100$) = 10$
    entry = 0.1646
    stop = entry * 0.90
    size = rm.calculate_position_size(entry, stop)
    loss_if_stop = size * 0.10
    assert loss_if_stop <= 11.0, f"perdida por stop demasiado alta: {loss_if_stop}"


def test_leverage_is_1x(rm):
    t = Trader(initial_capital=1000.0, leverage=1, risk_per_trade_pct=10.0, atr_multiplier=1.0)
    # Sin ATR: stop fijo 10% del precio
    trade = t.open_trade("ADA/USDT", price=0.1646, direction="BUY")
    assert trade.size <= 110, f"posicion sin palanca debe ser ~100$, fue {trade.size}"
    assert trade.stop_loss <= 0.1646 * 0.92, "stop debe estar ~10% bajo entry"


def test_max_loss_is_10pct_of_position():
    """Si el stop salta, la perdida es 10% de la posicion (100$ -> 10$)."""
    t = Trader(initial_capital=1000.0, leverage=1, risk_per_trade_pct=10.0)
    trade = t.open_trade("ADA/USDT", price=0.1646, direction="BUY")
    # stop al 10% bajo entry
    stop = trade.entry_price * 0.90
    closed = t.close_trade("ADA/USDT", stop, reason="SL_HIT")
    assert closed.pnl_usd <= -9.5 and closed.pnl_usd >= -10.5, \
        f"perdida por stop debe ser ~10$, fue {closed.pnl_usd}"


def test_capital_recalcula_after_loss():
    """Tras perder 10$, el 10% se aplica sobre 990$ (no 1000$)."""
    t = Trader(initial_capital=1000.0, leverage=1, risk_per_trade_pct=10.0)
    t.open_trade("ADA/USDT", price=0.1646, direction="BUY")
    t.close_trade("ADA/USDT", 0.1646 * 0.90, reason="SL_HIT")
    # Nueva posicion sobre capital restante 990$ => ~99$
    # daily_loss_limit=100 (10% de 1000$) simula la config real del bot
    t2 = Trader(initial_capital=t.risk.current_capital, leverage=1,
                risk_per_trade_pct=10.0, daily_loss_limit=100.0)
    trade2 = t2.open_trade("SOL/USDT", price=150.0, direction="BUY")
    assert 94 <= trade2.size <= 104, f"size debe ser ~99$, fue {trade2.size}"
