"""Tests del módulo de notificaciones Telegram."""
import pytest
from unittest.mock import AsyncMock, patch
from src.notifier import Notifier


@pytest.fixture
def notifier():
    return Notifier(token="mock_token", chat_id="123")


class TestInit:
    """El notifier debe inicializarse correctamente."""

    def test_requires_token(self):
        with pytest.raises(ValueError, match="token"):
            Notifier(token="", chat_id="123")

    def test_requires_chat_id(self):
        with pytest.raises(ValueError, match="chat_id"):
            Notifier(token="abc", chat_id="")


class TestFormatting:
    """Los mensajes deben formatearse correctamente (métodos estáticos, sin init)."""

    def test_format_trade_open(self):
        msg = Notifier.format_trade_open("BTC/USDT", "BUY", 50000, 100, 12.0)
        assert "BTC/USDT" in msg
        assert "BUY" in msg or "LONG" in msg
        assert "50,000" in msg or "50000" in msg

    def test_format_trade_close_win(self):
        msg = Notifier.format_trade_close("BTC/USDT", 55000, 500, 15.0, "TP_HIT")
        assert "BTC/USDT" in msg
        assert "+500" in msg or "500" in msg
        assert "TP_HIT" in msg or "tp" in msg.lower()

    def test_format_trade_close_loss(self):
        msg = Notifier.format_trade_close("BTC/USDT", 45000, -300, -12.0, "SL_HIT")
        assert "BTC/USDT" in msg

    def test_format_status(self):
        perf = {"capital": 1500, "total_trades": 10, "wins": 6, "losses": 4,
                "win_rate": 60.0, "roi_pct": 50.0, "cumulative_pnl_usd": 500}
        msg = Notifier.format_status(perf, [])
        assert "1,500" in msg or "1500" in msg
        assert "60" in msg

    def test_format_status_with_open_positions(self):
        perf = {"capital": 1500, "total_trades": 5, "wins": 3, "losses": 2,
                "win_rate": 60.0, "roi_pct": 50.0, "cumulative_pnl_usd": 500}
        positions = [{"symbol": "BTC/USDT", "entry": 50000, "pnl_pct": 5.0}]
        msg = Notifier.format_status(perf, positions)
        assert "BTC/USDT" in msg


class TestSending:
    """Los mensajes deben enviarse correctamente (mockeando Bot)."""

    @pytest.mark.asyncio
    async def test_send_message_returns_true_on_success(self):
        n = Notifier(token="mock_token", chat_id="123")
        with patch("telegram.Bot") as mock_bot_cls:
            mock_bot = AsyncMock()
            mock_bot_cls.return_value = mock_bot
            result = await n.send_message("test")
            assert result is True

    @pytest.mark.asyncio
    async def test_send_message_handles_error(self):
        n = Notifier(token="mock_token", chat_id="123")
        with patch("telegram.Bot") as mock_bot_cls:
            mock_bot = AsyncMock()
            mock_bot.send_message.side_effect = Exception("API Error")
            mock_bot_cls.return_value = mock_bot
            result = await n.send_message("test")
            assert result is False
