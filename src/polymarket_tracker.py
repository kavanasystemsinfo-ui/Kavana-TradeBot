"""Rastreador de wallets crypto en Polymarket — Smart Money Tracker."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("kavana.polymarket_tracker")

DATA_API = "https://data-api.polymarket.com"

# Palabras clave para identificar mercados crypto (copiado de polymarket.py)
CRYPTO_KEYWORDS = [
    "btc", "bitcoin", "eth", "ethereum", "sol", "solana", "xrp", "ripple",
    "ada", "cardano", "crypto", "token", "defi", "nft", "blockchain",
    "halving", "mining", "layer", "web3", "altcoin", "stablecoin",
    "usdt", "usdc", "doge", "matic", "polkadot", "dot", "link", "chainlink",
    "avax", "avalanche", "uniswap", "uni", "aave", "compound",
    "liquidity", "staking", "yield", "airdrop", "futures", "perp",
    "funding", "leverage", "binance", "kucoin", "coinbase",
    "sec", "etf", "spot", "onchain", "on-chain", "wallet",
    "arbitrum", "optimism", "base", "zksync", "scroll",
    "bitcoin etf", "memecoin", "meme coin", "celsius", "ftx",
]

NON_CRYPTO_EVENTS = [
    "super bowl", "nfl", "nba", "mlb", "soccer", "futbol", "tennis",
    "election", "president", "congress", "supreme court",
    "trump", "biden", "putin", "xi jinping", "kim jong",
    "grammy", "oscar", "emmy", "taylor swift", "beyonce",
    "rihanna", "gta", "grand theft auto", "call of duty", "fortnite",
    "netflix", "disney", "marvel", "dc comics",
    "weather", "hurricane", "earthquake", "covid",
    "box office", "imdb", "rotton tomatoes",
]


def is_crypto_market(market_name: str) -> bool:
    """Verifica si un mercado es de temática crypto."""
    name_lower = market_name.lower()
    for ne in NON_CRYPTO_EVENTS:
        if ne in name_lower:
            return False
    for kw in CRYPTO_KEYWORDS:
        if kw in name_lower:
            return True
    return False


# Wallets de traders crypto conocidos (del proyecto anterior)
TRADERS = [
    {"alias": "SeriouslySirius", "proxy_address": "0x16b29c00000000000000000000000000aa881"},
    {"alias": "swisstony", "proxy_address": "0x204f72f35326db932158cba6adff0b9a1da95e14"},
    {"alias": "Ballena-Top-01", "proxy_address": "0x2a2C53bD278c04DA9962Fcf96490E17F3DfB9Bc1"},
    {"alias": "Ballena-Top-02", "proxy_address": "0x492442EaB586F242B53bDa933fD5dE859c8A3782"},
    {"alias": "Ballena-Top-03", "proxy_address": "0x2c335066FE58fe9237c3d3Dc7b275C2a034a0563"},
    {"alias": "Ballena-Top-04", "proxy_address": "0x5966Db1fE50763C9e3C014d756369BAd07E1F804"},
]

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "polymarket_state.json"


class WalletTracker:
    """Monitorea wallets de Polymarket y registra trades nuevos."""

    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url
        self.last_seen: dict[str, str] = {}
        self._load_state()

    def _load_state(self):
        """Recupera el último txHash visto por wallet."""
        try:
            if STATE_FILE.exists():
                self.last_seen = json.loads(STATE_FILE.read_text())
                logger.info("📂 Estado Polymarket: %d wallets", len(self.last_seen))
        except Exception as e:
            logger.warning("⚠️ Error cargando estado Polymarket: %s", e)

    def _save_state(self):
        """Persiste el estado."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(self.last_seen, indent=2))
        except Exception as e:
            logger.warning("⚠️ Error guardando estado: %s", e)

    def fetch_user_trades(self, address: str, limit: int = 10) -> list[dict]:
        """Obtiene los últimos trades de una wallet y resuelve nombres de mercado."""
        import urllib.request
        url = f"{DATA_API}/trades?user={address}&limit={limit}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (KAVANA-Trading/2.0)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                trades = data if isinstance(data, list) else []
                # Resolver nombres de mercado
                for t in trades:
                    if t.get("conditionId") and not t.get("market"):
                        t["market"] = self._resolve_market(t["conditionId"])
                return trades
        except Exception as e:
            logger.warning("⚠️ Error fetching trades para %s: %s", address[:8], e)
            return []

    def _resolve_market(self, condition_id: str) -> str:
        """Resuelve un conditionId a nombre de mercado legible."""
        import urllib.request
        try:
            url = f"https://gamma-api.polymarket.com/markets?conditionId={condition_id}&limit=1"
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (KAVANA-Trading/2.0)",
            })
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                if isinstance(data, list) and data:
                    return data[0].get("question", condition_id[:20])
        except Exception:
            pass
        return condition_id[:20]

    def get_new_trades(self, address: str, trades: list[dict]) -> list[dict]:
        """Filtra solo los trades nuevos (no vistos antes)."""
        last_hash = self.last_seen.get(address, "")

        # Encontrar trades nuevos (más recientes que el último visto)
        nuevos = []
        for t in trades:
            # Filtrar mercados no-crypto
            market_name = t.get("market", t.get("conditionId", ""))
            if market_name and not is_crypto_market(market_name):
                logger.debug("⏭️ Mercado no-crypto: %s", market_name[:40])
                continue
            tx_hash = t.get("txHash", t.get("transactionHash", ""))
            if not tx_hash:
                continue
            if tx_hash == last_hash:
                break  # Llegamos al último visto, los anteriores ya se procesaron
            nuevos.append(t)

        # Actualizar último hash visto
        if nuevos:
            latest_hash = nuevos[0].get("txHash", nuevos[0].get("transactionHash", ""))
            if latest_hash:
                self.last_seen[address] = latest_hash
                self._save_state()

        return nuevos

    async def send_trade_to_webhook(
        self,
        trade: dict,
        alias: str = "unknown",
        capital: float = 1000,
    ) -> bool:
        """Envía un trade de wallet a la pestaña POLYMARKET."""
        if not self.webhook_url:
            return False

        import aiohttp
        market = trade.get("market", trade.get("conditionId", "???"))[:60]
        side = trade.get("side", "?")
        price = trade.get("price", "0")
        size = trade.get("size", "0")
        direction = "BUY" if side == "BUY" else "SELL"

        payload = {
            "sheet": "POLYMARKET",
            "activo": f"[{alias}] {market}",
            "estrategia": f"SMART_MONEY_{alias.upper()}",
            "direccion": direction,
            "precio_entrada": float(price),
            "precio_salida": float(price),
            "inversion": float(size),
            "apalancamiento": 1,
            "resultado": f"{direction} {size}@${price}",
            "pnl_neto": 0,
            "capital_actual": capital,
            "capital_inicial": 1000,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload, timeout=10) as resp:
                    ok = resp.status == 200
                    if ok:
                        logger.info("📊 [%s] %s %s $%s", alias, side, market[:30], price)
                    return ok
        except Exception as e:
            logger.warning("⚠️ Error enviando trade: %s", e)
            return False
