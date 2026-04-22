import pandas as pd
from typing import List, Dict

def detect_swings(df: pd.DataFrame, strength: int = 5) -> List[Dict]:
    """Deterministic swing high/low detection used in bias calculation."""
    if len(df) < strength * 2:
        return []
    
    swings = []
    for i in range(strength, len(df) - strength):
        # Swing High
        if df['high'].iloc[i] == df['high'].iloc[i-strength:i+strength+1].max():
            swings.append({
                'price': float(df['high'].iloc[i]),
                'type': 'high'
            })
        # Swing Low
        elif df['low'].iloc[i] == df['low'].iloc[i-strength:i+strength+1].min():
            swings.append({
                'price': float(df['low'].iloc[i]),
                'type': 'low'
            })
    return swings