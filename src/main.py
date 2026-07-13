"""Bucle principal de trading v2.1 — Risk Manager + Analyzer profesional."""
from __future__ import annotations

from datetime import datetime, timezone

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from src.config import Config
from src.exchange import Exchange
from src.analyzer import Analyzer, Signal
from src.trader import Trader
from src.risk import RiskManager
from src.notifier import Notifier
from src.db import Database
from src.exporter import Exporter
from src.dashboard import Dashboard

logger = logging.getLogger("kavana.trading")


class TradingLoop:
    """Orquesta Exchange → Analyzer v2 (VWAP/funding/BTC.D) → Trader + RiskManager."""

    def __init__(
        self,
        exchange: Exchange,
        analyzer: Analyzer,
        trader: Trader,
        notifier: Notifier,
        database: Optional[Database] = None,
        sheets_url: Optional[str] = None,
        symbols: Optional[list[str]] = None,
        interval_seconds: int = 60,
    ):
        if not all([exchange, analyzer, trader, notifier]):
            raise ValueError("Todos los componentes son requeridos")
        self.exchange = exchange
        self.analyzer = analyzer
        self.trader = trader
        self.notifier = notifier
        self.database = database
        self.sheets_url = sheets_url or Config.APPS_SCRIPT_URL or os.getenv("GOOGLE_SHEET_URL") or Config.WEBHOOK_URL
        self.symbols = symbols or Config.SYMBOLS
        self.interval = interval_seconds
        self._running = False

        # Estado de mercado (se actualiza en cada ciclo)
        self.funding_rate: float = 0.0
        self.btc_dominance: float = 50.0
        self.btc_trend: str = "neutral"

    async def start(self):
        """Inicia el bucle principal."""
        self._running = True
        logger.info("🚀 Bot v2.1 iniciado. Símbolos: %s | Risk: %.1f%%/trade | Trend filter: VWAP",
                     self.symbols, self.trader.risk.risk_per_trade_pct)

        if self.database:
            self._load_state()

        while self._running:
            try:
                self.scan_cycle()
                await self.manage_positions()
                await self._export_dashboard()
            except Exception as e:
                logger.error("Error en ciclo principal: %s", e)

            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False
        logger.info("⏹️ Bot detenido.")

    def scan_cycle(self):
        """Escanea símbolos con analyzer v2. Solo opera en dirección de la tendencia (VWAP)."""
        import time as _time
        for idx, symbol in enumerate(self.symbols):
            try:
                # Respiro anti rate-limit (429) entre símbolos, además del
                # enableRateLimit de ccxt. Evita "Too many requests" de KuCoin.
                if idx > 0:
                    _time.sleep(1.0)
                df = self.exchange.fetch_ohlcv(symbol, limit=100)
                if df is None or df.empty:
                    continue

                closes = df["close"]
                highs = df["high"]
                lows = df["low"]

                # Construir candles desde el DataFrame para VWAP
                candles = []
                for _, row in df.iterrows():
                    candles.append({
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row.get("volume", 1)),
                    })

                # Análisis completo con todos los indicadores
                result = self.analyzer.analyze(
                    close_prices=closes,
                    highs=highs,
                    lows=lows,
                    candles=candles,
                    funding_rate=self.funding_rate,
                    btc_dominance=self.btc_dominance,
                    btc_trend=self.btc_trend,
                )

                signal = result["signal"]
                price = float(closes.iloc[-1])

                # Logging de diagnóstico
                if signal != Signal.NEUTRAL:
                    logger.info(
                        "📊 %s | Señal: %s | RSI: %.1f | VWAP trend: %s | Funding: %s | BTC.D: %s",
                        symbol, signal.value, result.get("rsi", 0),
                        result.get("trend", {}).get("trend", "?"),
                        result.get("funding_risk", "?"),
                        result.get("btc_advice", "?")[:20],
                    )

                # Abrir trade si hay señal y no tenemos posición en este símbolo
                if signal in (Signal.BUY, Signal.SELL) and symbol not in self.trader.positions:
                    direction = "BUY" if signal == Signal.BUY else "SELL"

                    # Verificar límite diario antes de abrir
                    # risk_amount = $ en riesgo de este trade (10% del capital actual)
                    risk_amount = self.trader.risk.current_capital * (self.trader.risk.risk_per_trade_pct / 100)
                    if not self.trader.risk.can_trade(risk_amount):
                        logger.warning("⛔ %s | Límite diario de riesgo alcanzado", symbol)
                        continue

                    trade = self.trader.open_trade(
                        symbol=symbol,
                        price=price,
                        direction=direction,
                        atr=result.get("atr", 0),
                        vwap=result.get("vwap", 0),
                        funding_rate=self.funding_rate,
                        btc_dominance=self.btc_dominance,
                    )
                    logger.info("✅ %s %s @ %.2f | Stop: %.2f | Size: $%.0f",
                                symbol, direction, price, trade.stop_loss, trade.size)

                    if self.database:
                        self.database.save_trade(trade)

                    asyncio.ensure_future(
                        self.notifier.send_trade_open(
                            symbol, direction, price, trade.size,
                            self.trader.risk.risk_per_trade_pct,
                        )
                    )

            except Exception as e:
                logger.warning("⚠️ Error escaneando %s: %s", symbol, e)

    async def manage_positions(self):
        """Gestiona posiciones abiertas: SL/TP/MAX_DURATION."""
        for symbol in list(self.trader.positions.keys()):
            try:
                ticker = self.exchange.get_ticker(symbol)
                current_price = ticker["last"]
                result = self.trader.tick(symbol, current_price)

                if result:
                    logger.info("🔔 %s cerrado: %s (PnL: %.2f$ | Capital: %.2f$)",
                                symbol, result.close_reason, result.pnl_usd,
                                self.trader.risk.current_capital)

                    if self.database:
                        self.database.close_trade(symbol, result.pnl_usd, result.pnl_pct, result.close_reason)

                    await self.notifier.send_trade_close(
                        symbol, current_price, result.pnl_usd, result.pnl_pct, result.close_reason,
                    )

                    if self.sheets_url:
                        await Exporter.to_google_sheets(
                            [result],
                            self.sheets_url,
                            sheet="REAL",
                            leverage=self.trader.leverage,
                            capital=self.trader.risk.current_capital,
                            initial_capital=self.trader.initial_capital,
                        )
            except Exception as e:
                logger.warning("⚠️ Error gestionando %s: %s", symbol, e)

    async def _export_dashboard(self):
        try:
            all_trades = list(self.trader.positions.values()) + self.trader.history
            perf = self.trader.get_performance()
            out = Path(__file__).resolve().parent.parent / "data" / "dashboard.html"
            Dashboard.html_to_file(all_trades, perf, out)
        except Exception as e:
            logger.warning("⚠️ Error generando dashboard: %s", e)

    def _load_state(self):
        if not self.database:
            return
        for trade in self.database.load_all_open_trades():
            # Reset de opened_at al reinicio (la ventana de MAX_DURATION empieza ahora,
            # no desde la apertura original en una sesion previa).
            trade.opened_at = datetime.now(timezone.utc)
            # Recalcular stop/TP al modelo KAVANA (10% fijo) usando el precio actual,
            # por si la posicion se guardo con parametros viejos (ej. apalancamiento 10x).
            try:
                ticker = self.exchange.get_ticker(trade.symbol)
                price = ticker["last"]
            except Exception:
                price = trade.entry_price
            stop_pct = 0.10
            if trade.direction == "BUY":
                trade.stop_loss = round(price * (1 - stop_pct), 6)
                trade.take_profit = round(price * (1 + stop_pct), 6)
            else:
                trade.stop_loss = round(price * (1 + stop_pct), 6)
                trade.take_profit = round(price * (1 - stop_pct), 6)
            self.trader.positions[trade.symbol] = trade
            logger.info("📂 Recuperada posición abierta: %s (stop recalculado 10%%)", trade.symbol)


async def run_bot():
    """Punto de entrada principal — componentes con Risk Manager y Analyzer v2."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    db_path = Config.DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    database = Database(db_path)
    database.initialize()

    exchange = Exchange()
    analyzer = Analyzer()

    # Trader con Risk Manager profesional
    trader = Trader(
        initial_capital=Config.INITIAL_CAPITAL,
        leverage=Config.LEVERAGE,
        risk_per_trade_pct=Config.RISK_PER_TRADE_PCT,
        atr_multiplier=Config.ATR_MULTIPLIER,
        max_duration_min=Config.MAX_DURATION_MIN,
    )

    notifier = Notifier(
        token=Config.TELEGRAM_TOKEN or "",
        chat_id=Config.TELEGRAM_CHAT_ID or "",
    )

    loop = TradingLoop(
        exchange=exchange,
        analyzer=analyzer,
        trader=trader,
        notifier=notifier,
        database=database,
    )

    await notifier.send_message(
        "🚀 <b>KAVANA Trading v2.1</b> iniciado\n"
        f"📊 Capital: ${Config.INITIAL_CAPITAL:,.0f}\n"
        f"🎯 Símbolos: {', '.join(Config.SYMBOLS)}\n"
        f"⚙️ Risk: {Config.RISK_PER_TRADE_PCT}%/trade | Trend: VWAP\n"
        f"📡 Webhook: activo"
    )

    await loop.start()


if __name__ == "__main__":
    asyncio.run(run_bot())
