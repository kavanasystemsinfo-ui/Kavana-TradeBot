"""Configuración central — una sola fuente de verdad. v2.1"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def getenv_or_raise(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Falta variable de entorno: {key}")
    return value


class Config:
    """Configuración única del bot. Carga perezosa (lazy)."""

    # --- Exchange ---
    EXCHANGE_ID: str = os.getenv("EXCHANGE_ID", "kucoin")
    EXCHANGE_API_KEY: str | None = os.getenv("EXCHANGE_API_KEY")
    EXCHANGE_SECRET: str | None = os.getenv("EXCHANGE_SECRET")
    EXCHANGE_PASSPHRASE: str | None = os.getenv("EXCHANGE_PASSPHRASE")

    # --- Trading ---
    SYMBOLS: list[str] = os.getenv("SYMBOLS", "BTC/USDT,ETH/USDT,SOL/USDT,ADA/USDT,XRP/USDT").split(",")
    TIMEFRAME: str = os.getenv("TIMEFRAME", "15m")  # Cambiado a 15m (menos ruido)
    LEVERAGE: int = int(os.getenv("LEVERAGE", "10"))
    INITIAL_CAPITAL: float = float(os.getenv("INITIAL_CAPITAL", "10000"))

    # --- Risk Management (nuevo) ---
    RISK_PER_TRADE_PCT: float = float(os.getenv("RISK_PER_TRADE_PCT", "1.0"))  # 1% por trade
    MAX_RISK_PCT: float = float(os.getenv("MAX_RISK_PCT", "2.0"))  # 2% máximo
    ATR_MULTIPLIER: float = float(os.getenv("ATR_MULTIPLIER", "2.0"))  # 2 ATR para stop
    KELLY_FRACTION: float = float(os.getenv("KELLY_FRACTION", "0.25"))  # 25% de Kelly
    DAILY_LOSS_LIMIT: float = float(os.getenv("DAILY_LOSS_LIMIT", "5.0"))  # 5% pérdida diaria
    MAX_OPEN_TRADES: int = int(os.getenv("MAX_OPEN_TRADES", "3"))

    # --- VWAP / Trend Filter (nuevo) ---
    VWAP_PERIOD: int = int(os.getenv("VWAP_PERIOD", "20"))
    TREND_STRENGTH: float = float(os.getenv("TREND_STRENGTH", "0.02"))  # 2% sobre VWAP

    # --- Funding Rate (nuevo) ---
    FUNDING_EXTREME: float = float(os.getenv("FUNDING_EXTREME", "0.05"))  # >0.05% evitar
    FUNDING_HIGH: float = float(os.getenv("FUNDING_HIGH", "0.025"))

    # --- BTC Dominance (nuevo) ---
    BTC_D_HIGH: float = float(os.getenv("BTC_D_HIGH", "55.0"))

    # --- Legacy (compatibilidad) ---
    STOP_LOSS_PCT: float = float(os.getenv("STOP_LOSS_PCT", "12"))  # Ya no se usa directamente
    TAKE_PROFIT_PCT: float = float(os.getenv("TAKE_PROFIT_PCT", "15"))
    MAX_DURATION_MIN: int = int(os.getenv("MAX_DURATION_MIN", "120"))

    # --- Telegram ---
    TELEGRAM_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")

    APPS_SCRIPT_URL: str | None = os.getenv("APPS_SCRIPT_URL")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "http://localhost:8081/webhook")

    # --- Database ---
    DB_PATH: Path = BASE_DIR / "data" / "trading.db"

    # --- AIsa (opcional) ---
    AISA_API_KEY: str | None = os.getenv("AISA_API_KEY")
