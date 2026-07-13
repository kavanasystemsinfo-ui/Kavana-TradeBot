# Guía de Contribución — KAVANA Trading Bot

## Filosofía de Desarrollo

Este proyecto sigue principios de **TDD** (Test-Driven Development) y **YAGNI** (You Aren't Gonna Need It) para mantener la calidad del código y evitar la sobreingeniería. La disciplina de pruebas no es opcional: es la única forma de detectar regresiones en una estrategia de trading que se ejecuta 24/7.

## Antes de Escribir Código

1. Escribe una prueba que falle (fase **RED** de TDD).
2. Ejecuta las pruebas para confirmar que falla por la razón esperada.
3. Escribe el **mínimo código** necesario para hacer que la prueba pase (fase **GREEN**).
4. Refactoriza solo si mejora la legibilidad o elimina duplicación (fase **REFACTOR**).

### Regla de datos de prueba (aprendida en ADR-010)

Los fixtures de mercado deben usar un **patrón zigzag** (impulsos + retrocesos), no líneas rectas. Una línea recta hace que el VWAP persiga al precio (tendencia neutra constante) y lleva el RSI a extremos, enmascarando el comportamiento real del analizador.

## Commits Significativos

Cada commit debe responder: **"¿Qué problema específico resuelve este cambio?"**

- ✅ `"fix(analyzer): umbral VWAP 2%→0.15% calibrado con datos KuCoin reales — recupera señales"`
- ✅ `"refactor: elimina PolymarketTracker muerto (YAGNI), 112 tests en verde"`
- ❌ `"fix"`, `"update"`, `"cambios varios"`

## Antes de Hacer Push

1. Ejecuta la suite completa: `docker exec kavana-trading python -m pytest -q`
2. **0 fallos y 0 deselecciones** son requisito de salida.
3. Confirma que el contenedor arranca sin `ImportError` tras el cambio.

## Calibración de Parámetros de Mercado (lección ADR-010)

- Nunca fijes constantes de mercado (umbrales, % de desvío) basándote solo en intuición o un cuaderno teórico.
- **Mide primero** con datos reales del exchange (desvío VWAP p75/p90/máx por símbolo).
- Expón parámetros críticos como variables de entorno (`TREND_STRENGTH`) para recalibrar sin redeploy.

## Eliminación de Código Muerto (lección ADR-011)

- Al reemplazar un componente, elimina el antiguo en el **mismo** cambio (módulo + instanciación + tests).
- Si `grep "self.X."` da 0 resultados para un atributo, es candidato a borrado.

## Estructura de Tests

| Archivo | Foco | Tests |
|---------|------|-------|
| `test_analyzer_signals.py` | Regresión del motor de señales (zigzag) | 4 |
| `test_analyzer.py` | Indicadores y filtro VWAP | 11 |
| `test_trader.py` | Paper trading + Risk Manager | 13 |
| `test_risk.py` | Stops ATR, Kelly, límite diario | 9 |
| `test_polymarket_tracker.py` | Wallets smart money | 14 |
| `test_db.py` / `test_exchange.py` / `test_notifier.py` / `test_exporter.py` / `test_config.py` / `test_dashboard.py` / `test_main.py` | Integración por módulo | 6-10 c/u |

Total: **112 tests**.
