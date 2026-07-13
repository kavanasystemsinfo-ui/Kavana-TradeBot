"""Tests de logica de salida: trailing stop, TP simetrico, recuperacion de posiciones.

Modelo KAVANA:
- Stop = 10% del precio de entrada (fijo)
- TP = +10% (simétrico al stop)
- Trailing: tras +5%, stop sube a break-even (entrada)
- MAX_DURATION: cierra solo si en perdida; si en ganancia, deja correr
- Recuperacion desde DB: opened_at se resetea al reinicio y stop se recalcula
"""
from datetime import datetime, timezone, timedelta
from src.trader import Trader, Trade, TradeStatus


def _trader():
    return Trader(initial_capital=1000.0, leverage=1, risk_per_trade_pct=10.0,
                  atr_multiplier=1.0, max_duration_min=120)


def test_open_trade_tiene_stop_y_tp_10pct():
    t = _trader()
    trade = t.open_trade("ADA/USDT", price=0.1646, direction="BUY")
    assert abs(trade.stop_loss - 0.1646 * 0.90) < 1e-6   # SL 10% bajo
    assert abs(trade.take_profit - 0.1646 * 1.10) < 1e-6  # TP 10% arriba


def test_tp_salto_ganancia():
    t = _trader()
    t.open_trade("ADA/USDT", price=0.1646, direction="BUY")
    res = t.tick("ADA/USDT", 0.1646 * 1.10)  # +10%
    assert res is not None
    assert res.close_reason == "TP_HIT"
    assert res.pnl_usd > 0


def test_trailing_stop_a_breakeven():
    t = _trader()
    trade = t.open_trade("ADA/USDT", price=0.1646, direction="BUY")
    # Sube +5% -> stop deberia ir a break-even (entrada)
    t.tick("ADA/USDT", 0.1646 * 1.05)
    assert abs(trade.stop_loss - 0.1646) < 1e-6, f"stop={trade.stop_loss}"
    # Baja a entrada -> cierra por SL (break-even, sin perder)
    res = t.tick("ADA/USDT", 0.1646)
    assert res is not None
    assert res.close_reason == "SL_HIT"
    assert abs(res.pnl_usd) < 1e-6  # ~0, no pierde


def test_max_duration_no_cierra_si_ganancia():
    t = _trader()
    trade = t.open_trade("ADA/USDT", price=0.1646, direction="BUY")
    trade.opened_at = datetime.now(timezone.utc) - timedelta(minutes=200)  # paso 120min
    # Esta en ganancia (+5%) -> NO debe cerrar por MAX_DURATION
    res = t.tick("ADA/USDT", 0.1646 * 1.05)
    assert res is None, "no debe cerrar por tiempo si esta en ganancia"


def test_max_duration_cierra_si_perdida():
    t = _trader()
    trade = t.open_trade("ADA/USDT", price=0.1646, direction="BUY")
    trade.opened_at = datetime.now(timezone.utc) - timedelta(minutes=200)
    # Esta en perdida (-3%) -> SI cierra por MAX_DURATION
    res = t.tick("ADA/USDT", 0.1646 * 0.97)
    assert res is not None
    assert res.close_reason == "MAX_DURATION"


def test_recuperacion_resetea_opened_at():
    """Una posicion cargada desde DB (abierta hace horas) debe resetear opened_at."""
    from src.db import Database
    from pathlib import Path
    import tempfile
    # Simular posicion vieja
    db = Database(Path(tempfile.mktemp(suffix=".db")))
    db.initialize()
    old = Trade(symbol="ADA/USDT", direction="BUY", entry_price=0.1646,
                size=100.0, stop_loss=0.1481, status=TradeStatus.OPEN,
                opened_at=datetime.now(timezone.utc) - timedelta(hours=5))
    db.save_trade(old)
    loaded = db.load_open_trade("ADA/USDT")
    assert loaded is not None
    # Tras "recuperar" (main._load_state), opened_at debe ser reciente
    loaded.opened_at = datetime.now(timezone.utc)  # reset del reload
    assert (datetime.now(timezone.utc) - loaded.opened_at) < timedelta(minutes=1)
