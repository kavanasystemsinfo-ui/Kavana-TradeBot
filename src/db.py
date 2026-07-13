"""Persistencia SQLite — trades, configuración y métricas."""
import json
from pathlib import Path
from typing import Optional
import sqlite3

from src.trader import Trade, TradeStatus


class Database:
    """Base de datos SQLite para el bot de trading."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def initialize(self):
        """Crea las tablas si no existen."""
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    size REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    pnl_usd REAL DEFAULT 0,
                    pnl_pct REAL DEFAULT 0,
                    close_reason TEXT DEFAULT '',
                    opened_at TEXT NOT NULL,
                    closed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
            """)

    # --- Trades ---

    def save_trade(self, trade: Trade):
        """Guarda un trade (abierto o cerrado)."""
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO trades
                   (id, symbol, direction, entry_price, size, stop_loss, take_profit,
                    status, pnl_usd, pnl_pct, close_reason, opened_at, closed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trade.id, trade.symbol, trade.direction, trade.entry_price,
                    trade.size, trade.stop_loss, trade.take_profit,
                    trade.status.value, trade.pnl_usd, trade.pnl_pct,
                    trade.close_reason, trade.opened_at.isoformat(),
                    trade.closed_at.isoformat() if trade.closed_at else None,
                ),
            )

    def load_open_trade(self, symbol: str) -> Optional[Trade]:
        """Carga un trade abierto por símbolo."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM trades WHERE symbol = ? AND status = 'OPEN'",
                (symbol,),
            ).fetchone()
        return self._row_to_trade(row) if row else None

    def load_all_open_trades(self) -> list[Trade]:
        """Carga todos los trades abiertos."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'OPEN'"
            ).fetchall()
        return [self._row_to_trade(r) for r in rows]

    def close_trade(self, symbol: str, pnl_usd: float, pnl_pct: float, reason: str):
        """Marca un trade como cerrado."""
        from datetime import datetime, timezone
        with self.connect() as conn:
            conn.execute(
                """UPDATE trades SET status='CLOSED', pnl_usd=?, pnl_pct=?,
                   close_reason=?, closed_at=?
                   WHERE symbol=? AND status='OPEN'""",
                (pnl_usd, pnl_pct, reason, datetime.now(timezone.utc).isoformat(), symbol),
            )

    def load_history(self, limit: int = 50) -> list[Trade]:
        """Carga trades cerrados."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status='CLOSED' ORDER BY closed_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_trade(r) for r in rows]

    # --- Config ---

    def save_config(self, config: dict):
        """Guarda configuración como JSON."""
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                ("trading_config", json.dumps(config)),
            )

    def load_config(self) -> dict:
        """Carga configuración desde BD."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM config WHERE key = 'trading_config'"
            ).fetchone()
        return json.loads(row["value"]) if row else {}

    # --- Helpers ---

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Ejecuta una consulta y devuelve la primera fila."""
        with self.connect() as conn:
            return conn.execute(sql, params).fetchone()

    @staticmethod
    def _row_to_trade(row) -> Trade:
        from datetime import datetime
        trade = Trade(
            id=row["id"],
            symbol=row["symbol"],
            direction=row["direction"],
            entry_price=row["entry_price"],
            size=row["size"],
            stop_loss=row["stop_loss"] or 0,
            take_profit=row["take_profit"] or 0,
            status=TradeStatus(row["status"]),
            pnl_usd=row["pnl_usd"] or 0,
            pnl_pct=row["pnl_pct"] or 0,
            close_reason=row["close_reason"] or "",
        )
        if row["opened_at"]:
            trade.opened_at = datetime.fromisoformat(row["opened_at"])
        if row["closed_at"]:
            trade.closed_at = datetime.fromisoformat(row["closed_at"])
        return trade
