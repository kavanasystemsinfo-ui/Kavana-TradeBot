"""Tests del limite diario de riesgo y formato de precios del Dashboard."""
from src.risk import RiskManager
from src.dashboard import _fmt_price


def _rm():
    return RiskManager(initial_capital=1000.0, risk_per_trade_pct=10.0, daily_loss_limit=100.0)


def test_primer_trade_permitido():
    """El primer trade (riesgo 100$) debe permitirse con limite 100$ (margen flotacion)."""
    rm = _rm()
    risk_amount = rm.current_capital * (rm.risk_per_trade_pct / 100)  # 100.0
    assert rm.can_trade(risk_amount) is True


def test_daily_limit_blocks_second_trade():
    """Tras 1 trade perdido (100$), no puede arriesgar 100$ mas (limite 100$)."""
    rm = _rm()
    risk_amount = rm.current_capital * (rm.risk_per_trade_pct / 100)
    assert rm.can_trade(risk_amount) is True
    rm.record_trade(-100.0)  # perdio el riesgo maximo del dia
    assert rm.can_trade(risk_amount) is False


def test_fmt_price_small():
    assert _fmt_price(0.16) == "0.16"
    assert _fmt_price(0.16000) == "0.16"


def test_fmt_price_mid():
    assert _fmt_price(75.82) == "75.8200"


def test_fmt_price_large():
    assert _fmt_price(63048.2) == "63,048.20"
