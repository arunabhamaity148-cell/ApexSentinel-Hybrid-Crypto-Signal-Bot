from typing import Dict, Optional
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

class KlineCache:
    """Simple in-memory cache with staleness check."""

    def __init__(self):
        self.cache: Dict[str, pd.DataFrame] = {}
        self.timestamps: Dict[str, datetime] = {}

    def set(self, key: str, df: pd.DataFrame):
        self.cache[key] = df.copy()
        self.timestamps[key] = datetime.utcnow()
        logger.debug("Cache updated for {}", key)

    def get(self, key: str) -> Optional[pd.DataFrame]:
        return self.cache.get(key)

    def is_stale(self, key: str, max_age_minutes: int = 15) -> bool:
        ts = self.timestamps.get(key)
        if not ts:
            return True
        return datetime.utcnow() - ts > timedelta(minutes=max_age_minutes)

    def clear(self):
        self.cache.clear()
        self.timestamps.clear()