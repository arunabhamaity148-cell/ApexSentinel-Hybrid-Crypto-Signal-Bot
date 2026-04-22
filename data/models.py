from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class KlineData:
    """Minimal typed model for klines (future extensibility)."""
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class SignalData:
    """Internal signal representation."""
    symbol: str
    direction: str
    entry: float
    sl: float
    tp1: float
    tp2: Optional[float]
    rr: float
    reason: str
    confidence: float = 0.0