"""Tests del módulo de base de datos SQLite."""
import pytest
import tempfile
from pathlib import Path
from src.db import Database
from src.trader import Trade, TradeStatus


@pytest.fixture
def db():
    """Base de datos temporal para cada test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    database = Database(db_path)
    database.initialize()
    yield database
    db_path.unlink(missing_ok=True)


class TestDatabaseInit:
    """La BD debe crearse con las tablas correctas."""

    def test_creates_db_file(self, db):
        assert db.path.exists()

    def test_creates_trades_table(self, db):
        row = db.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        assert row is not None


class TestTradePersistence:
    """Los trades deben persistirse y recuperarse."""

    def test_saves_and_loads_trade(self, db):
        trade = Trade(id="test1", symbol="BTC/USDT", direction="BUY", entry_price=50000, size=100)
        db.save_trade(trade)
        loaded = db.load_open_trade("BTC/USDT")
        assert loaded is not None
        assert loaded.id == "test1"
        assert loaded.symbol == "BTC/USDT"
        assert loaded.entry_price == 50000

    def test_returns_none_for_missing_trade(self, db):
        loaded = db.load_open_trade("NONEXISTENT")
        assert loaded is None

    def test_closes_trade_in_db(self, db):
        trade = Trade(id="test2", symbol="ETH/USDT", direction="BUY", entry_price=3000, size=100)
        db.save_trade(trade)
        db.close_trade("ETH/USDT", pnl_usd=500, pnl_pct=15.0, reason="TP_HIT")
        loaded = db.load_open_trade("ETH/USDT")
        assert loaded is None  # Ya no está abierta

    def test_loads_trade_history(self, db):
        for i, sym in enumerate(["BTC", "ETH", "SOL"]):
            t = Trade(id=f"hist{i}", symbol=f"{sym}/USDT", direction="BUY", entry_price=100 * (i + 1), size=100)
            db.save_trade(t)
            db.close_trade(f"{sym}/USDT", pnl_usd=50, pnl_pct=5.0, reason="TP_HIT")
        history = db.load_history(limit=10)
        assert len(history) == 3

    def test_empty_history(self, db):
        history = db.load_history(limit=10)
        assert history == []


class TestConfigPersistence:
    """La configuración debe persistirse en BD."""

    def test_saves_and_loads_config(self, db):
        config = {"leverage": 10, "stop_loss_pct": 12, "max_duration_min": 120}
        db.save_config(config)
        loaded = db.load_config()
        assert loaded is not None
        assert loaded["leverage"] == 10

    def test_loads_empty_config(self, db):
        config = db.load_config()
        assert config == {}

    def test_updates_existing_config(self, db):
        db.save_config({"leverage": 5})
        db.save_config({"leverage": 10, "stop_loss_pct": 15})
        loaded = db.load_config()
        assert loaded["leverage"] == 10
        assert loaded["stop_loss_pct"] == 15
