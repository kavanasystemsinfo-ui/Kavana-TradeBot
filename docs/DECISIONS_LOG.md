# Registro de Decisiones y Lecciones Aprendidas — KAVANA Trading

> Formato IT Consulting. Cada entrada documenta situación, decisión, resultado y lección.

---

### 2026-07-12 — El bot no emitía señales (bug de motor de señales)

- **Situación:** Más de 24 h sin señales en Telegram. Contenedor vivo y escaneando, pero el analizador devolvía `NEUTRAL` en todos los ciclos.
- **Decisión tomada:** Auditoría con TDD. Se identificaron dos defectos: (1) lógica de señal con condiciones mutuamente excluyentes (tendencia alcista + RSI sobrevendido), (2) umbral de tendencia VWAP del 2%, cuando el desvío real del mercado es 0.07-0.25%. Se corrigió la lógica (tendencia = dirección, RSI = momentum en la misma dirección) y se recalibró el umbral a 0.15% con datos reales. Ver ADR-010.
- **Resultado:** Bot vuelve a emitir señales (backtest: 5-32 por símbolo según tendencia). 4 tests de regresión nuevos. Suite en verde.
- **Lección aprendida:** Los parámetros de un cuaderno teórico (NotebookLM) deben **validarse contra datos reales** antes de ponerse en producción. Un umbral del 2% suena razonable sobre el papel, pero es 10× mayor que lo que ocurre en velas de 5-15 min. Medir siempre antes de fijar constantes de mercado.
- **Próximos pasos:** Considerar recalibración automática del umbral por activo/temporalidad (percentil móvil del desvío VWAP).

---

### 2026-07-12 — Datos de prueba irreales enmascaraban el comportamiento

- **Situación:** El primer test de señal (tendencia como línea recta) seguía dando `NEUTRAL` incluso tras corregir la lógica.
- **Decisión tomada:** Reescribir los datos de prueba con patrón **zigzag** (impulsos + retrocesos), que imita el mercado real. Una línea recta hace que el VWAP persiga al precio (tendencia neutra) y lleva el RSI a extremos (0/100).
- **Resultado:** Tests representativos y en verde. El fixture zigzag quedó documentado en `test_analyzer_signals.py`.
- **Lección aprendida:** Un test con datos sintéticos poco realistas puede dar falsos negativos y ocultar que el código ya es correcto. Los datos de prueba deben reflejar la forma real del fenómeno, no un ideal matemático.
- **Próximos pasos:** Reutilizar el generador zigzag para futuros tests de estrategia.

---

### 2026-07-12 — Código muerto en el tracker de Polymarket

- **Situación:** Test `test_polymarket.py` fallando de forma persistente, ajeno al bug principal.
- **Decisión tomada:** Se confirmó que `src/polymarket.py` se instanciaba pero nunca se usaba (el rastreo real usa `polymarket_tracker.py`/`WalletTracker`). Aplicar YAGNI: eliminar módulo, instanciación y test. Ver ADR-011.
- **Resultado:** −177 líneas. Suite limpia (112 tests, 0 fallos, 0 deselecciones).
- **Lección aprendida:** Al reemplazar un componente (mercados → wallets), eliminar el antiguo en el mismo cambio. El código muerto genera tests rotos, confusión de nombres y ruido en auditorías.
- **Próximos pasos:** Revisar periódicamente instanciaciones sin uso (`grep self.X\.`).

---

### 2026-07-12 — Errores 429 intermitentes de KuCoin

- **Situación:** Logs con `429 Too many requests` esporádicos al escanear 5 símbolos cada 60 s.
- **Decisión tomada:** Añadir pausa de 1 s entre símbolos en `scan_cycle`, además del `enableRateLimit` de ccxt.
- **Resultado:** Reducción de errores 429. Coste: ~4 s extra por ciclo (asumible con intervalo de 60 s).
- **Lección aprendida:** `enableRateLimit` de ccxt no siempre basta bajo el rate-limit "system-level" de KuCoin; conviene un colchón propio.
- **Próximos pasos:** Si escala el nº de símbolos, evaluar backoff exponencial o caché de OHLCV.
