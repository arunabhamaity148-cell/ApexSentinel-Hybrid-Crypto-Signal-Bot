import pandas as pd
from datetime import datetime
from config import settings
from data.models import SignalData
from loguru import logger

def apply_hard_filters(signal: SignalData, df4h: pd.DataFrame, df15m: pd.DataFrame) -> bool:
    """Per-pair detailed filter check with clear rejection reasons"""
    
    logger.info("🔍 FILTER CHECK STARTED → {} | {} | Entry: {:.2f} | RR: {:.2f}", 
                signal.symbol, signal.direction, signal.entry, signal.rr)

    results = []

    # 1. Strong MTF Alignment
    passed = _filter_1_strong_mtf_alignment(df4h, df15m)
    results.append(("1. MTF Alignment", passed))
    if not passed:
        logger.info("❌ REJECTED | {} | Filter: 1. MTF Alignment", signal.symbol)

    # 2. Session Quality
    passed = _filter_2_session_quality()
    results.append(("2. Session Quality", passed))
    if not passed:
        logger.info("❌ REJECTED | {} | Filter: 2. Session Quality (Dead Zone)", signal.symbol)

    # 3. Strong Relative Volume
    passed = _filter_3_strong_relative_volume(df15m)
    results.append(("3. Strong Volume", passed))
    if not passed:
        logger.info("❌ REJECTED | {} | Filter: 3. Strong Relative Volume", signal.symbol)

    # 4. Clear Liquidity Sweep
    passed = _filter_4_clear_liquidity_sweep(df15m, signal.direction)
    results.append(("4. Liquidity Sweep", passed))
    if not passed:
        logger.info("❌ REJECTED | {} | Filter: 4. Clear Liquidity Sweep", signal.symbol)

    # 5. Clean Entry
    passed = _filter_5_clean_entry(signal, df15m)
    results.append(("5. Clean Entry", passed))
    if not passed:
        logger.info("❌ REJECTED | {} | Filter: 5. Clean Entry (Late Entry)", signal.symbol)

    # 6. Low Volatility (Clean Price Action)
    passed = _filter_6_low_volatility(df15m)
    results.append(("6. Clean Price Action", passed))
    if not passed:
        logger.info("❌ REJECTED | {} | Filter: 6. Clean Price Action", signal.symbol)

    # 7. Good RR
    passed = _filter_7_rr_validator(signal)
    results.append(("7. RR Validator", passed))
    if not passed:
        logger.info("❌ REJECTED | {} | Filter: 7. RR Validator", signal.symbol)

    # Final Result
    all_passed = all(p for _, p in results)
    if all_passed:
        logger.info("✅ HIGH QUALITY SIGNAL PASSED ALL FILTERS | {} | {} | RR: {:.2f}", 
                    signal.symbol, signal.direction, signal.rr)
        return True
    else:
        logger.info("⛔ SIGNAL BLOCKED | {} | {} | Not all filters passed", 
                    signal.symbol, signal.direction)
        return False


# ==================== Individual Strict Filters ====================

def _filter_1_strong_mtf_alignment(df4h: pd.DataFrame, df15m: pd.DataFrame) -> bool:
    if len(df4h) < 40 or len(df15m) < 30:
        return False
    htf_trend = df4h['close'].iloc[-1] > df4h['close'].iloc[-30:].mean()
    ltf_momentum = df15m['close'].iloc[-1] > df15m['close'].iloc[-10:].mean()
    return htf_trend == ltf_momentum


def _filter_2_session_quality() -> bool:
    hour = datetime.utcnow().hour
    return hour not in settings.DEAD_ZONE_HOURS


def _filter_3_strong_relative_volume(df15m: pd.DataFrame) -> bool:
    if len(df15m) < 30:
        return False
    current_vol = float(df15m['volume'].iloc[-1])
    avg_vol = float(df15m['volume'].rolling(20).mean().iloc[-1])
    return current_vol > avg_vol * 1.85   # Quality focus - stricter


def _filter_4_clear_liquidity_sweep(df15m: pd.DataFrame, direction: str) -> bool:
    if len(df15m) < 50:
        return False
    recent_low = float(df15m['low'].iloc[-40:-8].min())
    recent_high = float(df15m['high'].iloc[-40:-8].max())
    
    if direction == "LONG":
        return df15m['low'].iloc[-12:].min() <= recent_low * 1.001
    else:
        return df15m['high'].iloc[-12:].max() >= recent_high * 0.999


def _filter_5_clean_entry(signal: SignalData, df15m: pd.DataFrame) -> bool:
    current_price = float(df15m['close'].iloc[-1])
    distance_pct = abs(current_price - signal.entry) / signal.entry * 100
    return distance_pct < 0.6   # Quality: max 0.6% late entry


def _filter_6_low_volatility(df15m: pd.DataFrame) -> bool:
    if len(df15m) < 20:
        return False
    recent_vol = df15m['close'].pct_change().iloc[-10:].std() * 100
    return recent_vol < 1.3   # Clean price action


def _filter_7_rr_validator(signal: SignalData) -> bool:
    return signal.rr >= 2.3   # Quality: minimum 2.3 RR