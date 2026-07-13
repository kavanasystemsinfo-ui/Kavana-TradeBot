"""Dashboard HTML + servidor web + PWA para acceso móvil."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.trader import Trade, TradeStatus

logger = logging.getLogger("kavana.dashboard")


class Dashboard:
    """Genera dashboard HTML con métricas, equity curve y soporte PWA."""

    HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="theme-color" content="#0f172a">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
{PWA_LINKS}
<title>KAVANA Trading</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f172a;color:#e2e8f0;padding:16px;}}
  h1{{font-size:1.5rem;color:#f59e0b;margin-bottom:4px;}}
  .subtitle{{color:#64748b;font-size:0.85rem;margin-bottom:20px;}}
  .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:16px;}}
  .card{{background:#1e293b;border-radius:10px;padding:14px;border:1px solid #334155;}}
  .label{{font-size:0.65rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;}}
  .value{{font-size:1.2rem;font-weight:700;margin-top:2px;}}
  .positive{{color:#22c55e;}}.negative{{color:#ef4444;}}
  table{{width:100%;border-collapse:collapse;font-size:0.8rem;}}
  th{{text-align:left;padding:8px 6px;background:#1e293b;color:#94a3b8;font-size:0.7rem;text-transform:uppercase;}}
  td{{padding:8px 6px;border-bottom:1px solid #1e293b;}}
  .badge{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:0.65rem;font-weight:600;}}
  .badge-win{{background:#166534;color:#86efac;}}
  .badge-loss{{background:#991b1b;color:#fca5a5;}}
  .badge-open{{background:#92400e;color:#fcd34d;}}
  .chart-card{{background:#1e293b;border-radius:10px;padding:14px;border:1px solid #334155;margin-bottom:16px;}}
  #updated{{text-align:right;color:#64748b;font-size:0.7rem;margin-top:12px;}}
</style>
</head>
<body>
<h1>🏭 KAVANA</h1>
<p class="subtitle">Paper Trading · {TIMESTAMP_SHORT}</p>
<div class="grid">
  <div class="card"><div class="label">Capital</div><div class="value">${CAPITAL}</div></div>
  <div class="card"><div class="label">ROI</div><div class="value {ROI_CLASS}">{ROI}</div></div>
  <div class="card"><div class="label">Win Rate</div><div class="value">{WIN_RATE}%</div></div>
  <div class="card"><div class="label">Ganadas</div><div class="value positive">{WINS}</div></div>
  <div class="card"><div class="label">Perdidas</div><div class="value negative">{LOSSES}</div></div>
  <div class="card"><div class="label">Trades</div><div class="value">{TRADES}</div></div>
</div>
<div class="chart-card"><canvas id="chart"></canvas></div>
<table><thead><tr><th>Activo</th><th>Dir</th><th>Entrada</th><th>PnL</th><th>Estado</th></tr></thead>
<tbody>{ROWS}</tbody></table>
<div id="updated">{TIMESTAMP}</div>
<script>
const eq={EQUITY};
new Chart(document.getElementById('chart'),{{
  type:'line',
  data:{{labels:eq.map(d=>d.l),datasets:[{{label:'Capital',data:eq.map(d=>d.v),
    borderColor:'#f59e0b',backgroundColor:'rgba(245,158,11,0.1)',
    fill:true,tension:0.3,pointRadius:0}}]}},
  options:{{responsive:true,plugins:{{legend:{{display:false}}}},
    scales:{{x:{{ticks:{{color:'#64748b',maxTicksLimit:8}},grid:{{color:'#1e293b'}}}},
             y:{{ticks:{{color:'#64748b'}},grid:{{color:'#1e293b'}}}}}}}}
}});
</script>
</body></html>"""

    @staticmethod
    def generate_html(
        trades: list[Trade],
        perf: dict,
        pwa: bool = False,
    ) -> str:
        """Genera el HTML del dashboard."""
        pwa_links = ""
        if pwa:
            pwa_links = (
                '<link rel="manifest" href="/manifest.json">\n'
                '<link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏭</text></svg>">'
            )

        fechar = datetime.now()
        capital_fmt = f"{perf['capital']:,.2f}"
        roi_fmt = f"{perf['roi_pct']:+.2f}%"
        roi_class = "positive" if perf['roi_pct'] >= 0 else "negative"

        closed = sorted(
            [t for t in trades if t.status == TradeStatus.CLOSED],
            key=lambda t: t.closed_at or t.opened_at, reverse=True,
        )
        opens = [t for t in trades if t.status == TradeStatus.OPEN]
        all_trades = closed + opens

        rows = []
        equity = []
        cap = perf.get("initial_capital", 1000.0)
        trade_n = 0

        for t in all_trades:
            direction = "🟢" if t.direction == "BUY" else "🔴"

            if t.status == TradeStatus.CLOSED:
                badge_cls = "badge-win" if t.pnl_usd > 0 else "badge-loss"
                badge = f'<span class="badge {badge_cls}">{t.pnl_usd:+.0f}$</span>'
                pnl = f"{t.pnl_usd:+.2f}$"
                trade_n += 1
                cap += t.pnl_usd
                equity.append({"l": f"#{trade_n}", "v": round(cap, 2)})
            else:
                badge = '<span class="badge badge-open">Abierta</span>'
                pnl = "—"

            rows.append(
                f"<tr><td>{t.symbol}</td><td>{direction}</td>"
                f"<td>${t.entry_price:,.0f}</td>"
                f"<td class=\"{'positive' if t.pnl_usd > 0 else 'negative'}\">{pnl}</td>"
                f"<td>{badge}</td></tr>"
            )

        if not equity:
            equity = [{"l": "Inicio", "v": perf.get("initial_capital", 1000)},
                      {"l": "Ahora", "v": perf['capital']}]

        return Dashboard.HTML_TEMPLATE.format(
            PWA_LINKS=pwa_links,
            CAPITAL=capital_fmt,
            ROI=roi_fmt,
            ROI_CLASS=roi_class,
            WIN_RATE=perf['win_rate'],
            TRADES=perf['total_trades'],
            WINS=perf['wins'],
            LOSSES=perf['losses'],
            ROWS="\n".join(rows),
            EQUITY=json.dumps(equity),
            TIMESTAMP=fechar.strftime("%Y-%m-%d %H:%M:%S"),
            TIMESTAMP_SHORT=fechar.strftime("%d/%m %H:%M"),
        )

    @staticmethod
    def html_to_file(trades: list[Trade], perf: dict, output: Path) -> str:
        """Genera y guarda el dashboard HTML en un archivo."""
        html = Dashboard.generate_html(trades, perf, pwa=True)
        output.write_text(html, encoding="utf-8")
        logger.info("📊 Dashboard guardado en %s", output)
        return html

    @staticmethod
    async def serve(trades: list[Trade], perf: dict, host: str = "0.0.0.0", port: int = 8080):
        """Sirve el dashboard como servidor web (para PWA móvil)."""
        from aiohttp import web

        async def handler(request: web.Request) -> web.Response:
            html = Dashboard.generate_html(trades, perf, pwa=True)
            if request.path == "/manifest.json":
                manifest = {
                    "name": "KAVANA Trading",
                    "short_name": "KAVANA",
                    "start_url": "/",
                    "display": "standalone",
                    "background_color": "#0f172a",
                    "theme_color": "#0f172a",
                    "icons": [{"src": "data:image/svg+xml,...", "sizes": "192x192", "type": "image/svg+xml"}],
                }
                return web.json_response(manifest)
            return web.Response(text=html, content_type="text/html")

        app = web.Application()
        app.router.add_get("/", handler)
        app.router.add_get("/manifest.json", handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        logger.info("📊 Dashboard en http://%s:%s", host, port)
