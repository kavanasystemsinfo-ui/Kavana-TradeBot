"""Gestión de riesgo profesional — Basado en los informes de trading.
Implementa: Riesgo fijo 1-2%, ATR stops, Kelly Criterion, límites diarios."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("kavana.risk")


class RiskError(Exception):
    """Error controlado de gestión de riesgo."""


class RiskManager:
    """Gestor de riesgo profesional.

    Inspirado en:
    - Modelo de Riesgo Fijo (1-2% por trade)
    - Modelo Basado en Volatilidad (ATR)
    - Criterio de Kelly (Fractional Kelly)
    - Límites diarios de pérdida
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        risk_per_trade_pct: float = 1.0,
        max_risk_pct: float = 2.0,
        atr_multiplier: float = 2.0,
        kelly_fraction: float = 0.25,
        daily_loss_limit: float = 0.0,
        max_open_trades: int = 3,
    ):
        if initial_capital <= 0:
            raise ValueError("El capital inicial debe ser positivo")
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_risk_pct = max_risk_pct
        self.atr_multiplier = atr_multiplier
        self.kelly_pct = kelly_fraction
        self.daily_loss_limit = daily_loss_limit or initial_capital * 0.10  # 10% por defecto
        self.max_open_trades = max_open_trades

        # Estado dinámico
        self.current_capital = initial_capital
        self.daily_loss = 0.0
        self.open_trades_count = 0
        self.trade_history: list[dict] = []

    def calculate_position_size(self, entry_price: float, stop_price: float) -> float:
        """Calcula el tamaño de posición = 10% del capital actual.

        Modelo KAVANA: la posición es SIEMPRE el %risk del capital
        (por defecto 10%), independiente de la distancia al stop.
        El stop (10% del precio) garantiza que, si salta, la perdida
        es el 10% de la posición (p.ej. 1000$->100$->10$ de perdida).
        """
        if entry_price <= 0 or stop_price <= 0:
            raise RiskError("Precios inválidos")

        # Posición = %risk del capital actual (modelo de Jorge: 10% fijo)
        position_size = self.current_capital * (self.risk_per_trade_pct / 100.0)

        # Limitar al capital disponible (sin apalancamiento)
        max_size = self.current_capital
        return min(position_size, max_size)

    def atr_stop(self, entry_price: float, atr: float, multiplier: Optional[float] = None) -> float:
        """Calcula stop loss basado en ATR (Average True Range).

        Para LONG: stop = entry - (ATR * multiplier)
        """
        mult = multiplier or self.atr_multiplier
        return entry_price - (atr * mult)

    def kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: Optional[float] = None,
    ) -> float:
        """Calcula el porcentaje óptimo según Kelly Criterion.

        f* = (WR * avg_win - (1-WR) * avg_loss) / (avg_win * avg_loss) simplificado
        Kelly completo: f* = WR - (1-WR) / (avg_win/avg_loss)

        Returns:
            Fracción del capital a arriesgar (Fractional Kelly aplicado)
        """
        if avg_loss == 0:
            return 0

        r = avg_win / avg_loss  # Ratio beneficio/pérdida
        kelly = win_rate - ((1 - win_rate) / r)

        # Fractional Kelly: usar solo un porcentaje para reducir varianza
        frac = fraction or self.kelly_pct
        return max(0, kelly * frac)

    def can_trade(self, risk_amount: float) -> bool:
        """Verifica si se puede abrir un nuevo trade.

        Comprueba:
        - Pérdida diaria acumulada (solo pérdidas reales) no supera el límite
        - Máximo de trades abiertos concurrentes

        El riesgo por trade ya está acotado por el stop (10% de la posición),
        así que no se suma al límite diario.
        """
        if self.daily_loss >= self.daily_loss_limit:
            logger.warning("Límite diario de pérdidas alcanzado: %.2f/%.2f",
                           self.daily_loss, self.daily_loss_limit)
            return False
        if self.open_trades_count >= self.max_open_trades:
            logger.warning("Máximo de trades abiertos alcanzado: %d", self.max_open_trades)
            return False
        return True

    def record_trade(self, pnl: float) -> None:
        """Registra un trade cerrado y actualiza el estado."""
        if pnl < 0:
            self.daily_loss += abs(pnl)

        self.current_capital += pnl
        self.open_trades_count = max(0, self.open_trades_count - 1)

        self.trade_history.append({
            "pnl": pnl,
            "capital_after": self.current_capital,
        })
        logger.info("Trade cerrado. PnL: %.2f | Capital: %.2f", pnl, self.current_capital)

    def reset_daily(self) -> None:
        """Resetea contadores diarios."""
        self.daily_loss = 0.0
        logger.info("Límites diarios reseteados")

    @property
    def max_capital(self) -> float:
        return self.current_capital
