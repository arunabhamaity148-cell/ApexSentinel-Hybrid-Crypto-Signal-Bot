import asyncio
from typing import Optional, Dict
import pandas as pd
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger

from config import settings
from data.cache import KlineCache
from data.models import KlineData

class BinanceDataClient:
    """Production-grade Binance data layer with retry, reconnect and caching."""

    def __init__(self):
        self.client: Optional[AsyncClient] = None
        self.cache = KlineCache()
        self._healthy = False

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((BinanceAPIException, asyncio.TimeoutError, ConnectionError))
    )
    async def initialize(self):
        """Initialize async client."""
        if self.client:
            await self.client.close_connection()

        self.client = await AsyncClient.create(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_API_SECRET,
            testnet=settings.USE_TESTNET
        )
        self._healthy = True
        logger.info("✅ Binance AsyncClient initialized (Testnet: {})", settings.USE_TESTNET)

    async def get_klines(self, symbol: str, interval: str, limit: int = None) -> Optional[pd.DataFrame]:
        """Fetch klines with cache fallback and auto refresh."""
        if not self.client:
            await self.initialize()

        limit = limit or settings.HISTORY_LIMIT
        cache_key = f"{symbol}_{interval}"

        # Try cache first
        cached = self.cache.get(cache_key)
        if cached is not None and not self.cache.is_stale(cache_key):
            return cached

        try:
            raw = await self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            
            df = pd.DataFrame(raw, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df = df.astype({
                'open': 'float64', 'high': 'float64', 'low': 'float64',
                'close': 'float64', 'volume': 'float64'
            })
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df.set_index('open_time', inplace=True)

            self.cache.set(cache_key, df)
            return df

        except Exception as e:
            logger.error("Klines fetch failed for {} {}: {}", symbol, interval, e)
            self._healthy = False
            return cached  # fallback to cache

    def is_healthy(self) -> bool:
        return self._healthy and self.client is not None

    async def close(self):
        if self.client:
            await self.client.close_connection()
            logger.info("Binance client closed gracefully.")