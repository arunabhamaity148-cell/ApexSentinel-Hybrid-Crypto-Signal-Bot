import pandas as pd
from loguru import logger

from tracking.journal import TradeJournal

class PerformanceMetrics:
    """Advanced metrics calculator for validation."""

    def __init__(self, journal: TradeJournal):
        self.journal = journal

    def calculate_expectancy(self) -> float:
        """Expectancy in R units."""
        df = self.journal.get_recent_signals(limit=500)
        closed = df[df['outcome'].notna()].copy()
        if closed.empty:
            return 0.0

        win_rate = (closed['outcome'] == 'WIN').mean()
        avg_win = closed[closed['outcome'] == 'WIN']['realized_rr'].mean() or 0
        avg_loss = abs(closed[closed['outcome'] == 'LOSS']['realized_rr'].mean() or 1.0)

        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        logger.info("Expectancy: {:.3f}R | Win Rate: {:.1f}%", expectancy, win_rate * 100)
        return expectancy

    def get_pair_performance(self) -> pd.DataFrame:
        """Performance broken down by pair."""
        df = self.journal.get_recent_signals(limit=1000)
        if df.empty:
            return pd.DataFrame()

        closed = df[df['outcome'].notna()]
        return closed.groupby('symbol').agg(
            signals=('symbol', 'count'),
            win_rate=('outcome', lambda x: (x == 'WIN').mean() * 100),
            avg_rr=('realized_rr', 'mean')
        ).round(2)

    def get_rejection_stats(self) -> dict:
        """How many signals were rejected by filters."""
        total = pd.read_sql_query("SELECT COUNT(*) as cnt FROM signals", self.journal.conn).iloc[0]['cnt']
        closed = pd.read_sql_query(
            "SELECT COUNT(*) as cnt FROM signals WHERE outcome IS NOT NULL", 
            self.journal.conn
        ).iloc[0]['cnt']
        
        return {
            "total_generated": total,
            "closed_trades": closed,
            "rejection_rate": round((1 - closed / total) * 100, 1) if total > 0 else 0
        }