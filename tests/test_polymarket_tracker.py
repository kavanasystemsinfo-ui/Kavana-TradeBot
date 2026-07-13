"""Tests del rastreador de wallets de Polymarket."""
import pytest
from unittest.mock import patch, MagicMock
from src.polymarket_tracker import WalletTracker, TRADERS, is_crypto_market


@pytest.fixture
def tracker():
    return WalletTracker(webhook_url="http://localhost:8081/webhook")


class TestWalletsConfig:
    """Las wallets deben cargarse correctamente."""

    def test_has_known_traders(self):
        assert len(TRADERS) >= 5
        assert any("Seriously" in t["alias"] for t in TRADERS)

    def test_each_trader_has_address(self):
        for t in TRADERS:
            assert len(t["proxy_address"]) >= 38  # 0x + 36+ hex chars
            assert t["alias"]


class TestFetchTrades:
    """Obtener trades de una wallet debe funcionar."""

    def test_fetches_trades_for_address(self, tracker):
        with patch("urllib.request.urlopen") as mock_fetch:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'[{"side":"BUY","price":"0.99","size":"52.87","conditionId":"0x1","timestamp":"2026-07-01T00:00:00Z","market":"Will BTC hit 200k?"}]'
            mock_fetch.return_value.__enter__.return_value = mock_resp

            trades = tracker.fetch_user_trades("0xabc")
            assert len(trades) > 0
            assert trades[0]["side"] == "BUY"

    def test_handles_empty_response(self, tracker):
        with patch("urllib.request.urlopen") as mock_fetch:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'[]'
            mock_fetch.return_value.__enter__.return_value = mock_resp

            trades = tracker.fetch_user_trades("0xabc")
            assert len(trades) == 0

    def test_handles_api_error(self, tracker):
        with patch("urllib.request.urlopen") as mock_fetch:
            mock_fetch.side_effect = Exception("Connection error")

            trades = tracker.fetch_user_trades("0xabc")
            assert len(trades) == 0


class TestDetectNewTrades:
    """Detectar trades nuevos debe evitar duplicados."""

    def test_identifies_new_trades(self, tracker):
        tracker.last_seen = {"0xabc": "tx_old"}
        trades = [
            {"txHash": "tx_new", "side": "BUY", "price": "0.99"},
        ]
        nuevos = tracker.get_new_trades("0xabc", trades)
        assert len(nuevos) == 1
        assert nuevos[0]["txHash"] == "tx_new"

    def test_skips_old_trades(self, tracker):
        tracker.last_seen = {"0xabc": "tx_old"}
        trades = [
            {"txHash": "tx_old", "side": "BUY"},
        ]
        nuevos = tracker.get_new_trades("0xabc", trades)
        assert len(nuevos) == 0

    def test_updates_last_seen(self, tracker):
        tracker.last_seen = {}
        trades = [
            {"txHash": "tx_newest"},
            {"txHash": "tx_older"},
        ]
        tracker.get_new_trades("0xabc", trades)
        assert tracker.last_seen.get("0xabc") == "tx_newest"


class TestCryptoFilter:
    """El filtro de mercados crypto debe funcionar correctamente."""

    def test_detects_crypto_market(self):
        assert is_crypto_market("Will Bitcoin reach $100k?") is True

    def test_rejects_non_crypto_market(self):
        assert is_crypto_market("New Rihanna Album before GTA VI?") is False

    def test_rejects_sports(self):
        assert is_crypto_market("Who wins the Super Bowl?") is False

    def test_detects_ethereum(self):
        assert is_crypto_market("Ethereum price above $5000?") is True

    def test_empty_string(self):
        assert is_crypto_market("") is False


class TestIntegration:

    @pytest.mark.asyncio
    async def test_sends_to_webhook(self, tracker):
        result = await tracker.send_trade_to_webhook(
            {"side": "BUY", "market": "Will BTC hit 200k?", "price": "0.99", "size": "50"},
            alias="SeriouslySirius",
            capital=1000,
        )
        assert result is True
