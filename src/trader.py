"""Trader — Paper trading con Risk Manager profesional."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from src.risk import RiskManager


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class RiskError(Exception):
    """Error controlado de gestión de riesgo."""


@dataclass
class Trade:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    symbol: str = ""
    direction: str = ""
    entry_price: float = 0.0
    size: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    status: TradeStatus = TradeStatus.OPEN
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    close_reason: str = ""
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    # Metadatos de mercado en apertura
    vwap: float = 0.0
    atr: float = 0.0
    funding_rate: float = 0.0
    btc_dominance: float = 0.0


class Trader:
    """Paper trader con Risk Manager integrado.

    Usa RiskManager para:
    - Tamaño de posición basado en riesgo fijo (% del capital)
    - Stop loss dinámico basado en ATR
    - Fractional Kelly para optimizar sizing
    - Límite diario de pérdidas
    - Máximo de posiciones concurrentes
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        leverage: int = 1,
        risk_per_trade_pct: float = 10.0,
        atr_multiplier: float = 1.0,
        max_duration_min: int = 120,
        daily_loss_limit: float | None = None,
    ):
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.max_duration_min = max_duration_min
        self.positions: dict[str, Trade] = {}
        self.history: list[Trade] = []

        # Risk Manager profesional
        self.risk = RiskManager(
            initial_capital=initial_capital,
            risk_per_trade_pct=risk_per_trade_pct,
            atr_multiplier=atr_multiplier,
            daily_loss_limit=daily_loss_limit or initial_capital * 0.10,
        )

    def open_trade(
        self,
        symbol: str,
        price: float,
        direction: str,
        size: float | None = None,
        atr: float = 0.0,
        vwap: float = 0.0,
        funding_rate: float = 0.0,
        btc_dominance: float = 50.0,
    ) -> Trade:
        """Abre posición con el modelo KAVANA:

        - Posición = %risk del capital (10% por defecto).
        - Stop = 10% del precio de entrada (fijo, sin ATR ni palanca).
        - Si el stop salta, la perdida máxima = 10% de la posición.
        """
        if symbol in self.positions:
            raise RiskError(f"Ya tienes posición abierta en {symbol}")

        # Stop fijo al 10% del precio (modelo de Jorge: 10% de perdida máxima)
        stop_pct = 0.10
        tp_pct = 0.10  # TP simétrico al stop (cierra ganando 10%)
        if direction == "BUY":
            stop_price = price * (1 - stop_pct)
            tp_price = price * (1 + tp_pct)
        else:
            stop_price = price * (1 + stop_pct)
            tp_price = price * (1 - tp_pct)

        # Riesgo por trade = %risk del capital actual (para el límite diario)
        risk_amount = self.risk.current_capital * (self.risk.risk_per_trade_pct / 100)

        # Validar límite diario y de posiciones
        # risk_amount = $ en riesgo de este trade (ya en dólares)
        if not self.risk.can_trade(risk_amount):
            raise RiskError("Límite de riesgo diario o de posiciones alcanzado")

        # Tamaño = %risk del capital actual (sin apalancamiento)
        if size is None:
            position_size = self.risk.calculate_position_size(price, stop_price)
        else:
            position_size = size

        # Sin palanca: el tamaño nunca supera el capital disponible
        position_size = min(position_size, self.risk.current_capital)

        if position_size <= 0:
            raise RiskError("Tamaño de posición inválido")

        trade = Trade(
            symbol=symbol,
            direction=direction,
            entry_price=price,
            size=round(position_size, 2),
            stop_loss=round(stop_price, 6),
            take_profit=round(tp_price, 6),
            vwap=vwap,
            atr=atr,
            funding_rate=funding_rate,
            btc_dominance=btc_dominance,
        )
        self.positions[symbol] = trade
        self.risk.open_trades_count += 1
        return trade

    def close_trade(
        self,
        symbol: str,
        price: float,
        reason: str = "MANUAL",
    ) -> Trade:
        """Cierra posición y registra PnL en Risk Manager."""
        trade = self.positions.pop(symbol)

        if trade.direction == "BUY":
            pnl_pct = (price - trade.entry_price) / trade.entry_price * 100 * self.leverage
        else:
            pnl_pct = (trade.entry_price - price) / trade.entry_price * 100 * self.leverage

        pnl_usd = trade.size * (pnl_pct / 100)

        trade.status = TradeStatus.CLOSED
        trade.pnl_usd = round(pnl_usd, 2)
        trade.pnl_pct = round(pnl_pct, 2)
        trade.close_reason = reason
        trade.closed_at = datetime.now(timezone.utc)

        # Registrar en Risk Manager
        self.risk.record_trade(pnl_usd)
        self.history.append(trade)
        return trade

    def tick(self, symbol: str, current_price: float) -> Optional[Trade]:
        """Evalúa una posición abierta."""
        trade = self.positions.get(symbol)
        if not trade:
            return None

        # Stop loss
        if trade.direction == "BUY" and current_price <= trade.stop_loss:
            return self.close_trade(symbol, current_price, "SL_HIT")
        if trade.direction == "SELL" and current_price >= trade.stop_loss:
            return self.close_trade(symbol, current_price, "SL_HIT")

        # Take profit (simétrico al 10%)
        if trade.take_profit > 0:
            if trade.direction == "BUY" and current_price >= trade.take_profit:
                return self.close_trade(symbol, current_price, "TP_HIT")
            if trade.direction == "SELL" and current_price <= trade.take_profit:
                return self.close_trade(symbol, current_price, "TP_HIT")

        # Trailing stop: tras +5% (en direccion del trade), sube el stop a break-even
        if trade.direction == "BUY":
            gain_pct = (current_price - trade.entry_price) / trade.entry_price
        else:
            gain_pct = (trade.entry_price - current_price) / trade.entry_price
        if gain_pct >= 0.05 and trade.stop_loss < trade.entry_price:
            # Mueve el stop a entrada (break-even): nunca se pasa de ganar a perder
            trade.stop_loss = round(trade.entry_price, 6)

        # Duración máxima: solo cierra por tiempo si esta en perdida.
        # Si esta en ganancia, deja correr (el TP o trailing lo sacaran).
        elapsed = datetime.now(timezone.utc) - trade.opened_at
        if elapsed > timedelta(minutes=self.max_duration_min):
            if gain_pct < 0:  # en perdida -> cierra
                return self.close_trade(symbol, current_price, "MAX_DURATION")
            # en ganancia -> extiende la ventana para no cortar un trade ganador
            trade.opened_at = datetime.now(timezone.utc)

        return None

    def get_performance(self) -> dict:
        """Métricas de rendimiento desde el histórico."""
        total = len(self.history)
        wins = sum(1 for t in self.history if t.pnl_usd > 0)
        losses = sum(1 for t in self.history if t.pnl_usd <= 0)
        cumulative_pnl = sum(t.pnl_usd for t in self.history)
        roi = ((self.risk.current_capital - self.initial_capital) / self.initial_capital) * 100

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round((wins / total * 100) if total else 0, 1),
            "roi_pct": round(roi, 2),
            "cumulative_pnl_usd": round(cumulative_pnl, 2),
            "capital": round(self.risk.current_capital, 2),
            "daily_loss": round(self.risk.daily_loss, 2),
            "max_positions": self.risk.max_open_trades,
        }
