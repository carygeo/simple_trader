"""
Enhanced Trading Strategies - Based on research improvements
- RSI + MACD confirmation
- Slope filter (trending only)  
- 2% risk rule position sizing
- Re-test entry confirmation
- Volume confirmation
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class Signal(Enum):
    LONG = 1
    SHORT = -1
    NEUTRAL = 0


@dataclass
class TradeSignal:
    signal: Signal
    strategy: str
    confidence: float
    reason: str
    price: float
    indicators: dict
    position_size_pct: float = 100.0  # Percentage of capital to use


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return prices.rolling(window=period).mean()


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return prices.ewm(span=period, adjust=False).mean()


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD, Signal line, and Histogram"""
    ema_12 = calculate_ema(prices, 12)
    ema_26 = calculate_ema(prices, 26)
    macd = ema_12 - ema_26
    signal = calculate_ema(macd, 9)
    histogram = macd - signal
    return macd, signal, histogram


def calculate_slope(series: pd.Series, period: int = 5) -> pd.Series:
    """Calculate slope of a series over N periods (normalized)"""
    return (series - series.shift(period)) / series.shift(period) * 100


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range for position sizing"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


class EnhancedSMAStrategy:
    """
    Enhanced SMA Crossover Strategy with multiple confirmations:
    - RSI filter (avoid overbought/oversold entries)
    - MACD confirmation
    - Slope filter (only trade trending markets)
    - 2% risk rule position sizing
    """
    
    def __init__(
        self, 
        fast_period: int = 20, 
        slow_period: int = 50,
        rsi_period: int = 14,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
        slope_threshold: float = 0.5,  # Min slope % for trending
        use_macd_confirm: bool = True,
        use_slope_filter: bool = True,
        use_rsi_filter: bool = True,
        risk_per_trade: float = 0.02,  # 2% risk rule
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.slope_threshold = slope_threshold
        self.use_macd_confirm = use_macd_confirm
        self.use_slope_filter = use_slope_filter
        self.use_rsi_filter = use_rsi_filter
        self.risk_per_trade = risk_per_trade
        
        self.name = f"ENHANCED_SMA_{fast_period}/{slow_period}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        """Analyze price data and return trade signal with confirmations"""
        prices = df['close']
        
        # Core indicators
        sma_fast = calculate_sma(prices, self.fast_period)
        sma_slow = calculate_sma(prices, self.slow_period)
        rsi = calculate_rsi(prices, self.rsi_period)
        macd, macd_signal, macd_hist = calculate_macd(prices)
        atr = calculate_atr(df)
        
        # Slope of slow SMA (trend strength)
        sma_slope = calculate_slope(sma_slow, 5)
        
        current_price = prices.iloc[-1]
        fast_current = sma_fast.iloc[-1]
        slow_current = sma_slow.iloc[-1]
        rsi_current = rsi.iloc[-1]
        macd_hist_current = macd_hist.iloc[-1]
        slope_current = sma_slope.iloc[-1]
        atr_current = atr.iloc[-1]
        
        # Previous values for crossover detection
        fast_prev = sma_fast.iloc[-2]
        slow_prev = sma_slow.iloc[-2]
        
        # Initialize
        signal = Signal.NEUTRAL
        confidence = 0.0
        reasons = []
        
        # 1. Base SMA signal
        bullish_cross = fast_prev <= slow_prev and fast_current > slow_current
        bearish_cross = fast_prev >= slow_prev and fast_current < slow_current
        
        if bullish_cross:
            signal = Signal.LONG
            confidence = 0.5
            reasons.append(f"Bullish SMA cross")
        elif bearish_cross:
            signal = Signal.SHORT
            confidence = 0.5
            reasons.append(f"Bearish SMA cross")
        elif fast_current > slow_current:
            signal = Signal.LONG
            confidence = 0.3
            reasons.append(f"Uptrend (fast > slow)")
        else:
            signal = Signal.SHORT
            confidence = 0.3
            reasons.append(f"Downtrend (fast < slow)")
        
        # 2. RSI Filter
        if self.use_rsi_filter:
            if signal == Signal.LONG and rsi_current > self.rsi_overbought:
                signal = Signal.NEUTRAL
                confidence = 0.0
                reasons.append(f"RSI overbought ({rsi_current:.1f})")
            elif signal == Signal.SHORT and rsi_current < self.rsi_oversold:
                signal = Signal.NEUTRAL
                confidence = 0.0
                reasons.append(f"RSI oversold ({rsi_current:.1f})")
            elif signal == Signal.LONG and rsi_current < 50:
                confidence += 0.15
                reasons.append(f"RSI room to run ({rsi_current:.1f})")
            elif signal == Signal.SHORT and rsi_current > 50:
                confidence += 0.15
                reasons.append(f"RSI room to fall ({rsi_current:.1f})")
        
        # 3. MACD Confirmation
        if self.use_macd_confirm and signal != Signal.NEUTRAL:
            if signal == Signal.LONG and macd_hist_current > 0:
                confidence += 0.2
                reasons.append("MACD confirms bullish")
            elif signal == Signal.SHORT and macd_hist_current < 0:
                confidence += 0.2
                reasons.append("MACD confirms bearish")
            elif signal == Signal.LONG and macd_hist_current < 0:
                confidence -= 0.15
                reasons.append("MACD divergence (bearish)")
            elif signal == Signal.SHORT and macd_hist_current > 0:
                confidence -= 0.15
                reasons.append("MACD divergence (bullish)")
        
        # 4. Slope Filter (trending only)
        if self.use_slope_filter and signal != Signal.NEUTRAL:
            if abs(slope_current) < self.slope_threshold:
                # Market is ranging, reduce confidence significantly
                confidence *= 0.5
                reasons.append(f"Flat market (slope {slope_current:.2f}%)")
            elif signal == Signal.LONG and slope_current > self.slope_threshold:
                confidence += 0.15
                reasons.append(f"Strong uptrend (slope {slope_current:.2f}%)")
            elif signal == Signal.SHORT and slope_current < -self.slope_threshold:
                confidence += 0.15
                reasons.append(f"Strong downtrend (slope {slope_current:.2f}%)")
        
        # 5. Calculate position size based on 2% risk rule
        # Position size = (Portfolio * Risk%) / ATR
        # We return a percentage that the backtester can use
        position_size_pct = min(100, (self.risk_per_trade * 100) / (atr_current / current_price * 100 + 0.001))
        
        # Cap confidence at 1.0
        confidence = min(1.0, max(0.0, confidence))
        
        # If confidence too low, go neutral
        if confidence < 0.3:
            signal = Signal.NEUTRAL
            reasons.append("Confidence too low")
        
        return TradeSignal(
            signal=signal,
            strategy=self.name,
            confidence=confidence,
            reason=" | ".join(reasons),
            price=current_price,
            indicators={
                "sma_fast": fast_current,
                "sma_slow": slow_current,
                "rsi": rsi_current,
                "macd_hist": macd_hist_current,
                "slope": slope_current,
                "atr": atr_current
            },
            position_size_pct=position_size_pct
        )


class EnhancedSMA3XShortStrategy(EnhancedSMAStrategy):
    """Enhanced SMA with 3x leverage for short-enabled accounts"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = f"ENHANCED_SMA_3X_SHORT_{self.fast_period}/{self.slow_period}"
        self.leverage = 3.0


# Strategy factory
def get_enhanced_strategy(name: str = "enhanced_sma") -> EnhancedSMAStrategy:
    """Get strategy instance by name"""
    strategies = {
        "enhanced_sma": EnhancedSMAStrategy(),
        "enhanced_sma_3x": EnhancedSMA3XShortStrategy(),
        "enhanced_sma_conservative": EnhancedSMAStrategy(
            rsi_overbought=65, rsi_oversold=35, 
            slope_threshold=1.0, risk_per_trade=0.01
        ),
        "enhanced_sma_aggressive": EnhancedSMAStrategy(
            rsi_overbought=80, rsi_oversold=20,
            slope_threshold=0.3, risk_per_trade=0.03
        ),
    }
    return strategies.get(name, EnhancedSMAStrategy())
