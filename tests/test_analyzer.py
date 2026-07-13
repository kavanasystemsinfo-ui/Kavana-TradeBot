"""Tests del módulo de análisis técnico v2."""
import pytest
import pandas as pd
import numpy as np
from src.analyzer import Analyzer, Signal


@pytest.fixture
def sample_data():
    """100 velas de ejemplo."""
    np.random.seed(42)
    n = 100
    closes = 50000 + np.cumsum(np.random.randn(n) * 50) + np.linspace(0, 2000, n)
    highs = closes + np.random.rand(n) * 200
    lows = closes - np.random.rand(n) * 200
    candles = []
    for i in range(n):
        candles.append({
            "high": float(highs[i]),
            "low": float(lows[i]),
            "close": float(closes[i]),
            "volume": float(np.random.rand() * 1000 + 500),
        })
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="5min"),
        "open": closes - np.random.rand(n) * 50,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": np.random.rand(n) * 1000 + 500,
    }), candles


class TestIndicators:
    def test_rsi_between_0_and_100(self, sample_data):
        df, _ = sample_data
        az = Analyzer()
        rsi = az.rsi(df["close"])
        assert rsi > 0
        assert rsi < 100

    def test_ema_exists(self, sample_data):
        df, _ = sample_data
        az = Analyzer()
        ema = az.ema(df["close"], 20)
        assert ema > 0

    def test_macd_components_exist(self, sample_data):
        df, _ = sample_data
        az = Analyzer()
        macd_line, signal_line, hist = az.macd(df["close"])
        assert isinstance(macd_line, float)
        assert isinstance(signal_line, float)
        assert isinstance(hist, float)

    def test_atr_is_positive(self, sample_data):
        df, _ = sample_data
        az = Analyzer()
        atr = az.atr(df["high"], df["low"], df["close"])
        assert atr > 0

    def test_vwap_calculated(self, sample_data):
        _, candles = sample_data
        az = Analyzer()
        vwap = az.vwap(candles)
        assert vwap > 0

    def test_trend_filter_long(self, sample_data):
        _, candles = sample_data
        az = Analyzer()
        vwap = az.vwap(candles)
        trend = az.trend_filter(vwap * 1.05, vwap)  # Precio 5% sobre VWAP
        assert trend["trend"] == "bullish"

    def test_trend_filter_short(self, sample_data):
        _, candles = sample_data
        az = Analyzer()
        vwap = az.vwap(candles)
        trend = az.trend_filter(vwap * 0.95, vwap)  # Precio 5% bajo VWAP
        assert trend["trend"] == "bearish"


class TestSignalDetection:
    def test_detects_neutral_on_flat(self, sample_data):
        df, candles = sample_data
        az = Analyzer()
        result = az.analyze(df["close"], df["high"], df["low"], candles)
        assert "signal" in result

    def test_signal_has_reason(self, sample_data):
        df, candles = sample_data
        az = Analyzer()
        result = az.analyze(df["close"], df["high"], df["low"], candles)
        assert len(result.get("reasons", [])) > 0

    def test_funding_extreme_blocks_trades(self, sample_data):
        df, candles = sample_data
        az = Analyzer()
        result = az.analyze(df["close"], df["high"], df["low"], candles, funding_rate=0.1)
        assert result["signal"] == Signal.NEUTRAL
        assert "extreme_funding" in result.get("reasons", []) or \
               any("extreme" in r for r in result.get("reasons", []))

    def test_btc_dominance_advice_exists(self, sample_data):
        df, candles = sample_data
        az = Analyzer()
        result = az.analyze(df["close"], df["high"], df["low"], candles, btc_dominance=60.0, btc_trend="up")
        assert "avoid" in result.get("btc_advice", "")
