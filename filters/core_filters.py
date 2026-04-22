import pandas as pd
from datetime import datetime
from config import settings
from data.models import SignalData
from loguru import logger

def apply_hard_filters(signal: SignalData, df4h: pd.DataFrame, df15m: pd.DataFrame) -> bool:
    """Strict filters for HIGH QUALITY signals only"""
    
    logger.debug("🔍 Quality Check for {} {} | Entry: {:.2f} | RR: {:.2f}", 
                 signal.symbol, signal.direction, signal.entry, signal.rr)

    filter_checks = [
        ("1. Strong MTF Alignment", _filter_1_strong_mtf_alignment(df4h, df15m)),
        ("2. Good Session", _filter_2_session_quality()),
        ("3. Strong Relative Volume", _filter_3_strong_relative_volume(df15m)),
        ("4. Clear Liquidity Sweep", _filter_4_clear_liquidity_sweep(df15m, signal.direction)),
        ("5. Clean Entry", _filter_5_clean_entry(signal, df15m)),
        ("6. Low Volatility Proxy", _filter_6_low_volatility(df15m)),
        ("7. Good RR", _filter_7_rr_validator(signal)),
    ]

    for filter_name, passed in filter_checks:
        if not passed:
            logger.info("🚫 QUALITY REJECTED | {} | {} | ❌ {}", 
                       signal.symbol, signal.direction, filter_name)
            return False

    logger.info("✅ HIGH QUALITY SIGNAL PASSED | {} | {} | RR: {:.2f}", 
                signal.symbol, signal.direction, signal.rr)
    return True


def _filter_1_strong_mtf_alignment(df4h: pd.DataFrame, df15m: pd.DataFrame) -> bool:
    """Very strict MTF alignment for quality"""
    if len(df4h) < 40 or len(df15m) < 30:
        return False
    
    htf_trend = df4h['close'].iloc[-1] > df4h['close'].iloc[-30:].mean()
    ltf_momentum = df15m['close'].iloc[-1] > df15m['close'].iloc[-10:].mean()
    
    # Must have strong alignment + momentum in same direction
    if htf_trend != ltf_momentum:
        return False
    
    # Additional strength check
    htf_strength = abs((df4h['close'].iloc[-1] - df4h['close'].iloc[-30:].mean()) / df4h['close'].iloc[-30:].mean())
    return htf_strength > 0.005  # at least 0.5% move in HTF


def _filter_2_session_quality() -> bool:
    hour = datetime.utcnow().hour
    is_good = hour not in settings.DEAD_ZONE_HOURS
    if not is_good:
        logger.debug("⛔ Bad session (Asia dead zone)")
    return is_good


def _filter_3_strong_relative_volume(df15m: pd.DataFrame) -> bool:
    """Strong volume filter for quality"""
    if len(df15m) < 30:
        return False
    current_vol = float(df15m['volume'].iloc[-1])
    avg_vol = float(df15m['volume'].rolling(20).mean().iloc[-1])
    ratio = current_vol / avg_vol if avg_vol > 0 else 0
    passed = ratio > 1.8   # stricter than before
    if not passed:
        logger.debug("Volume too weak: {:.2f}x", ratio)
    return passed


def _filter_4_clear_liquidity_sweep(df15m: pd.DataFrame, direction: str) -> bool:
    """Clear liquidity sweep confirmation"""
    if len(df15m) < 50:
        return False
    
    recent_low = float(df15m['low'].iloc[-40:-8].min())
    recent_high = float(df15m['high'].iloc[-40:-8].max())
    
    if direction == "LONG":
        return df15m['low'].iloc[-12:].min() <= recent_low * 1.001
    else:
        return df15m['high'].iloc[-12:].max() >= recent_high * 0.999


def _filter_5_clean_entry(signal: SignalData, df15m: pd.DataFrame) -> bool:
    """Avoid late entries"""
    current_price = float(df15m['close'].iloc[-1])
    distance_pct = abs(current_price - signal.entry) / signal.entry * 100
    passed = distance_pct < 0.5   # stricter: max 0.5%
    if not passed:
        logger.debug("Entry too late: {:.2f}%", distance_pct)
    return passed


def _filter_6_low_volatility(df15m: pd.DataFrame) -> bool:
    """Clean price action (low recent volatility)"""
    if len(df15m) < 20:
        return False
    recent_vol = df15m['close'].pct_change().iloc[-10:].std() * 100
    passed = recent_vol < 1.2   # stricter
    if not passed:
        logger.debug("Too volatile: {:.2f}%", recent_vol)
    return passed


def _filter_7_rr_validator(signal: SignalData) -> bool:
    passed = signal.rr >= 2.2   # stricter RR
    if not passed:
        logger.debug("RR too low: {:.2f}", signal.rr)
    return passed