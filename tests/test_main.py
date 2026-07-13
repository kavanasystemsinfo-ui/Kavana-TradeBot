"""Tests del bucle principal de trading v2.1."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.main import TradingLoop
from src.analyzer import Signal


@pytest.fixture
def loop():
    """Bucle con todos los componentes mockeados."""
    return TradingLoop(
        exchange=MagicMock(),
        analyzer=MagicMock(),
        trader=MagicMock(),
        notifier=MagicMock(),
    )


class TestLoopInit:
    def test_requires_all_components(self):
        with pytest.raises(ValueError):
            TradingLoop(exchange=None, analyzer=None, trader=None, notifier=None)


class TestScanCycle:
    """Ciclo de escaneo con analyzer v2."""

    def test_analyzes_each_symbol(self, loop):
        loop.symbols = ["BTC/USDT", "ETH/USDT"]
        loop.exchange.fetch_ohlcv.return_value = MagicMock()
        loop.exchange.fetch_ohlcv.return_value.empty = False
        # Mock del DataFrame con iterrows
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.__iter__.return_value = iter([])
        mock_df.iterrows.return_value = iter([])
        loop.exchange.fetch_ohlcv.return_value = mock_df

        loop.analyzer.analyze.return_value = {"signal": Signal.NEUTRAL, "reasons": []}

        loop.scan_cycle()

        assert loop.exchange.fetch_ohlcv.call_count == 2
        assert loop.analyzer.analyze.call_count == 2

    def test_opens_trade_on_buy_signal(self, loop):
        loop.symbols = ["BTC/USDT"]
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.iterrows.return_value = iter([
            (0, {"high": 101, "low": 99, "close": 100, "volume": 1000}),
        ])
        loop.exchange.fetch_ohlcv.return_value = mock_df
        loop.analyzer.analyze.return_value = {
            "signal": Signal.BUY, "reasons": ["bullish_trend"],
            "rsi": 28, "atr": 500, "vwap": 99000,
            "trend": {"trend": "bullish"},
            "funding_risk": "normal",
            "btc_advice": "neutral_market",
        }
        loop.trader.positions = {}
        loop.trader.risk = MagicMock()
        loop.trader.risk.can_trade.return_value = True
        loop.trader.risk.risk_per_trade_pct = 1.0
        loop.trader.risk.current_capital = 10000
        loop.trader.open_trade.return_value = MagicMock()
        loop.notifier.send_trade_open = AsyncMock()

        loop.scan_cycle()
        loop.trader.open_trade.assert_called_once()

    def test_does_not_open_trade_on_neutral(self, loop):
        loop.symbols = ["BTC/USDT"]
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.iterrows.return_value = iter([])
        loop.exchange.fetch_ohlcv.return_value = mock_df
        loop.analyzer.analyze.return_value = {
            "signal": Signal.NEUTRAL, "reasons": ["waiting"],
        }
        loop.trader.positions = {}

        loop.scan_cycle()
        loop.trader.open_trade.assert_not_called()


class TestPositionManagement:
    def test_ticks_open_positions(self):
        loop = TradingLoop(
            exchange=MagicMock(),
            analyzer=MagicMock(),
            trader=MagicMock(),
            notifier=MagicMock(),
        )
        loop.trader.positions = {"BTC/USDT": MagicMock()}
        loop.exchange.get_ticker.return_value = {"last": 51000}

        import asyncio
        asyncio.run(loop.manage_positions())

        loop.trader.tick.assert_called_once_with("BTC/USDT", 51000)

    def test_sends_notification_on_trade_close(self):
        loop = TradingLoop(
            exchange=MagicMock(),
            analyzer=MagicMock(),
            trader=MagicMock(),
            notifier=MagicMock(),
        )
        loop.trader.positions = {"BTC/USDT": MagicMock()}
        loop.exchange.get_ticker.return_value = {"last": 51000}
        closed_trade = MagicMock()
        closed_trade.symbol = "BTC/USDT"
        loop.trader.tick.return_value = closed_trade

        import asyncio
        asyncio.run(loop.manage_positions())

        loop.notifier.send_trade_close.assert_called_once()
