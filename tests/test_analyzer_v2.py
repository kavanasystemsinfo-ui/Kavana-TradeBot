"""Tests del analizador mejorado — VWAP, tendencia, funding rates."""
import pytest
from unittest.mock import MagicMock
from src.analyzer import Analyzer


@pytest.fixture
def analyzer():
    return Analyzer()


class TestVWAP:
    def test_calculates_vwap(self, analyzer):
        candles = [
            {"high": 101, "low": 99, "close": 100, "volume": 1000},
            {"high": 102, "low": 100, "close": 101, "volume": 2000},
            {"high": 103, "low": 101, "close": 102, "volume": 1500},
        ]
        vwap = analyzer.vwap(candles)
        # VWAP = sum(price*volume) / sum(volume)
        # price = (high+low+close)/3 para cada candle
        assert vwap > 0

    def test_trend_filter(self, analyzer):
        # Precio por encima de VWAP = tendencia alcista
        signal = analyzer.trend_filter(current_price=110.0, vwap=100.0)
        assert signal["trend"] == "bullish"
        assert signal["vwap_distance"] > 0

    def test_trend_filter_bearish(self, analyzer):
        signal = analyzer.trend_filter(current_price=90.0, vwap=100.0)
        assert signal["trend"] == "bearish"

    def test_trend_filter_neutral(self, analyzer):
        # Precio muy cerca del VWAP (<0.15%) = sin tendencia clara
        signal = analyzer.trend_filter(current_price=100.05, vwap=100.0)
        assert signal["trend"] == "neutral"


class TestMarketRegime:
    def test_high_funding_warning(self, analyzer):
        rating = analyzer.funding_risk_rating(0.1)  # 0.1% funding = muy alto
        assert rating == "extreme"

    def test_normal_funding(self, analyzer):
        rating = analyzer.funding_risk_rating(0.01)  # 0.01% = normal
        assert rating == "normal"

    def test_btc_dominance_filter(self, analyzer):
        # BTC.D > 55% + BTC price up = altcoins débiles
        advice = analyzer.btc_dominance_advice(dominance=58.0, btc_trend="up")
        assert "avoid" in advice.lower()
