import pandas as pd
from datetime import datetime
from typing import List, Optional
from loguru import logger

from config import settings
from data.binance_client import BinanceDataClient
from strategy.signals import SignalEngine
from data.models import SignalData
from filters.core_filters import apply_hard_filters

class BacktestEngine:
    """
    Walk-forward / paper backtest engine using the exact same logic as live.
    Critical for scientific validation.
    """

    def __init__(self, data_client: BinanceDataClient):
        self.data_client = data_client
        # We reuse the same SignalEngine but in offline mode
        self.signal_engine = None  # will be set externally with mock journal/notifier

    async def run_backtest(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """
        Run backtest on historical data using identical code path.
        Note: Full implementation would require bar-by-bar simulation.
        This is the skeleton for same-logic validation.
        """
        logger.info("Starting backtest from {} to {}", start_date, end_date)
        results = []

        for symbol in symbols:
            try:
                # Fetch full history
                df4h = await self.data_client.get_klines(symbol, settings.HTF, limit=2000)
                df15m = await self.data_client.get_klines(symbol, settings.LTF, limit=8000)

                if df4h is None or df15m is None:
                    continue

                # Simulate scan at each 15m bar (simplified for production start)
                for i in range(100, len(df15m) - 50, 4):  # step every hour approx
                    # Slice data up to current bar (no future leak)
                    hist4h = df4h[df4h.index <= df15m.index[i]]
                    hist15m = df15m.iloc[:i+1]

                    if len(hist4h) < 80 or len(hist15m) < 80:
                        continue

                    # Use same signal logic
                    signal = await self._simulate_signal_generation(symbol, hist4h, hist15m)
                    if signal:
                        results.append({
                            'timestamp': df15m.index[i],
                            'symbol': symbol,
                            'direction': signal.direction,
                            'entry': signal.entry,
                            'rr': signal.rr,
                            'reason': signal.reason
                        })

            except Exception as e:
                logger.error("Backtest error on {}: {}", symbol, e)

        df_results = pd.DataFrame(results)
        logger.info("Backtest completed. Generated {} signals", len(df_results))
        return df_results

    async def _simulate_signal_generation(self, symbol: str, df4h: pd.DataFrame, df15m: pd.DataFrame) -> Optional[SignalData]:
        """Reuse core logic from live engine (simplified call)."""
        # This would call the same functions from strategy/signals.py in real implementation
        # For now we return None as placeholder for full integration
        # In production you would inject the live engine here
        return None

    def analyze_results(self, results_df: pd.DataFrame):
        """Basic backtest analytics."""
        if results_df.empty:
            logger.warning("No signals generated in backtest")
            return

        print("\n=== Backtest Summary ===")
        print(f"Total signals: {len(results_df)}")
        print(f"Unique pairs: {results_df['symbol'].nunique()}")
        print("\nSignals per pair:")
        print(results_df['symbol'].value_counts().head(10))