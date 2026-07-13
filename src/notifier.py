"""Notificaciones vía Telegram."""
from __future__ import annotations


class Notifier:
    """Envía notificaciones de trading a Telegram."""

    def __init__(self, token: str, chat_id: str):
        if not token:
            raise ValueError("Se requiere token de Telegram")
        if not chat_id:
            raise ValueError("Se requiere chat_id de Telegram")
        self.token = token
        self.chat_id = chat_id

    async def _bot(self):
        from telegram import Bot
        return Bot(token=self.token)

    async def send_message(self, text: str) -> bool:
        """Envía un mensaje a Telegram. Retorna True si tuvo éxito."""
        try:
            bot = await self._bot()
            await bot.send_message(chat_id=self.chat_id, text=text, parse_mode="HTML")
            return True
        except Exception:
            return False

    async def send_trade_open(
        self, symbol: str, direction: str, price: float, size: float, sl_pct: float
    ) -> bool:
        msg = self.format_trade_open(symbol, direction, price, size, sl_pct)
        return await self.send_message(msg)

    async def send_trade_close(
        self, symbol: str, exit_price: float, pnl_usd: float, pnl_pct: float, reason: str
    ) -> bool:
        msg = self.format_trade_close(symbol, exit_price, pnl_usd, pnl_pct, reason)
        return await self.send_message(msg)

    async def send_status(
        self, perf: dict, positions: list[dict]
    ) -> bool:
        msg = self.format_status(perf, positions)
        return await self.send_message(msg)

    # --- Formateo ---

    @staticmethod
    def format_trade_open(symbol: str, direction: str, price: float, size: float, sl_pct: float) -> str:
        emoji = "🟢" if direction == "BUY" else "🔴"
        return (
            f"{emoji} <b>POSICIÓN ABIERTA</b>\n"
            f"<b>{symbol}</b> | {direction}\n"
            f"💰 Entrada: ${price:,.2f}\n"
            f"📏 Tamaño: ${size:,.0f}\n"
            f"🛑 SL: {sl_pct:.0f}%"
        )

    @staticmethod
    def format_trade_close(symbol: str, exit_price: float, pnl_usd: float, pnl_pct: float, reason: str) -> str:
        emoji = "🟢" if pnl_usd > 0 else "🔴"
        return (
            f"{emoji} <b>POSICIÓN CERRADA</b>\n"
            f"<b>{symbol}</b>\n"
            f"💰 Salida: ${exit_price:,.2f}\n"
            f"📊 PnL: <b>{pnl_usd:+.2f}$ ({pnl_pct:+.2f}%)</b>\n"
            f"📝 Razón: {reason}"
        )

    @staticmethod
    def format_status(perf: dict, positions: list[dict]) -> str:
        lines = [
            "📊 <b>ESTADO DE CUENTA</b>",
            f"💰 Capital: <b>${perf['capital']:,.2f}</b>",
            f"📈 ROI: <b>{perf['roi_pct']:+.2f}%</b>",
            f"🎯 Win Rate: <b>{perf['win_rate']}%</b> ({perf['wins']}W/{perf['losses']}L)",
            f"🔄 Trades: {perf['total_trades']}",
            f"💵 PnL Neto: <b>{perf['cumulative_pnl_usd']:+.2f}$</b>",
        ]
        if positions:
            lines.append("")
            lines.append("📝 <b>ABIERTAS:</b>")
            for p in positions:
                lines.append(f"• {p['symbol']} @ {p.get('entry', '?')} ({p.get('pnl_pct', 0):+.1f}%)")
        return "\n".join(lines)
