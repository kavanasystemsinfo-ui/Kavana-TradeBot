"""Módulo de conexión con exchanges via ccxt."""
import ccxt
import pandas as pd
from src.config import Config


class ExchangeError(Exception):
    """Error controlado del exchange."""


class Exchange:
    """Wrapper alrededor de ccxt con manejo de errores."""

    def __init__(self, exchange_id: str | None = None):
        self.exchange_id = (exchange_id or Config.EXCHANGE_ID).lower()
        self._exchange = self._build()

    def _build(self) -> ccxt.Exchange:
        exchange_class = getattr(ccxt, self.exchange_id)
        return exchange_class({
            "enableRateLimit": True,
            "apiKey": Config.EXCHANGE_API_KEY or "",
            "secret": Config.EXCHANGE_SECRET or "",
            "password": Config.EXCHANGE_PASSPHRASE or "",
        })

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str | None = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """Obtiene velas OHLCV y las devuelve como DataFrame limpio."""
        try:
            raw = self._exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe or Config.TIMEFRAME,
                limit=limit,
            )
        except Exception as e:
            raise ExchangeError(f"Error de conexión: {e}") from e

        if not raw:
            raise ExchangeError(f"Sin datos para {symbol}")

        df = pd.DataFrame(
            raw,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    def get_ticker(self, symbol: str) -> dict:
        """Obtiene el ticker actual de un símbolo."""
        try:
            return self._exchange.fetch_ticker(symbol)
        except Exception as e:
            raise ExchangeError(f"Error obteniendo ticker: {e}") from e
