"""Tests del dashboard — generación HTML y servidor web."""
import pytest
from src.dashboard import Dashboard
from src.trader import Trade, TradeStatus


@pytest.fixture
def trades():
    return [
        Trade(id="t1", symbol="BTC/USDT", direction="BUY", entry_price=50000,
              size=100, stop_loss=44000, take_profit=57500,
              status=TradeStatus.CLOSED, pnl_usd=500, pnl_pct=15.0,
              close_reason="TP_HIT"),
        Trade(id="t2", symbol="SOL/USDT", direction="BUY", entry_price=150,
              size=50, status=TradeStatus.OPEN, stop_loss=130, take_profit=172),
    ]


class TestHtmlGeneration:
    def test_generates_html_string(self, trades):
        perf = {"capital": 1500, "total_trades": 1, "wins": 1, "losses": 0,
                "win_rate": 100.0, "roi_pct": 50.0, "cumulative_pnl_usd": 500}
        html = Dashboard.generate_html(trades, perf)
        assert isinstance(html, str)
        assert html.strip().startswith("<!DOCTYPE html>")
        assert len(html) > 500

    def test_includes_trade_list(self, trades):
        perf = {"capital": 1500, "total_trades": 1, "wins": 1, "losses": 0,
                "win_rate": 100.0, "roi_pct": 50.0, "cumulative_pnl_usd": 500}
        html = Dashboard.generate_html(trades, perf)
        assert "BTC/USDT" in html
        assert "500" in html  # PnL del trade cerrado

    def test_marks_open_trades(self, trades):
        perf = {"capital": 1000, "total_trades": 0, "wins": 0, "losses": 0,
                "win_rate": 0, "roi_pct": 0, "cumulative_pnl_usd": 0}
        html = Dashboard.generate_html(trades, perf)
        assert "Abierta" in html or "OPEN" in html.upper()

    def test_empty_state(self):
        perf = {"capital": 1000, "total_trades": 0, "wins": 0, "losses": 0,
                "win_rate": 0, "roi_pct": 0, "cumulative_pnl_usd": 0}
        html = Dashboard.generate_html([], perf)
        assert "1000" in html or "1,000" in html


class TestPwaManifest:
    """El dashboard debe incluir meta para PWA (accesible desde móvil)."""

    def test_includes_viewport_meta(self):
        perf = {"capital": 1000, "total_trades": 0, "wins": 0, "losses": 0,
                "win_rate": 0, "roi_pct": 0, "cumulative_pnl_usd": 0}
        html = Dashboard.generate_html([], perf)
        assert 'name="viewport"' in html or "viewport" in html

    def test_includes_pwa_icons(self):
        perf = {"capital": 1000, "total_trades": 0, "wins": 0, "losses": 0,
                "win_rate": 0, "roi_pct": 0, "cumulative_pnl_usd": 0}
        html = Dashboard.generate_html([], perf, pwa=True)
        assert "apple-touch-icon" in html
        assert "manifest" in html
        assert "theme-color" in html
