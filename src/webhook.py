""""Mini servidor webhook — recibe trades, los guarda en SQLite y los sirve como CSV."""
from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import aiohttp
from aiohttp import web

logger = logging.getLogger("kavana.webhook")

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "webhook.db"


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            sheet TEXT,
            activo TEXT,
            direccion TEXT,
            precio_entrada REAL,
            precio_salida REAL,
            inversion REAL,
            apalancamiento INTEGER,
            resultado TEXT,
            pnl_neto REAL,
            capital_actual REAL,
            capital_inicial REAL
        )
    """)
    conn.commit()
    conn.close()


async def handle_post(request: web.Request) -> web.Response:
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid json"}, status=400)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """INSERT INTO trades (timestamp, sheet, activo, direccion, precio_entrada,
           precio_salida, inversion, apalancamiento, resultado, pnl_neto,
           capital_actual, capital_inicial)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.utcnow().isoformat(),
            data.get("sheet", "REAL"),
            data.get("activo", ""),
            data.get("direccion", ""),
            data.get("precio_entrada", 0),
            data.get("precio_salida", 0),
            data.get("inversion", 0),
            data.get("apalancamiento", 10),
            data.get("resultado", ""),
            data.get("pnl_neto", 0),
            data.get("capital_actual", 1000),
            data.get("capital_inicial", 1000),
        ),
    )
    conn.commit()
    conn.close()

    logger.info("📥 Trade registrado: %s %s", data.get("activo"), data.get("resultado"))
    return web.json_response({"ok": True, "message": "Trade registrado"})


async def handle_csv_real(request: web.Request) -> web.Response:
    return await _csv_for_sheet(request, "REAL")

async def handle_csv_labs(request: web.Request) -> web.Response:
    return await _csv_for_sheet(request, "LABS")

async def handle_csv_polymarket(request: web.Request) -> web.Response:
    return await _csv_for_sheet(request, "POLYMARKET")


async def _csv_for_sheet(request: web.Request, sheet_name: str) -> web.Response:
    """Sirve CSV filtrado por pestaña."""
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT * FROM trades WHERE sheet = ? ORDER BY id DESC LIMIT 200",
        (sheet_name,),
    ).fetchall()
    conn.close()

    csv_lines = ["Timestamp,Activo,Direccion,Entrada,Salida,Resultado,PnL,Capital"]
    for r in rows:
        csv_lines.append(
            f"{r[1]},{r[3]},{r[4]},{r[5]},{r[6]},{r[9]},{r[10]},{r[11]}"
        )
    return web.Response(
        text="\n".join(csv_lines),
        content_type="text/csv",
        headers={"Access-Control-Allow-Origin": "*"},
    )


async def handle_html(request: web.Request) -> web.Response:
    """Mini dashboard web."""
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT * FROM trades ORDER BY id DESC LIMIT 50"
    ).fetchall()
    stats = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(pnl_neto),0) FROM trades WHERE resultado LIKE 'WIN%'"
    ).fetchone()
    stats2 = conn.execute(
        "SELECT COUNT(*) FROM trades WHERE resultado LIKE 'LOSE%'"
    ).fetchone()
    conn.close()

    wins = stats[0] or 0
    losses = stats2[0] or 0
    total = wins + losses
    win_rate = round(wins / total * 100, 1) if total else 0
    pnl = stats[1] or 0

    html = f"""<!DOCTYPE html><html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KAVANA Webhook</title>
<style>body{{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;padding:20px}}
h1{{color:#f59e0b}}.stats{{display:flex;gap:16px;margin:16px 0}}
.card{{background:#1e293b;padding:14px 20px;border-radius:10px}}
table{{width:100%;border-collapse:collapse;font-size:0.85rem}}
th{{text-align:left;padding:8px;background:#1e293b;color:#94a3b8;border-bottom:2px solid #334155}}
td{{padding:8px;border-bottom:1px solid #1e293b}}
.win{{color:#22c55e}}.loss{{color:#ef4444}}
.url-box{{background:#1e293b;padding:10px;border-radius:6px;font-family:monospace;font-size:0.8rem;margin:12px 0}}
a{{color:#f59e0b}}</style></head>
<body>
<h1>🏭 KAVANA Trading — Webhook</h1>
<div class="url-box">📥 POST → http://{request.host}/webhook &nbsp;|&nbsp; 📊 CSV → http://{request.host}/trades.csv</div>
<div class="stats">
  <div class="card">🎯 Win Rate <b>{win_rate}%</b></div>
  <div class="card">✅ {wins}W | ❌ {losses}L</div>
  <div class="card">💰 PnL <b class="{'win' if pnl>=0 else 'loss'}">${pnl:+.2f}</b></div>
  <div class="card">📊 Total <b>{total}</b></div>
</div>
<p style="color:#94a3b8">📋 Últimos trades:</p>
<table><thead><tr><th>#</th><th>Activo</th><th>Direccion</th><th>Entrada</th><th>Salida</th><th>Resultado</th><th>PnL</th></tr></thead><tbody>
"""
    for r in rows[:20]:
        cls = "win" if "WIN" in str(r[9]) else "loss" if "LOSE" in str(r[9]) else ""
        html += f"<tr><td>{r[0]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td><td>{r[6]}</td><td class='{cls}'>{r[9]}</td><td>{r[10]}</td></tr>"

    html += "</tbody></table></body></html>"
    return web.Response(text=html, content_type="text/html",
                        headers={"Access-Control-Allow-Origin": "*"})


async def handle_pwa(request: web.Request) -> web.Response:
    """Sirve el dashboard PWA generado por el bot."""
    pwa_path = Path(__file__).resolve().parent.parent / "data" / "dashboard.html"
    if pwa_path.exists():
        return web.Response(text=pwa_path.read_text(encoding="utf-8"), content_type="text/html")
    return web.Response(text="Dashboard no generado aún", status=202)


async def start_webhook(host: str = "0.0.0.0", port: int = 8081):
    init_db()
    app = web.Application()
    app.router.add_post("/webhook", handle_post)
    app.router.add_get("/trades.csv", handle_csv_real)
    app.router.add_get("/trades/real.csv", handle_csv_real)
    app.router.add_get("/trades/labs.csv", handle_csv_labs)
    app.router.add_get("/trades/polymarket.csv", handle_csv_polymarket)
    app.router.add_get("/", handle_html)
    app.router.add_get("/dashboard", handle_pwa)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("📡 Webhook en http://%s:%s", host, port)
    logger.info("   POST → /webhook  (recibe trades)")
    logger.info("   CSV  → /trades.csv  (importable en Google Sheets)")
    return runner


async def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    await start_webhook()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
