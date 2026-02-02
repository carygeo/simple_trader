"""
Low-Frequency High-Conviction Strategies
Target: < 30 trades/year with high win rate
"""

import pandas as pd
import numpy as np
from .strategies import Signal, TradeSignal, calculate_sma, calculate_ema, calculate_rsi
from .advanced_strategies import calculate_atr, calculate_adx


class WeeklyMomentumStrategy:
    """
    Weekly Momentum - Only rebalance weekly based on momentum
    
    Drastically reduces trade frequency while capturing major trends.
    Uses 4-week momentum to determine direction.
    """
    
    def __init__(self, lookback_hours: int = 168):  # 7 days = 168 hours
        self.lookback = lookback_hours
        self.name = "WEEKLY_MOMENTUM"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self.lookback + 10:
            return TradeSignal(
                signal=Signal.NEUTRAL, strategy=self.name, confidence=0.0,
                reason="Need more data", price=df['close'].iloc[-1] if len(df) > 0 else 0, indicators={}
            )
        
        prices = df['close']
        current = prices.iloc[-1]
        week_ago = prices.iloc[-self.lookback] if len(prices) > self.lookback else prices.iloc[0]
        two_weeks_ago = prices.iloc[-self.lookback*2] if len(prices) > self.lookback*2 else prices.iloc[0]
        
        # Weekly returns
        ret_1w = (current - week_ago) / week_ago
        ret_2w = (current - two_weeks_ago) / two_weeks_ago
        
        indicators = {"ret_1w": ret_1w, "ret_2w": ret_2w, "price": current}
        
        # Strong upward momentum over 2 weeks
        if ret_2w > 0.05 and ret_1w > 0:  # 5%+ over 2 weeks, still positive last week
            return TradeSignal(
                signal=Signal.LONG, strategy=self.name, confidence=0.8,
                reason=f"Weekly momentum bullish: 2w {ret_2w:.1%}, 1w {ret_1w:.1%}",
                price=current, indicators=indicators
            )
        
        # Strong downward momentum
        if ret_2w < -0.05 and ret_1w < 0:
            return TradeSignal(
                signal=Signal.SHORT, strategy=self.name, confidence=0.8,
                reason=f"Weekly momentum bearish: 2w {ret_2w:.1%}, 1w {ret_1w:.1%}",
                price=current, indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL, strategy=self.name, confidence=0.3,
            reason="No clear weekly momentum", price=current, indicators=indicators
        )


class ExtremesOnlyStrategy:
    """
    Only trade at extreme RSI levels with trend confirmation
    
    Long when RSI < 20 AND price above 50-day SMA (oversold in uptrend)
    Short when RSI > 80 AND price below 50-day SMA (overbought in downtrend)
    """
    
    def __init__(self, rsi_extreme_low: float = 20, rsi_extreme_high: float = 80):
        self.rsi_low = rsi_extreme_low
        self.rsi_high = rsi_extreme_high
        self.name = "EXTREMES_ONLY"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 60:
            return TradeSignal(
                signal=Signal.NEUTRAL, strategy=self.name, confidence=0.0,
                reason="Need 60 candles", price=df['close'].iloc[-1] if len(df) > 0 else 0, indicators={}
            )
        
        prices = df['close']
        current = prices.iloc[-1]
        rsi = calculate_rsi(prices, 14).iloc[-1]
        sma50 = calculate_sma(prices, 50).iloc[-1]
        
        indicators = {"rsi": rsi, "sma50": sma50, "price": current}
        
        # Extreme oversold + in uptrend context
        if rsi < self.rsi_low:
            confidence = 0.85 if current > sma50 else 0.7
            return TradeSignal(
                signal=Signal.LONG, strategy=self.name, confidence=confidence,
                reason=f"EXTREME oversold RSI {rsi:.0f}",
                price=current, indicators=indicators
            )
        
        # Extreme overbought + in downtrend context
        if rsi > self.rsi_high:
            confidence = 0.85 if current < sma50 else 0.7
            return TradeSignal(
                signal=Signal.SHORT, strategy=self.name, confidence=confidence,
                reason=f"EXTREME overbought RSI {rsi:.0f}",
                price=current, indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL, strategy=self.name, confidence=0.3,
            reason=f"RSI {rsi:.0f} not extreme", price=current, indicators=indicators
        )


class BigMoveBreakoutStrategy:
    """
    Only trade on BIG moves - ATR breakouts > 3 standard deviations
    
    Waits for massive volatility expansion then follows the direction.
    Very few trades but catches major moves.
    """
    
    def __init__(self, atr_mult: float = 3.0):
        self.atr_mult = atr_mult
        self.name = f"BIG_MOVE_BREAKOUT_{atr_mult}X"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 50:
            return TradeSignal(
                signal=Signal.NEUTRAL, strategy=self.name, confidence=0.0,
                reason="Need 50 candles", price=df['close'].iloc[-1] if len(df) > 0 else 0, indicators={}
            )
        
        prices = df['close']
        current = prices.iloc[-1]
        prev = prices.iloc[-2]
        
        atr = calculate_atr(df, 14)
        atr_current = atr.iloc[-1]
        atr_mean = atr.iloc[-50:].mean()
        atr_std = atr.iloc[-50:].std()
        
        # Current move size
        move = abs(current - prev)
        threshold = atr_mean + (self.atr_mult * atr_std)
        
        indicators = {"atr": atr_current, "atr_threshold": threshold, "move": move, "price": current}
        
        # BIG move up
        if current > prev and move > threshold:
            return TradeSignal(
                signal=Signal.LONG, strategy=self.name, confidence=0.85,
                reason=f"BIG move UP: {move:.2f} > {threshold:.2f} threshold",
                price=current, indicators=indicators
            )
        
        # BIG move down
        if current < prev and move > threshold:
            return TradeSignal(
                signal=Signal.SHORT, strategy=self.name, confidence=0.85,
                reason=f"BIG move DOWN: {move:.2f} > {threshold:.2f} threshold",
                price=current, indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL, strategy=self.name, confidence=0.3,
            reason="No big move detected", price=current, indicators=indicators
        )


class TrendFollowLongOnlyStrategy:
    """
    Simple trend-following - LONG only when above 200 SMA
    
    Classic "above 200 SMA = bull market" approach.
    Reduces losses in bear markets by going to cash.
    """
    
    def __init__(self, sma_period: int = 200):
        self.sma_period = sma_period
        self.name = f"TREND_FOLLOW_{sma_period}SMA"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self.sma_period + 10:
            return TradeSignal(
                signal=Signal.NEUTRAL, strategy=self.name, confidence=0.0,
                reason=f"Need {self.sma_period + 10} candles", 
                price=df['close'].iloc[-1] if len(df) > 0 else 0, indicators={}
            )
        
        prices = df['close']
        current = prices.iloc[-1]
        sma = calculate_sma(prices, self.sma_period).iloc[-1]
        
        # Distance from SMA
        distance_pct = (current - sma) / sma * 100
        
        indicators = {"sma": sma, "distance_pct": distance_pct, "price": current}
        
        if current > sma:
            confidence = 0.6 + min(distance_pct / 20, 0.3)
            return TradeSignal(
                signal=Signal.LONG, strategy=self.name, confidence=confidence,
                reason=f"Price {distance_pct:+.1f}% above {self.sma_period} SMA - BULL",
                price=current, indicators=indicators
            )
        else:
            return TradeSignal(
                signal=Signal.SHORT, strategy=self.name, confidence=0.7,
                reason=f"Price {distance_pct:+.1f}% below {self.sma_period} SMA - BEAR",
                price=current, indicators=indicators
            )


class MonthlyRebalanceStrategy:
    """
    Monthly rebalance based on monthly momentum
    
    Ultra-low frequency: ~12 trades/year maximum.
    Uses 1-month and 3-month momentum for decision.
    """
    
    def __init__(self):
        self.name = "MONTHLY_REBALANCE"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 720:  # ~30 days of hourly data
            return TradeSignal(
                signal=Signal.NEUTRAL, strategy=self.name, confidence=0.0,
                reason="Need 30 days of data", price=df['close'].iloc[-1] if len(df) > 0 else 0, indicators={}
            )
        
        prices = df['close']
        current = prices.iloc[-1]
        
        # Monthly momentum (720 hours = 30 days)
        month_ago = prices.iloc[-720] if len(prices) > 720 else prices.iloc[0]
        three_months = prices.iloc[-2160] if len(prices) > 2160 else prices.iloc[0]
        
        ret_1m = (current - month_ago) / month_ago
        ret_3m = (current - three_months) / three_months
        
        indicators = {"ret_1m": ret_1m, "ret_3m": ret_3m, "price": current}
        
        # Strong positive momentum both timeframes
        if ret_1m > 0.03 and ret_3m > 0.05:
            return TradeSignal(
                signal=Signal.LONG, strategy=self.name, confidence=0.8,
                reason=f"Monthly bullish: 1m {ret_1m:.1%}, 3m {ret_3m:.1%}",
                price=current, indicators=indicators
            )
        
        # Strong negative momentum both timeframes
        if ret_1m < -0.03 and ret_3m < -0.05:
            return TradeSignal(
                signal=Signal.SHORT, strategy=self.name, confidence=0.8,
                reason=f"Monthly bearish: 1m {ret_1m:.1%}, 3m {ret_3m:.1%}",
                price=current, indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL, strategy=self.name, confidence=0.3,
            reason="Monthly momentum mixed", price=current, indicators=indicators
        )


# Registry
LOWFREQ_STRATEGIES = {
    "weekly_momentum": WeeklyMomentumStrategy(),
    "extremes_only": ExtremesOnlyStrategy(),
    "extremes_25_75": ExtremesOnlyStrategy(rsi_extreme_low=25, rsi_extreme_high=75),
    "big_move": BigMoveBreakoutStrategy(),
    "big_move_2x": BigMoveBreakoutStrategy(atr_mult=2.0),
    "big_move_4x": BigMoveBreakoutStrategy(atr_mult=4.0),
    "trend_follow_200": TrendFollowLongOnlyStrategy(200),
    "trend_follow_100": TrendFollowLongOnlyStrategy(100),
    "monthly_rebalance": MonthlyRebalanceStrategy(),
}


def get_lowfreq_strategy(name: str):
    return LOWFREQ_STRATEGIES.get(name.lower())
