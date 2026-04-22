import pandas as pd
from typing import Optional
from loguru import logger

from config import settings
from data.models import SignalData

class TargetEngine:
    """Realistic TP/SL and RR calculation."""

    def create_signal(self, symbol: str, direction: str, df15m: pd.DataFrame, reason: str) -> Optional[SignalData]:
        price = float(df15m['close'].iloc[-1])
        atr = self._calculate_atr(df15m)

        if atr <= 0:
            return None

        sl_dist = atr * 1.65
        sl = price - sl_dist if direction == "LONG" else price + sl_dist
        tp1 = price + sl_dist * 2.0 if direction == "LONG" else price - sl_dist * 2.0
        tp2 = price + sl_dist * 3.5 if direction == "LONG" else price - sl_dist * 3.5

        rr = round(abs((tp1 - price) / (price - sl)), 2)

        if rr < settings.MIN_RR:
            return None

        return SignalData(
            symbol=symbol,
            direction=direction,
            entry=price,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
            rr=rr,
            reason=reason
        )

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        if len(df) < period:
            return 0.0
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return float(tr.rolling(window=period).mean().iloc[-1])