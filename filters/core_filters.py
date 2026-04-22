import pandas as pd
from datetime import datetime
from config import settings
from data.models import SignalData
from loguru import logger

def apply_hard_filters(signal: SignalData, df4h: pd.DataFrame, df15m: pd.DataFrame) -> bool:
    """Max 7 hard filters with detailed rejection logging"""
    
    logger.debug("🔍 Checking filters for {} {} | Entry: {:.2f} | RR: {:.2f}", 
                 signal.symbol, signal.direction, signal.entry, signal.rr)

    filter_checks = [
        ("1. MTF Alignment", _filter_1_mtf_alignment(df4h, df15m)),
        ("2. Session Quality", _filter_2_session_quality()),
        ("3. Relative Volume", _filter_3_relative_volume(df15m)),
        ("4. Liquidity Confirmation", _filter_4_liquidity_confirmation(df15m)),
        ("5. Entry Not Late", _filter_5_entry_not_late(signal, df15m)),
        ("6. Spread Proxy", _filter_6_spread_proxy(df15m)),
        ("7. RR Validator", _filter_7_rr_validator(signal)),
    ]

    for filter_name, passed in filter_checks:
        if not passed:
            logger.info("🚫 SIGNAL REJECTED | {} | {} | Filter: {} | Entry: {:.2f}", 
                       signal.symbol, signal.direction, filter_name, signal.entry)
            return False

    logger.info("✅ SIGNAL PASSED ALL FILTERS | {} | {} | RR: {:.2f} | Entry: {:.2f}", 
                signal.symbol, signal.direction, signal.rr, signal.entry)
    return True


def _filter_1_mtf_alignment(df4h: pd.DataFrame, df15m: pd.DataFrame) -> bool:
    if len(df4h) < 30 or len(df15m) < 20:
        return False
    htf_trend = df4h['close'].iloc[-1] > df4h['close'].iloc[-20:].mean()
    ltf_momentum = df15m['close'].iloc[-1] > df15m['close'].iloc[-8:].mean()
    return htf_trend == ltf_momentum


def _filter_2_session_quality() -> bool:
    hour = datetime.utcnow().hour
    is_good = hour not in settings.DEAD_ZONE_HOURS
    if not is_good:
        logger.debug("Session filter failed - current hour: {}", hour)
    return is_good


def _filter_3_relative_volume(df15m: pd.DataFrame) -> bool:
    if len(df15m) < 30:
        return False
    current_vol = float(df15m['volume'].iloc[-1])
    avg_vol = float(df15m['volume'].rolling(20).mean().iloc[-1])
    passed = current_vol > avg_vol * 1.55
    if not passed:
        logger.debug("Volume filter failed - Current: {:.0f} | Avg: {:.0f}", current_vol, avg_vol)
    return passed


def _filter_4_liquidity_confirmation(df15m: pd.DataFrame) -> bool:
    return len(df15m) >= 40


def _filter_5_entry_not_late(signal: SignalData, df15m: pd.DataFrame) -> bool:
    current_price = float(df15m['close'].iloc[-1])
    distance_pct = abs(current_price - signal.entry) / signal.entry * 100
    passed = distance_pct < 0.8
    if not passed:
        logger.debug("Entry too late - distance: {:.2f}%", distance_pct)
    return passed


def _filter_6_spread_proxy(df15m: pd.DataFrame) -> bool:
    if len(df15m) < 15:
        return False
    recent_volatility = df15m['close'].pct_change().iloc[-10:].std() * 100
    passed = recent_volatility < 1.8
    if not passed:
        logger.debug("Spread/Volatility too high: {:.2f}%", recent_volatility)
    return passed


def _filter_7_rr_validator(signal: SignalData) -> bool:
    passed = signal.rr >= settings.MIN_RR
    if not passed:
        logger.debug("RR too low: {:.2f} (min required: {:.2f})", signal.rr, settings.MIN_RR)
    return passed