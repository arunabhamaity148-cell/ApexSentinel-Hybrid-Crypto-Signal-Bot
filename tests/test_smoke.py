import pytest
import pandas as pd
from datetime import datetime

from config import settings
from strategy.regime import MarketRegime
from filters.core_filters import apply_hard_filters
from data.models import SignalData
from core.utils import detect_swings  # Will be created if needed

def test_config_safety():
    """Ensure safe defaults."""
    assert settings.ENABLE_SAFE_MODE is True
    assert settings.MIN_RR >= 1.8
    assert settings.MAX_RISK_PER_TRADE <= 0.01
    assert len(settings.CORE_PAIRS) >= 6

def test_regime_detection():
    """Smoke test for regime detector."""
    dates = pd.date_range('2025-01-01', periods=100, freq='15T')
    df = pd.DataFrame({
        'open': [100 + i*0.05 for i in range(100)],
        'high': [101 + i*0.06 for i in range(100)],
        'low': [99 + i*0.04 for i in range(100)],
        'close': [100.5 + i*0.05 for i in range(100)],
        'volume': [10000 + i*10 for i in range(100)]
    }, index=dates)

    regime = MarketRegime.detect(df)
    assert regime in ["TREND", "RANGE", "VOLATILITY_EXPANSION", "DEAD"]

def test_hard_filters():
    """Test filter stack."""
    signal = SignalData(
        symbol="BTCUSDT",
        direction="LONG",
        entry=65000.0,
        sl=64000.0,
        tp1=67000.0,
        tp2=68500.0,
        rr=2.0,
        reason="Liquidity sweep test"
    )

    df = pd.DataFrame({
        'close': [65000.0] * 100,
        'high': [65200.0] * 100,
        'low': [64800.0] * 100,
        'volume': [5000.0] * 100
    })

    result = apply_hard_filters(signal, df, df)
    assert isinstance(result, bool)

def test_signal_data_model():
    """Validate data model."""
    signal = SignalData(
        symbol="ETHUSDT",
        direction="SHORT",
        entry=3200.0,
        sl=3250.0,
        tp1=3100.0,
        tp2=3000.0,
        rr=2.5,
        reason="Bearish liquidity sweep"
    )
    assert signal.rr == 2.5
    assert signal.direction == "SHORT"

@pytest.mark.asyncio
async def test_backtest_skeleton():
    """Ensure backtest engine doesn't crash."""
    from backtest.engine import BacktestEngine
    from data.binance_client import BinanceDataClient

    client = BinanceDataClient()
    engine = BacktestEngine(client)
    # Just test instantiation and method existence
    assert hasattr(engine, 'run_backtest')
    assert hasattr(engine, 'analyze_results')