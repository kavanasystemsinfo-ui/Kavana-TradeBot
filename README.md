# KAVANA Trading v2.1 — Paper Trading Bot

> Bot de paper trading algorítmico que detecta tendencias de mercado y las ejecuta con gestión de riesgo institucional. **112 tests TDD | Python 3.12 | Docker | Telegram**

## El Problema

Un operador que vigila manualmente 5 pares cripto en velas de 5-15 min no puede reaccionar a las rupturas de tendencia de forma consistente ni llevar una gestión de riesgo disciplinada 24/7. Las decisiones intuitivas sufren de sesgo y fatiga.

## Nuestra Solución

KAVANA Trading automatiza el ciclo completo: **lee** datos de KuCoin, **detecta** tendencia con VWAP y momentum con RSI/MACD, **gestiona** el riesgo por trade (1% de la cuenta, stops ATR, criterio de Kelly) y **notifica** cada señal en Telegram con su dashboard de rendimiento.

Metodología **TDD + YAGNI** estricta: cada regla de mercado tiene pruebas que reproducen fallos reales, y se elimina todo código que no se ejecute.

## Probar en 60 Segundos

```bash
# Levantar el bot (producción en VPS)
docker compose up -d

# Verificar que la suite pasa (112 tests)
docker exec kavana-trading python -m pytest -q

# Ver señales en vivo
# → Telegram: 🚀 Bot v2.1 iniciado
# → Dashboard: http://167.233.97.71:8081/dashboard
```

**Backtest de validación (12/07/2026):** sobre las últimas ~70 velas de cada par, la lógica corregida genera **5-32 señales por símbolo** según tendencia. Antes del fix: 0 señales constantes.

## Arquitectura

```
                ┌─────────────┐
   KuCoin API → │  exchange   │ fetch OHLCV (ccxt, read-only)
                └──────┬──────┘
                       ▼
   ┌────────────────────────────────────┐
   │  analyzer  →  RSI + MACD + VWAP     │ tendencia = dirección, RSI = timing
   └────────────────┬───────────────────┘
                    ▼
   ┌────────────────────────────────────┐
   │  trader  →  Risk Manager (ATR/Kelly) │ decide tamaño y stop
   └────────┬───────────────┬─────────────┘
            ▼               ▼
      notifier         db + exporter
      (Telegram)       (SQLite + CSV + webhook)
            ▼
      dashboard (Chart.js)
```

| Componente | Tecnología |
|-----------|------------|
| Core | Python 3.12 |
| Exchange | ccxt (KuCoin) — solo lectura OHLCV |
| Análisis | RSI, MACD, VWAP (20 velas), EMAs, ATR |
| Risk | Stops ATR dinámicos, Kelly fraccional, límite de pérdida diaria |
| DB | SQLite con WAL |
| Notifier | Telegram bot |
| Dashboard | HTML + Chart.js |
| Webhook | aiohttp + endpoints CSV |

## Estado actual

| Métrica | Valor |
|---------|-------|
| Versión | **v2.1** |
| Tests | **112 passed, 0 fallos** |
| Risk per trade | 1,0% |
| Trend filter | VWAP (umbral **0.15%**, configurable) |
| Símbolos | BTC, ETH, SOL, ADA, XRP |
| Dashboard | http://167.233.97.71:8081/dashboard |

## Métricas de Resultado (realidad, no marketing)

- **Recuperación de señales:** el bot pasó de 0 señales (24 h+ en NEUTRAL) a 5-32 señales/símbolo en backtest tras corregir umbral y lógica (ADR-010).
- **Reducción de superficie:** −177 líneas de código muerto eliminadas (ADR-011) sin pérdida de funcionalidad.
- **Cobertura de regresión:** 4 tests nuevos reproducen el bug histórico de señal para que no vuelva a pasar.

## Configuración (`.env`)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `INITIAL_CAPITAL` | 1000 | Capital inicial |
| `SYMBOLS` | BTC,ETH,SOL,ADA,XRP | Activos vigilados |
| `TIMEFRAME` | 5m | Temporalidad |
| `LEVERAGE` | 10 | Apalancamiento |
| `RISK_PER_TRADE_PCT` | 1.0 | % riesgo por trade |
| `ATR_MULTIPLIER` | 2.0 | Stop dinámico ATR |
| `KELLY_FRACTION` | 0.25 | Kelly fraccional |
| `DAILY_LOSS_LIMIT` | 5.0 | % pérdida diaria máxima |
| `TREND_STRENGTH` | 0.0015 | Umbral de tendencia VWAP (0.15%) |
| `TELEGRAM_BOT_TOKEN` | — | Token bot Telegram |

## Tests

```bash
docker exec kavana-trading python -m pytest -q          # 112 tests
docker exec kavana-trading python -m pytest tests/test_analyzer_signals.py -v
```

## Documentación IT Consulting

- `docs/ADR-010-motor-de-senales.md` — Bug de señales: lógica contradictoria + umbral VWAP irreal.
- `docs/ADR-011-yagni-polymarket-cleanup.md` — Eliminación de código muerto.
- `docs/DECISIONS_LOG.md` — Registro de decisiones y lecciones aprendidas.
- `docs/technical-documentation.md` — Informe técnico completo.
- `docs/CONTRIBUTING.md` — Guía de contribución (TDD/YAGNI).

## ⚠️ Descargo de responsabilidad

**Paper trading únicamente.** El bot no opera capital real. Ningún contenido aquí es asesoramiento financiero.

## Licencia

Privado — KAVANA Systems © 2026
