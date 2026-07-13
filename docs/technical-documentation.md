# KAVANA Trading — Documentación Técnica

> **Proyecto:** KAVANA Trading Bot
> **Versión:** 2.1.0 — Motor de señales corregido + limpieza YAGNI
> **Fecha:** 12/07/2026
> **Clasificación:** IT Consulting — Documentation Standard

## Historial de versiones

| Versión | Fecha | Estado | Descripción |
|---------|-------|--------|-------------|
| Alpha | 07-08/07/2026 | ❌ Pruebas | 14 trades de prueba (-303.67$ PnL), stops fijos 12/15% |
| v1.0 | 09/07/2026 | ✅ Estable | Risk Manager + Analyzer V2 + 105 tests. Reseteo a 1.000$ |
| **v2.1** | **12/07/2026** | ✅ **Estable** | **Fix motor de señales (ADR-010) + limpieza YAGNI (ADR-011) + 112 tests** |

### Estado actual del bot

| Métrica | Valor |
|---------|-------|
| Versión | **v2.1** |
| Tests | **112 passed, 0 fallos** |
| Risk per trade | 1,0% |
| Trend filter | VWAP (umbral **0.15%**, configurable vía `TREND_STRENGTH`) |
| Símbolos | BTC, ETH, SOL, ADA, XRP |
| Dashboard | http://167.233.97.71:8081/dashboard |
| CSV | http://167.233.97.71:8081/trades/real.csv |

### Lo que incluye v2.1

| Módulo | Archivo | Tests | Estado |
|--------|---------|-------|--------|
| Exchange | `src/exchange.py` | 7 | ✅ ccxt wrapper (OHLCV, read-only) |
| Analyzer | `src/analyzer.py` | 11+4 | ✅ VWAP, RSI, MACD — lógica corregida (ADR-010) |
| Risk Manager | `src/risk.py` | 9 | ✅ ATR stops, Kelly, límite diario |
| Trader | `src/trader.py` | 13 | ✅ Risk Manager integrado |
| Notifier | `src/notifier.py` | 9 | ✅ Telegram |
| DB | `src/db.py` | 10 | ✅ SQLite WAL |
| Exporter | `src/exporter.py` | 7 | ✅ CSV + webhook |
| Dashboard | `src/dashboard.py` | 6 | ✅ Chart.js |
| Main | `src/main.py` | 6 | ✅ Bucle de escaneo + sleep anti-429 |
| Wallet Tracker | `src/polymarket_tracker.py` | 14 | ✅ Wallets smart money (sustituye al tracker de mercados eliminado) |

> **Nota YAGNI (ADR-011):** el antiguo `src/polymarket.py` (tracker de mercados por keywords) fue eliminado: se instanciaba pero nunca se invocaba. El rastreo real usa `WalletTracker`.

### ADR-009: Renombrado v2.1 → v1.0

**Contexto:** El proyecto pasó por una fase Alpha con 14 trades de prueba que arrojaron un PnL de -303.67$. Esos datos corresponden a prototipado y no representan el rendimiento del producto estable.
**Decisión:** La versión 2.1 (que incluía las mejoras de Risk Manager, Analyzer V2, y 105 tests) pasa a denominarse **v1.0** como primera release estable. Los datos de la fase Alpha se descartan del histórico oficial.
**Consecuencia:** El bot arranca desde cero con 1.000$ de capital y un win rate esperado de 55-65% con la nueva configuración.
**Fecha:** 09/07/2026

### ADR-010: Corrección del motor de señales (12/07/2026)

**Contexto:** El bot llevaba 24 h+ sin emitir señales. Dos defectos: (1) lógica de señal con condiciones mutuamente excluyentes (tendencia alcista + RSI sobrevendido); (2) umbral de tendencia VWAP del 2% — 10× superior al desvío real de mercado (0.07-0.25% medido en KuCoin).
**Decisión:** Tendencia = dirección, RSI/MACD = timing en la misma dirección. Umbral recalibrado a **0.15%** con datos reales y expuesto como `TREND_STRENGTH`.
**Resultado:** 4 tests de regresión nuevos; backtest 5-32 señales/símbolo. Detalle en `docs/ADR-010-motor-de-senales.md`.

### ADR-011: Limpieza YAGNI del tracker Polymarket (12/07/2026)

**Contexto:** `src/polymarket.py` se instanciaba pero nunca se usaba (el rastreo real usa `polymarket_tracker.py`/`WalletTracker`).
**Decisión:** Eliminar módulo + instanciación + test (YAGNI).
**Resultado:** −177 líneas, suite limpia (112 tests, 0 fallos). Detalle en `docs/ADR-011-yagni-polymarket-cleanup.md`.

### Lecciones aprendidas (resumen)

1. **Mide antes de fijar parámetros de mercado.** Un umbral del 2% suena razonable en papel pero es 10× el desvío real del VWAP en velas 5-15 min.
2. **Datos de prueba realistas.** Líneas rectas enmascaran el comportamiento (VWAP persigue al precio → tendencia neutra). Usar patrones zigzag.
3. **Elimina el código muerto al reemplazar componentes**, no en un cambio aparte.
4. **Rate-limit de exchange.** `enableRateLimit` de ccxt no basta con KuCoin; añadir colchón propio (1 s entre símbolos).
