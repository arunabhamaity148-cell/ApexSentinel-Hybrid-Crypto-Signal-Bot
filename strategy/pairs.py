import asyncio
from typing import List
import pandas as pd
from loguru import logger

from config import settings
from data.binance_client import BinanceDataClient

class PairManager:
    """Smart pair universe: Core + Dynamic high-quality leaders."""

    def __init__(self, data_client: BinanceDataClient):
        self.data_client = data_client

    async def get_active_pairs(self) -> List[str]:
        """Return final list of pairs to scan."""
        pairs = settings.CORE_PAIRS.copy()

        if settings.DYNAMIC_PAIR_LIMIT > 0:
            dynamic = await self._get_dynamic_pairs()
            pairs.extend([p for p in dynamic if p not in pairs])

        # Safety cap
        return pairs[:15]

    async def _get_dynamic_pairs(self) -> List[str]:
        """Select top volume + momentum leaders, reject illiquid/fake pumps."""
        try:
            tickers = await self.data_client.client.get_ticker()
            df = pd.DataFrame(tickers)

            df = df[df['symbol'].str.endswith('USDT')].copy()
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            df['quoteVolume'] = pd.to_numeric(df['quoteVolume'], errors='coerce')
            df['priceChangePercent'] = pd.to_numeric(df['priceChangePercent'], errors='coerce')

            df = df[
                (df['quoteVolume'] > settings.MIN_24H_VOLUME_USDT) &
                (abs(df['priceChangePercent']) < 30)  # reject extreme pumps
            ]

            df['score'] = df['quoteVolume'] * (1 + abs(df['priceChangePercent']) / 100)
            top_pairs = df.nlargest(settings.DYNAMIC_PAIR_LIMIT * 2, 'score')['symbol'].tolist()

            # Exclude core and stables
            dynamic = [s for s in top_pairs if s not in settings.CORE_PAIRS and not s.startswith(('USDC', 'BUSD', 'TUSD'))]
            return dynamic[:settings.DYNAMIC_PAIR_LIMIT]

        except Exception as e:
            logger.warning("Dynamic pair scan failed, using core only: {}", e)
            return []