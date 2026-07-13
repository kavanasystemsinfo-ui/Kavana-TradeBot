"""Exportación de trades — CSV y Google Sheets (formato legacy compatible)."""
from __future__ import annotations

import csv
import io
from typing import Optional

from src.trader import Trade, TradeStatus


class Exporter:
    """Exporta trades a CSV y Google Sheets vía Apps Script webhook."""

    @staticmethod
    def _build_payload(
        trade: Trade,
        sheet: str = "REAL",
        leverage: int = 10,
        capital: float = 1000,
        initial_capital: float = 1000,
    ) -> dict:
        """Construye payload en el formato exacto del viejo sistema (paper_trader.py)."""
        if trade.status == TradeStatus.CLOSED:
            resultado = "WIN ✅" if trade.pnl_usd > 0 else "LOSE ❌"
            precio_salida = trade.entry_price * (1 + trade.pnl_pct / 100 / leverage)
        else:
            resultado = "ABIERTA ⏳"
            precio_salida = trade.entry_price

        return {
            "sheet": sheet,
            "activo": trade.symbol,
            "estrategia": "MOMENTUM_BREAKOUT",
            "direccion": trade.direction,
            "precio_entrada": trade.entry_price,
            "precio_salida": round(precio_salida, 2),
            "inversion": trade.size,
            "apalancamiento": leverage,
            "resultado": resultado,
            "pnl_neto": trade.pnl_usd,
            "capital_actual": round(capital, 2),
            "capital_inicial": initial_capital,
        }

    @staticmethod
    def to_csv(trades: list[Trade]) -> str:
        """Convierte trades a CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "symbol", "direction", "entry_price", "size",
            "pnl_usd", "pnl_pct", "close_reason", "status",
        ])
        for t in trades:
            writer.writerow([
                t.id, t.symbol, t.direction, t.entry_price, t.size,
                t.pnl_usd, t.pnl_pct, t.close_reason, t.status.value,
            ])
        return output.getvalue()

    @staticmethod
    async def to_google_sheets(
        trades: list[Trade],
        webhook_url: str,
        sheet: str = "REAL",
        leverage: int = 10,
        capital: float = 1000,
        initial_capital: float = 1000,
    ) -> bool:
        """Envía trades a Google Sheets (formato legacy)."""
        if not webhook_url:
            return False

        import aiohttp

        for trade in trades:
            payload = Exporter._build_payload(
                trade, sheet=sheet, leverage=leverage,
                capital=capital, initial_capital=initial_capital,
            )
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=payload, timeout=10) as resp:
                        if resp.status != 200:
                            return False
            except Exception:
                return False
        return True
