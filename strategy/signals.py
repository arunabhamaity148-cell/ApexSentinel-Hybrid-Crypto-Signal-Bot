import asyncio
import pandas as pd
from datetime import datetime
from typing import Optional

from loguru import logger

from config import settings
from data.binance_client import BinanceDataClient
from tracking.journal import TradeJournal
from notification.telegram_bot import TelegramNotifier
from risk.manager import RiskManager
from strategy.regime import MarketRegime
from strategy.pairs import PairManager
from strategy.targets import TargetEngine
from filters.core_filters import apply_hard_filters
from data.models import SignalData
from core.utils import detect_swings


class SignalEngine:
    """Main signal generation engine with heavy debugging logs."""

    def __init__(self, data_client: BinanceDataClient, journal: TradeJournal,
                 notifier: TelegramNotifier, risk_manager: RiskManager):
        self.data_client = data_client
        self.journal = journal
        self.notifier = notifier
        self.risk_manager = risk_manager
        self.pair_manager = PairManager(data_client)
        self.target_engine = TargetEngine()

    async def start_scanner(self):
        logger.info("Scanner started - scanning every {} minutes", settings.SCAN_INTERVAL_MINUTES)
        while True:
            try:
                await self.scan_market()
                await asyncio.sleep(settings.SCAN_INTERVAL_MINUTES * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scanner error: {}", e)
                await asyncio.sleep(30)

    async def scan_market(self):
        pairs = await self.pair_manager.get_active_pairs()
        logger.debug("Scanning {} pairs: {}", len(pairs), pairs)

        signals_count = 0
        for symbol in pairs:
            if not self.risk_manager.can_trade(symbol):
                logger.debug("Risk blocked: {}", symbol)
                continue

            signal = await self._generate_signal(symbol)
            if signal:
                if self.risk_manager.accept_signal(signal):
                    self.journal.log_signal(signal)
                    await self.notifier.send_signal(signal)
                    signals_count += 1

        if signals_count == 0:
            logger.debug("No signals generated in this scan cycle")

    async def _generate_signal(self, symbol: str) -> Optional[SignalData]:
        """Core pipeline with detailed step-by-step logging"""
        logger.debug("=== Starting signal generation for {} ===", symbol)

        # Step 1: HTF Data
        df4h = await self.data_client.get_klines(symbol, settings.HTF)
        if df4h is None or len(df4h) < 100:
            logger.debug("Failed: Not enough 4H data for {}", symbol)
            return None
        logger.debug("4H data loaded: {} candles", len(df4h))

        # Step 2: Regime
        regime = MarketRegime.detect(df4h)
        logger.debug("Regime detected: {}", regime)
        if regime in ("DEAD", "RANGE"):
            logger.debug("Rejected by regime: {}", regime)
            return None

        # Step 3: Bias
        bias = self._determine_bias(df4h)
        if not bias:
            logger.debug("No clear bias found for {}", symbol)
            return None
        logger.debug("Bias determined: {}", bias)

        # Step 4: LTF Data
        df15m = await self.data_client.get_klines(symbol, settings.LTF, limit=300)
        if df15m is None or len(df15m) < 80:
            logger.debug("Failed: Not enough 15M data for {}", symbol)
            return None
        logger.debug("15M data loaded: {} candles", len(df15m))

        # Step 5: Trigger
        trigger_reason = self._detect_trigger(df15m, bias)
        if not trigger_reason:
            logger.debug("No liquidity trigger found for {}", symbol)
            return None
        logger.debug("Trigger found: {}", trigger_reason)

        # Step 6: Create Signal
        signal = self.target_engine.create_signal(symbol, bias, df15m, trigger_reason)
        if not signal:
            logger.debug("TargetEngine failed to create signal for {}", symbol)
            return None

        logger.debug("Signal candidate created: {} {} RR:{:.2f}", symbol, bias, signal.rr)

        # Step 7: Hard Filters
        if not apply_hard_filters(signal, df4h, df15m):
            logger.debug("Hard filters rejected the signal for {}", symbol)
            return None

        logger.info("✅ FINAL SIGNAL GENERATED | {} | {} | RR: {:.2f}", symbol, bias, signal.rr)
        return signal

    def _determine_bias(self, df4h: pd.DataFrame) -> Optional[str]:
        swings = detect_swings(df4h, strength=6)
        logger.debug("Detected {} swings in 4H chart", len(swings))
        if len(swings) < 4:
            return None

        highs = [s['price'] for s in swings if s['type'] == 'high'][-3:]
        lows = [s['price'] for s in swings if s['type'] == 'low'][-3:]

        if len(highs) < 2 or len(lows) < 2:
            return None

        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            return "LONG"
        if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            return "SHORT"
        return None

    def _detect_trigger(self, df15m: pd.DataFrame, bias: str) -> Optional[str]:
        if len(df15m) < 60:
            return None

        price = float(df15m['close'].iloc[-1])
        vol = float(df15m['volume'].iloc[-1])
        avg_vol = float(df15m['volume'].rolling(20).mean().iloc[-1])

        recent_low = float(df15m['low'].iloc[-50:-5].min())
        recent_high = float(df15m['high'].iloc[-50:-5].max())

        volume_ok = vol > avg_vol * 1.6

        if bias == "LONG" and volume_ok and df15m['low'].iloc[-8:].min() <= recent_low * 1.001:
            return "Bullish liquidity sweep + volume"

        if bias == "SHORT" and volume_ok and df15m['high'].iloc[-8:].max() >= recent_high * 0.999:
            return "Bearish liquidity sweep + volume"

        return None