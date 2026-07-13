"""YAGNI: el bot NO debe tener nada de Polymarket (contaminaba el Dashboard)."""
import importlib
import pytest


def test_polymarket_tracker_no_existe():
    """El modulo polymarket_tracker debe haber sido eliminado."""
    with pytest.raises(ImportError):
        importlib.import_module("src.polymarket_tracker")


def test_main_no_importa_polymarket():
    import src.main as m
    assert not hasattr(m, "WalletTracker")
    assert not hasattr(m, "TRADERS")


def test_main_no_tiene_scan_polymarket():
    import src.main as m
    assert not hasattr(m.TradingLoop, "_scan_polymarket")


def test_webhook_no_sirve_polymarket_csv():
    import src.webhook as w
    # El handler de polymarket no debe existir
    assert not hasattr(w, "handle_csv_polymarket")
