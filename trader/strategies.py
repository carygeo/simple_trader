"""Trading Strategies - SMA Crossover, MACD, Combined"""

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


class SMAStrategy:
    """SMA Crossover Strategy - Best performer in backtest"""
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = f"SMA_{fast_period}/{slow_period}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        """Analyze price data and return trade signal"""
        prices = df['close']
        
        sma_fast = calculate_sma(prices, self.fast_period)
        sma_slow = calculate_sma(prices, self.slow_period)
        
        current_price = prices.iloc[-1]
        fast_current = sma_fast.iloc[-1]
        slow_current = sma_slow.iloc[-1]
        
        # Previous values for crossover detection
        fast_prev = sma_fast.iloc[-2]
        slow_prev = sma_slow.iloc[-2]
        
        # Determine signal
        if fast_current > slow_current:
            if fast_prev <= slow_prev:
                # Bullish crossover just happened
                signal = Signal.LONG
                reason = f"Bullish crossover: SMA{self.fast_period} crossed above SMA{self.slow_period}"
                confidence = 0.8
            else:
                # Already in uptrend
                signal = Signal.LONG
                reason = f"Uptrend: SMA{self.fast_period} > SMA{self.slow_period}"
                confidence = 0.6
        else:
            if fast_prev >= slow_prev:
                # Bearish crossover just happened
                signal = Signal.SHORT
                reason = f"Bearish crossover: SMA{self.fast_period} crossed below SMA{self.slow_period}"
                confidence = 0.8
            else:
                # Already in downtrend
                signal = Signal.SHORT
                reason = f"Downtrend: SMA{self.fast_period} < SMA{self.slow_period}"
                confidence = 0.6
        
        return TradeSignal(
            signal=signal,
            strategy=self.name,
            confidence=confidence,
            reason=reason,
            price=current_price,
            indicators={
                f"sma_{self.fast_period}": fast_current,
                f"sma_{self.slow_period}": slow_current,
                "trend": "bullish" if fast_current > slow_current else "bearish"
            }
        )


class MACDStrategy:
    """MACD Strategy"""
    
    def __init__(self):
        self.name = "MACD"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        """Analyze price data and return trade signal"""
        prices = df['close']
        
        macd, signal_line, histogram = calculate_macd(prices)
        
        current_price = prices.iloc[-1]
        macd_current = macd.iloc[-1]
        signal_current = signal_line.iloc[-1]
        hist_current = histogram.iloc[-1]
        
        # Previous values
        macd_prev = macd.iloc[-2]
        signal_prev = signal_line.iloc[-2]
        
        # Determine signal
        if macd_current > signal_current:
            if macd_prev <= signal_prev:
                signal = Signal.LONG
                reason = "MACD bullish crossover"
                confidence = 0.75
            else:
                signal = Signal.LONG
                reason = "MACD above signal line"
                confidence = 0.55
        else:
            if macd_prev >= signal_prev:
                signal = Signal.SHORT
                reason = "MACD bearish crossover"
                confidence = 0.75
            else:
                signal = Signal.SHORT
                reason = "MACD below signal line"
                confidence = 0.55
        
        return TradeSignal(
            signal=signal,
            strategy=self.name,
            confidence=confidence,
            reason=reason,
            price=current_price,
            indicators={
                "macd": macd_current,
                "signal": signal_current,
                "histogram": hist_current
            }
        )


class CombinedStrategy:
    """Combined SMA + MACD Strategy"""
    
    def __init__(self):
        self.sma = SMAStrategy()
        self.macd = MACDStrategy()
        self.name = "Combined_SMA_MACD"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        """Analyze using both strategies"""
        sma_signal = self.sma.analyze(df)
        macd_signal = self.macd.analyze(df)
        
        # Combine signals
        sma_val = sma_signal.signal.value
        macd_val = macd_signal.signal.value
        
        combined_val = sma_val + macd_val
        
        if combined_val > 0:
            signal = Signal.LONG
            confidence = (sma_signal.confidence + macd_signal.confidence) / 2
            if sma_val == macd_val == 1:
                confidence = min(confidence + 0.15, 0.95)
                reason = "Both SMA and MACD bullish"
            else:
                reason = "Net bullish (mixed signals)"
        elif combined_val < 0:
            signal = Signal.SHORT
            confidence = (sma_signal.confidence + macd_signal.confidence) / 2
            if sma_val == macd_val == -1:
                confidence = min(confidence + 0.15, 0.95)
                reason = "Both SMA and MACD bearish"
            else:
                reason = "Net bearish (mixed signals)"
        else:
            signal = Signal.NEUTRAL
            confidence = 0.3
            reason = "Conflicting signals - staying neutral"
        
        return TradeSignal(
            signal=signal,
            strategy=self.name,
            confidence=confidence,
            reason=reason,
            price=sma_signal.price,
            indicators={
                **sma_signal.indicators,
                **macd_signal.indicators,
                "sma_signal": sma_signal.signal.name,
                "macd_signal": macd_signal.signal.name
            }
        )


def get_strategy(name: str):
    """Get strategy by name"""
    strategies = {
        "sma": SMAStrategy(),
        "macd": MACDStrategy(),
        "combined": CombinedStrategy()
    }
    return strategies.get(name.lower(), SMAStrategy())
