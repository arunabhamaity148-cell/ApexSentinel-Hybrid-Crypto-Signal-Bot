import pandas as pd
from typing import Literal
from loguru import logger

RegimeType = Literal["TREND", "RANGE", "VOLATILITY_EXPANSION", "DEAD"]

class MarketRegime:
    """Layer 1: Detect market regime using price action and volatility."""

    @staticmethod
    def detect(df: pd.DataFrame) -> RegimeType:
        if len(df) < 50:
            return "DEAD"

        returns = df['close'].pct_change().dropna()
        recent_vol = returns.iloc[-20:].std() * 100
        avg_vol = returns.std() * 100

        # Dead market
        if recent_vol < 0.6:
            return "DEAD"

        # Volatility expansion
        if recent_vol > avg_vol * 1.8:
            return "VOLATILITY_EXPANSION"

        # Range vs Trend
        price_range = (df['high'].iloc[-30:].max() - df['low'].iloc[-30:].min()) / df['close'].iloc[-30:].mean()
        if price_range < 0.035:
            return "RANGE"

        return "TREND"