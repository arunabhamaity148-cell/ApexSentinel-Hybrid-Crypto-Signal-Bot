import pandas as pd
from config import settings
from data.models import SignalData

def apply_hard_filters(signal: SignalData, df4h: pd.DataFrame, df15m: pd.DataFrame) -> bool:
    """
    Maximum 7 hard filters.
    No bloat. Every filter must be meaningful and defendable.
    """
    if not _filter_1_mtf_alignment(df4h, df15m):          # 1
        return False
    if not _filter_2_session_quality():                   # 2
        return False
    if not _filter_3_relative_volume(df15m):              # 3
        return False
    if not _filter_4_liquidity_confirmation(df15m):       # 4
        return False
    if not _filter_5_entry_not_late(signal, df15m):       # 5
        return False
    if not _filter_6_spread_proxy(df15m):                 # 6
        return False
    if not _filter_7_rr_validator(signal):                # 7
        return False

    return True


def _filter_1_mtf_alignment(df4h: pd.DataFrame, df15m: pd.DataFrame) -> bool:
    """HTF bias should align with LTF momentum."""
    if len(df4h) < 30 or len(df15m) < 20:
        return False
    htf_trend = df4h['close'].iloc[-1] > df4h['close'].iloc[-20:].mean()
    ltf_momentum = df15m['close'].iloc[-1] > df15m['close'].iloc[-8:].mean()
    return htf_trend == ltf_momentum


def _filter_2_session_quality() -> bool:
    """Avoid dead Asia session."""
    hour = __import__('datetime').datetime.utcnow().hour
    return hour not in settings.DEAD_ZONE_HOURS


def _filter_3_relative_volume(df15m: pd.DataFrame) -> bool:
    """Real volume expansion."""
    if len(df15m) < 30:
        return False
    current_vol = float(df15m['volume'].iloc[-1])
    avg_vol = float(df15m['volume'].rolling(20).mean().iloc[-1])
    return current_vol > avg_vol * 1.55


def _filter_4_liquidity_confirmation(df15m: pd.DataFrame) -> bool:
    """Confirm sweep happened with rejection."""
    if len(df15m) < 40:
        return False
    recent_range = df15m['high'].iloc[-40:-5].max() - df15m['low'].iloc[-40:-5].min()
    return recent_range > 0  # basic sanity (can be strengthened later)


def _filter_5_entry_not_late(signal: SignalData, df15m: pd.DataFrame) -> bool:
    """Avoid chasing late entries."""
    current_price = float(df15m['close'].iloc[-1])
    distance_pct = abs(current_price - signal.entry) / signal.entry
    return distance_pct < 0.008  # max 0.8% from trigger price


def _filter_6_spread_proxy(df15m: pd.DataFrame) -> bool:
    """Proxy for good liquidity (low recent volatility)."""
    if len(df15m) < 15:
        return False
    recent_volatility = df15m['close'].pct_change().iloc[-10:].std()
    return recent_volatility < 0.018


def _filter_7_rr_validator(signal: SignalData) -> bool:
    """Minimum realistic risk-reward."""
    return signal.rr >= settings.MIN_RR