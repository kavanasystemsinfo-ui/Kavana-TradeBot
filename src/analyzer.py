"""Módulo de análisis técnico — indicadores, VWAP, tendencia, funding rates."""
from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("kavana.analyzer")

# Constantes
VWAP_PERIOD = 20
FUNDING_EXTREME = 0.05  # Funding > 0.05% es extremo
FUNDING_HIGH = 0.025    # Funding > 0.025% es alto
BTC_D_HIGH = 55.0       # BTC Dominance > 55% es alta
# Distancia mínima al VWAP para considerar tendencia.
# Calibrado con datos reales de KuCoin (5-15m): el desvío típico BTC/ETH/SOL/ADA/XRP
# es 0.07%-0.25%. Un umbral de 2% (valor original) jamás se alcanzaba → cero señales.
# 0.15% ≈ percentil 75-90 del desvío real: capta tendencia sin dispararse con ruido plano.
TREND_STRENGTH = float(os.getenv("TREND_STRENGTH", "0.0015"))


class Trend(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class Analyzer:
    """Analizador técnico con indicadores profesionales.

    Indicadores disponibles:
    - RSI, MACD, EMAs (original)
    - VWAP + Trend Filter (nuevo)
    - Funding Rate Risk (nuevo)
    - BTC Dominance Filter (nuevo)
    - ATR con stop dinámico (mejorado)
    """

    def __init__(self):
        self.last_analysis: dict[str, Any] = {}

    # === MÉTODOS ORIGINALES (mejorados) ===

    def rsi(self, series: pd.Series, period: int = 14) -> float:
        diff = series.diff()
        gain = diff.where(diff > 0, 0.0).rolling(window=period).mean()
        loss = (-diff.where(diff < 0, 0.0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, float("inf"))
        return float(100 - (100 / (1 + rs)).iloc[-1])

    def macd(self, series: pd.Series) -> tuple[float, float, float]:
        ema12 = series.ewm(span=12).mean()
        ema26 = series.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(macd_line.iloc[-1] - signal_line.iloc[-1])

    def ema(self, series: pd.Series, period: int) -> float:
        return float(series.ewm(span=period).mean().iloc[-1])

    def atr(self, highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14) -> float:
        high_low = highs - lows
        high_close = (highs - closes.shift()).abs()
        low_close = (lows - closes.shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return float(tr.rolling(window=period).mean().iloc[-1])

    # === NUEVOS MÉTODOS PROFESIONALES ===

    def vwap(self, candles: list[dict]) -> float:
        """Calcula VWAP (Volume Weighted Average Price).

        VWAP = sum(typical_price * volume) / sum(volume)
        typical_price = (high + low + close) / 3
        """
        if not candles:
            return 0.0

        total_pv = 0.0
        total_v = 0.0
        for c in candles[-VWAP_PERIOD:]:
            typical = (c["high"] + c["low"] + c["close"]) / 3.0
            vol = c.get("volume", 1)
            total_pv += typical * vol
            total_v += vol

        return total_pv / total_v if total_v > 0 else 0.0

    def trend_filter(self, current_price: float, vwap: float) -> dict:
        """Determina la tendencia basada en la distancia al VWAP.

        Returns:
            dict con trend, distancia, y recomendación
        """
        if vwap == 0:
            return {"trend": "neutral", "vwap_distance": 0, "action": "wait"}

        distance = (current_price - vwap) / vwap

        if distance > TREND_STRENGTH:
            return {"trend": "bullish", "vwap_distance": distance, "action": "long_only"}
        elif distance < -TREND_STRENGTH:
            return {"trend": "bearish", "vwap_distance": distance, "action": "short_only"}
        else:
            return {"trend": "neutral", "vwap_distance": distance, "action": "wait"}

    def funding_risk_rating(self, funding_rate: float) -> str:
        """Evalúa el riesgo basado en la tasa de financiación.

        Funding > 0.05% = extremo (riesgo de liquidación en cascada)
        Funding > 0.025% = alto
        Funding < 0.01% = normal
        """
        if funding_rate > FUNDING_EXTREME:
            return "extreme"
        elif funding_rate > FUNDING_HIGH:
            return "high"
        return "normal"

    def btc_dominance_advice(self, dominance: float, btc_trend: str = "up") -> str:
        """Recomendación basada en BTC Dominance.

        BTC.D > 55% + BTC up = evitar altcoins
        BTC.D < 45% + BTC stable = altseason potencial
        """
        if dominance > BTC_D_HIGH and btc_trend == "up":
            return "avoid_altcoins_btc_absorbing_liquidity"
        elif dominance > BTC_D_HIGH:
            return "caution_btc_dominance_high"
        elif dominance < 45.0:
            return "potential_altseason_monitor_btc_trend"
        return "neutral_market"

    def analyze(
        self,
        close_prices: pd.Series,
        highs: pd.Series,
        lows: pd.Series,
        candles: list[dict],
        funding_rate: float = 0.0,
        btc_dominance: float = 50.0,
        btc_trend: str = "neutral",
    ) -> dict:
        """Análisis completo con todos los indicadores.

        Returns:
            dict con señal, tendencia, métricas de riesgo
        """
        if len(close_prices) < 26:
            return {"signal": Signal.NEUTRAL, "reason": "insufficient_data"}

        # Indicadores originales
        rsi_val = self.rsi(close_prices)
        macd_line, signal_line, hist = self.macd(close_prices)
        atr_val = self.atr(highs, lows, close_prices)

        # Nuevos indicadores profesionales
        vwap_val = self.vwap(candles)
        current_price = float(close_prices.iloc[-1])
        trend = self.trend_filter(current_price, vwap_val)
        funding_risk = self.funding_risk_rating(funding_rate)
        btc_advice = self.btc_dominance_advice(btc_dominance, btc_trend)

        # Señal combinada — la tendencia (VWAP) marca la DIRECCIÓN,
        # el momentum (RSI + MACD) confirma la entrada EN ESA MISMA dirección.
        signal = Signal.NEUTRAL
        reasons = []

        if trend["trend"] == "bullish":
            reasons.append("bullish_trend_vwap")
            # BUY: tendencia alcista + momentum comprador (RSI sobre 50).
            # El MACD por encima de su señal refuerza, pero no es obligatorio.
            if rsi_val >= 50 and rsi_val < 80:
                signal = Signal.BUY
                reasons.append("rsi_momentum_up")
                if hist > 0:
                    reasons.append("macd_confirms_up")
            elif rsi_val >= 80:
                reasons.append("rsi_overbought_skip_late_entry")

        elif trend["trend"] == "bearish":
            reasons.append("bearish_trend_vwap")
            # SELL: tendencia bajista + momentum vendedor (RSI bajo 50).
            if rsi_val <= 50 and rsi_val > 20:
                signal = Signal.SELL
                reasons.append("rsi_momentum_down")
                if hist < 0:
                    reasons.append("macd_confirms_down")
            elif rsi_val <= 20:
                reasons.append("rsi_oversold_skip_late_entry")

        else:
            # Sin tendencia clara: esperar
            reasons.append("no_clear_trend_waiting")
            signal = Signal.NEUTRAL

        # Filtro de funding extremo
        if funding_risk == "extreme":
            signal = Signal.NEUTRAL
            reasons.append("extreme_funding_risk_avoid_trading")

        # Filtro BTC Dominance
        if "avoid" in btc_advice and signal != Signal.NEUTRAL:
            # Si BTC absorbe liquidez, reducir señales en altcoins
            if funding_risk != "extreme":
                reasons.append("btc_dominance_caution")

        result = {
            "signal": signal,
            "rsi": rsi_val,
            "macd_histogram": hist,
            "atr": atr_val,
            "vwap": vwap_val,
            "trend": trend,
            "funding_risk": funding_risk,
            "btc_advice": btc_advice,
            "reasons": reasons,
        }
        self.last_analysis = result
        return result
