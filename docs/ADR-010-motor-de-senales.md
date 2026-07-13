# ADR-010: Corrección del motor de señales — lógica contradictoria y umbral VWAP irreal

> **Estado:** Aceptado
> **Fecha:** 12/07/2026
> **Autor:** Auditoría técnica KAVANA
> **Componentes afectados:** `src/analyzer.py`, `src/main.py`

## Contexto

El bot llevaba **más de 24 horas sin emitir una sola señal** de trading a Telegram. El contenedor estaba vivo y escaneando (logs cada 60 s con "Dashboard guardado"), pero el analizador devolvía `NEUTRAL` en todos los ciclos.

La investigación reveló **dos defectos acumulados**, ambos introducidos durante la fase de "mejoras profesionales" (Analyzer V2, basadas en un cuaderno de NotebookLM):

### Defecto 1 — Lógica de señal mutuamente excluyente

Las condiciones para emitir señal exigían estados de mercado **opuestos al mismo tiempo**:

```python
# Lógica original (rota):
# BUY  → tendencia ALCISTA (precio +2% sobre VWAP)  Y  RSI < 30 (sobrevendido)
# SELL → tendencia BAJISTA (precio −2% bajo VWAP)   Y  RSI > 70 (sobrecomprado)
```

Un mercado en tendencia alcista no puede estar simultáneamente sobrevendido (RSI < 30): son estados contradictorios. Resultado: la condición **nunca se cumplía** → cero señales.

### Defecto 2 — Umbral de tendencia irreal (causa de fondo)

El filtro de tendencia exigía que el precio se desviara un **2%** (`TREND_STRENGTH = 0.02`) respecto de su VWAP de 20 velas para declarar "tendencia".

Medición empírica sobre datos reales de KuCoin (velas 5-15 min):

| Símbolo | Desvío medio | p75 | p90 | Máximo observado |
|---------|-------------|-----|-----|------------------|
| BTC/USDT | 0.07% | 0.10% | 0.14% | 0.21% |
| ETH/USDT | 0.12% | 0.16% | 0.26% | 0.45% |
| SOL/USDT | 0.13% | 0.22% | 0.25% | 0.41% |
| ADA/USDT | 0.17% | 0.25% | 0.34% | 0.51% |
| XRP/USDT | 0.10% | 0.15% | 0.20% | 0.29% |

El umbral del 2% era **entre 4× y 28× superior al desvío máximo real**. El VWAP es una media móvil que "persigue" al precio, por lo que la separación entre ambos casi nunca supera el 0.25%. Conclusión: el filtro clasificaba el mercado como "plano" de forma permanente.

## Decisión

### 1. Lógica coherente: tendencia = dirección, momentum = timing

La tendencia (VWAP) marca la **dirección permitida** y el RSI confirma el momentum **en esa misma dirección**, no en la opuesta:

```python
# Lógica corregida:
# BUY  → tendencia ALCISTA  Y  50 ≤ RSI < 80  (momentum comprador, sin sobrecompra)
# SELL → tendencia BAJISTA  Y  20 < RSI ≤ 50  (momentum vendedor, sin sobreventa)
# El MACD refuerza la señal (macd_confirms_up/down) pero no es obligatorio.
```

### 2. Umbral calibrado con datos reales y configurable

```python
TREND_STRENGTH = float(os.getenv("TREND_STRENGTH", "0.0015"))  # 0.15%
```

0.15% se sitúa en el percentil 75-90 del desvío real: capta tendencias genuinas sin dispararse con ruido lateral. Se expone como variable de entorno para recalibración sin tocar código.

### 3. Mitigación de rate-limit (429) en KuCoin

Se añadió una pausa de 1 s entre símbolos en `scan_cycle`, complementando el `enableRateLimit` de ccxt, tras observar errores intermitentes `429 Too many requests`.

## Metodología (TDD estricto)

1. **RED** — Se escribió `tests/test_analyzer_signals.py` con un mercado claramente alcista → debía dar `BUY`. Con la lógica rota devolvía `NEUTRAL` (test en rojo, bug reproducido).
2. **GREEN** — Corregida la lógica y el umbral. Los 4 tests de señal pasan.
3. Se detectó que los datos de prueba iniciales (líneas rectas) eran irreales: una tendencia lineal hace que el VWAP persiga al precio y lleva el RSI a extremos. Se reescribieron con patrón **zigzag** (impulsos + retrocesos), que imita el mercado real.

## Consecuencias

- **Positivas:**
  - El bot vuelve a emitir señales. Backtest sobre ~70 velas recientes: 5-32 señales por símbolo según tendencia (antes: 0 constante).
  - Umbral recalibrable vía `.env` sin redeploy de código.
  - Regresión blindada con 4 tests nuevos que reproducen el bug histórico.
  - Menos errores 429 de KuCoin.
- **Negativas / trade-offs:**
  - El umbral 0.15% es específico para BTC/ETH/SOL/ADA/XRP en 5-15 min. Otros activos o temporalidades requerirán recalibración (documentado).
  - La lógica sigue el sesgo de tendencia (trend-following); no captura reversiones. Decisión consciente: alinear con el filtro VWAP existente.
- **Alternativas consideradas:**
  - *Eliminar el filtro VWAP y operar solo con RSI/MACD* — rechazado: perdería el filtro de dirección que evita operar contra tendencia.
  - *Umbral fijo hardcodeado a 0.15%* — rechazado: no permite recalibración por activo/temporalidad.

## Verificación

```bash
docker exec kavana-trading python -m pytest -q
# 112 passed
```

Diagnóstico en vivo confirmó que en mercado lateral (los 5 pares < 0.15%) la respuesta `NEUTRAL` es ahora **correcta**, no un fallo.
