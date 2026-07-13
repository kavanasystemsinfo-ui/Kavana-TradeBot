# ADR-011: Eliminación del tracker de mercados Polymarket (YAGNI)

> **Estado:** Aceptado
> **Fecha:** 12/07/2026
> **Componentes afectados:** `src/polymarket.py` (eliminado), `src/main.py`, `tests/test_polymarket.py` (eliminado)

## Contexto

Durante la auditoría del motor de señales se detectó que la suite de tests tenía un fallo persistente (`test_polymarket.py::test_fetches_markets`) ajeno al bug principal.

Al investigar se confirmó que `src/polymarket.py` (clase `PolymarketTracker`, rastreo de **mercados** por keywords) era **código muerto**:

- Se instanciaba en `main.py` (`self.polymarket = PolymarketTracker(...)`).
- **Nunca se invocaba ninguno de sus métodos** (`grep "self.polymarket\." → 0 resultados`).
- El rastreo real de Polymarket lo hace `self.polymarket_wallets` (clase `WalletTracker` en `polymarket_tracker.py`), que sigue **wallets de smart money** en lugar de escanear mercados por palabras clave.

Esta duplicidad venía de la decisión previa (ADR de wallets) de reemplazar el escaneo de mercados por el seguimiento de wallets, pero el módulo antiguo quedó huérfano.

## Decisión

Aplicar **YAGNI**: eliminar el módulo muerto, su instanciación y su test.

- Borrado `src/polymarket.py`.
- Borrado `tests/test_polymarket.py`.
- Eliminada la línea `self.polymarket = PolymarketTracker(...)` y el import en `main.py`.

## Consecuencias

- **Positivas:**
  - Suite limpia: 112 tests, 0 fallos, 0 deselecciones.
  - −127 líneas de código muerto, −50 líneas de test obsoleto.
  - Elimina confusión entre dos "PolymarketTracker" con propósitos distintos.
- **Negativas:** Ninguna — el código no se ejecutaba.
- **Alternativas consideradas:**
  - *Arreglar el test roto* — rechazado: no tiene sentido mantener tests de código que no se usa (viola YAGNI).

## Verificación

```bash
grep -rn "src.polymarket\b" --include="*.py" .   # sin resultados (solo polymarket_tracker)
docker exec kavana-trading python -m pytest -q   # 112 passed
docker restart kavana-trading                     # arranque limpio, sin ImportError
```
