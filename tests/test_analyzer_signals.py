"""Tests de generación de señales — reproducen y previenen el bug de lógica contradictoria.

Contexto: la lógica original exigía condiciones mutuamente excluyentes
(tendencia alcista + RSI sobrevendido), por lo que analyze() devolvía siempre
NEUTRAL. Estos tests fijan la lógica correcta: la tendencia (VWAP) marca la
DIRECCIÓN permitida y el momentum (RSI + MACD) confirma la entrada EN ESA
MISMA dirección.

Los datos de prueba imitan mercados reales: tendencias en ZIGZAG (impulsos +
retrocesos), no líneas rectas. Una línea recta hace que el VWAP persiga al
precio (tendencia neutra) y lleva el RSI a extremos (0/100), lo que no
representa una entrada real.
"""
import numpy as np
import pandas as pd
import pytest

from src.analyzer import Analyzer, Signal


def _zigzag(start: float, up: float, down: float, base_len: int = 80, ramp_len: int = 20):
    """Genera una tendencia en zigzag: base plana + rampa con impulsos y retrocesos.

    up/down positivos → tendencia alcista. Invertir signos → bajista.
    """
    closes = [start] * base_len
    price = start
    for i in range(ramp_len):
        price += up if i % 2 == 0 else down
        closes.append(price)
    closes = np.array(closes, dtype=float)
    highs = closes + 20
    lows = closes - 20
    candles = [
        {"high": float(highs[i]), "low": float(lows[i]), "close": float(closes[i]), "volume": 1000.0}
        for i in range(len(closes))
    ]
    return pd.Series(closes), pd.Series(highs), pd.Series(lows), candles


def _uptrend():
    # Impulsos +500 / retrocesos -150 → sube en zigzag, RSI en banda media-alta,
    # precio claramente por encima del VWAP de 20 velas.
    return _zigzag(start=50000, up=500, down=-150)


def _downtrend():
    # Impulsos -500 / retrocesos +150 → baja en zigzag.
    return _zigzag(start=60000, up=-500, down=150)


@pytest.fixture
def analyzer():
    return Analyzer()


class TestSignalGeneration:
    def test_uptrend_generates_buy(self, analyzer):
        """Un mercado alcista en zigzag DEBE producir una señal BUY (no NEUTRAL)."""
        closes, highs, lows, candles = _uptrend()
        result = analyzer.analyze(closes, highs, lows, candles)
        assert result["signal"] == Signal.BUY, (
            f"Mercado alcista debería dar BUY, dio {result['signal']} "
            f"(rsi={result.get('rsi'):.1f}, trend={result.get('trend', {}).get('trend')}, "
            f"vwap_dist={result.get('trend', {}).get('vwap_distance'):.4f})"
        )

    def test_downtrend_generates_sell(self, analyzer):
        """Un mercado bajista en zigzag DEBE producir una señal SELL (no NEUTRAL)."""
        closes, highs, lows, candles = _downtrend()
        result = analyzer.analyze(closes, highs, lows, candles)
        assert result["signal"] == Signal.SELL, (
            f"Mercado bajista debería dar SELL, dio {result['signal']} "
            f"(rsi={result.get('rsi'):.1f}, trend={result.get('trend', {}).get('trend')}, "
            f"vwap_dist={result.get('trend', {}).get('vwap_distance'):.4f})"
        )

    def test_extreme_funding_still_blocks_buy(self, analyzer):
        """El filtro de funding extremo sigue bloqueando incluso en tendencia alcista."""
        closes, highs, lows, candles = _uptrend()
        result = analyzer.analyze(closes, highs, lows, candles, funding_rate=0.1)
        assert result["signal"] == Signal.NEUTRAL

    def test_flat_market_stays_neutral(self, analyzer):
        """Un mercado plano (sin tendencia sobre VWAP) sigue siendo NEUTRAL."""
        closes, highs, lows, candles = _zigzag(start=50000, up=30, down=-25)
        result = analyzer.analyze(closes, highs, lows, candles)
        assert result["signal"] == Signal.NEUTRAL
