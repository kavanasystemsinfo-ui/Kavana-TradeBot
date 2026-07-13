"""Tests del módulo de configuración."""
import os
from pathlib import Path
import pytest
from src.config import Config, getenv_or_raise


class TestConfig:
    """La configuración debe cargar valores por defecto sensatos."""

    def test_default_exchange(self):
        assert Config.EXCHANGE_ID == "kucoin"

    def test_default_symbols(self):
        assert "BTC/USDT" in Config.SYMBOLS
        assert "ETH/USDT" in Config.SYMBOLS

    def test_default_leverage(self):
        # Modelo KAVANA: sin apalancamiento (riesgo real = riesgo de posicion)
        assert Config.LEVERAGE == 1

    def test_default_capital(self):
        assert Config.INITIAL_CAPITAL == 1000.0

    def test_default_timeframe(self):
        assert Config.TIMEFRAME == "5m"

    def test_default_risk_params(self):
        # Modelo KAVANA: posicion 10% capital, stop 10% fijo, 1x
        assert Config.STOP_LOSS_PCT == 10
        assert Config.TAKE_PROFIT_PCT == 15
        assert Config.MAX_DURATION_MIN == 120
        assert Config.RISK_PER_TRADE_PCT == 10.0

    def test_db_path_is_absolute(self):
        assert isinstance(Config.DB_PATH, Path)
        assert str(Config.DB_PATH).endswith("data/trading.db")


class TestGetenvOrRaise:
    """getenv_or_raise debe lanzar error si falta la variable."""

    def test_raises_on_missing_var(self):
        with pytest.raises(ValueError, match="Falta variable de entorno"):
            getenv_or_raise("VARIABLE_QUE_NO_EXISTE_12345")

    def test_returns_value_when_set(self):
        os.environ["__TEST_VAR__"] = "test_value"
        assert getenv_or_raise("__TEST_VAR__") == "test_value"
        del os.environ["__TEST_VAR__"]
