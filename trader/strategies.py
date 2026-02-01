"""Trading Strategies - SMA Crossover, MACD, Combined with RSI Filter"""

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
    """SMA Crossover Strategy with RSI Filter"""
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50, 
                 use_rsi_filter: bool = True, rsi_overbought: float = 70, rsi_oversold: float = 30):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.use_rsi_filter = use_rsi_filter
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.name = f"SMA_{fast_period}/{slow_period}" + ("_RSI" if use_rsi_filter else "")
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        """Analyze price data and return trade signal"""
        prices = df['close']
        
        sma_fast = calculate_sma(prices, self.fast_period)
        sma_slow = calculate_sma(prices, self.slow_period)
        rsi = calculate_rsi(prices)
        
        current_price = prices.iloc[-1]
        fast_current = sma_fast.iloc[-1]
        slow_current = sma_slow.iloc[-1]
        rsi_current = rsi.iloc[-1]
        
        # Previous values for crossover detection
        fast_prev = sma_fast.iloc[-2]
        slow_prev = sma_slow.iloc[-2]
        
        # Determine base signal from SMA
        if fast_current > slow_current:
            if fast_prev <= slow_prev:
                base_signal = Signal.LONG
                reason = f"Bullish crossover: SMA{self.fast_period} crossed above SMA{self.slow_period}"
                confidence = 0.8
            else:
                base_signal = Signal.LONG
                reason = f"Uptrend: SMA{self.fast_period} > SMA{self.slow_period}"
                confidence = 0.6
        else:
            if fast_prev >= slow_prev:
                base_signal = Signal.SHORT
                reason = f"Bearish crossover: SMA{self.fast_period} crossed below SMA{self.slow_period}"
                confidence = 0.8
            else:
                base_signal = Signal.SHORT
                reason = f"Downtrend: SMA{self.fast_period} < SMA{self.slow_period}"
                confidence = 0.6
        
        # Apply RSI filter
        signal = base_signal
        if self.use_rsi_filter and not pd.isna(rsi_current):
            if base_signal == Signal.LONG and rsi_current > self.rsi_overbought:
                signal = Signal.NEUTRAL
                reason = f"RSI filter: Overbought ({rsi_current:.1f} > {self.rsi_overbought}) - blocking LONG"
                confidence = 0.3
            elif base_signal == Signal.SHORT and rsi_current < self.rsi_oversold:
                signal = Signal.NEUTRAL
                reason = f"RSI filter: Oversold ({rsi_current:.1f} < {self.rsi_oversold}) - blocking SHORT"
                confidence = 0.3
        
        return TradeSignal(
            signal=signal,
            strategy=self.name,
            confidence=confidence,
            reason=reason,
            price=current_price,
            indicators={
                f"sma_{self.fast_period}": fast_current,
                f"sma_{self.slow_period}": slow_current,
                "rsi": rsi_current,
                "trend": "bullish" if fast_current > slow_current else "bearish",
                "rsi_filtered": signal != base_signal
            }
        )


class MACDStrategy:
    """MACD Strategy with RSI Filter"""
    
    def __init__(self, use_rsi_filter: bool = True, rsi_overbought: float = 70, rsi_oversold: float = 30):
        self.use_rsi_filter = use_rsi_filter
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.name = "MACD" + ("_RSI" if use_rsi_filter else "")
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        """Analyze price data and return trade signal"""
        prices = df['close']
        
        macd, signal_line, histogram = calculate_macd(prices)
        rsi = calculate_rsi(prices)
        
        current_price = prices.iloc[-1]
        macd_current = macd.iloc[-1]
        signal_current = signal_line.iloc[-1]
        hist_current = histogram.iloc[-1]
        rsi_current = rsi.iloc[-1]
        
        # Previous values
        macd_prev = macd.iloc[-2]
        signal_prev = signal_line.iloc[-2]
        
        # Determine base signal from MACD
        if macd_current > signal_current:
            if macd_prev <= signal_prev:
                base_signal = Signal.LONG
                reason = "MACD bullish crossover"
                confidence = 0.75
            else:
                base_signal = Signal.LONG
                reason = "MACD above signal line"
                confidence = 0.55
        else:
            if macd_prev >= signal_prev:
                base_signal = Signal.SHORT
                reason = "MACD bearish crossover"
                confidence = 0.75
            else:
                base_signal = Signal.SHORT
                reason = "MACD below signal line"
                confidence = 0.55
        
        # Apply RSI filter
        signal = base_signal
        if self.use_rsi_filter and not pd.isna(rsi_current):
            if base_signal == Signal.LONG and rsi_current > self.rsi_overbought:
                signal = Signal.NEUTRAL
                reason = f"RSI filter: Overbought ({rsi_current:.1f} > {self.rsi_overbought}) - blocking LONG"
                confidence = 0.3
            elif base_signal == Signal.SHORT and rsi_current < self.rsi_oversold:
                signal = Signal.NEUTRAL
                reason = f"RSI filter: Oversold ({rsi_current:.1f} < {self.rsi_oversold}) - blocking SHORT"
                confidence = 0.3
        
        return TradeSignal(
            signal=signal,
            strategy=self.name,
            confidence=confidence,
            reason=reason,
            price=current_price,
            indicators={
                "macd": macd_current,
                "signal": signal_current,
                "histogram": hist_current,
                "rsi": rsi_current,
                "rsi_filtered": signal != base_signal
            }
        )


class CombinedStrategy:
    """Combined SMA + MACD Strategy with RSI Filter"""
    
    def __init__(self, use_rsi_filter: bool = True, rsi_overbought: float = 70, rsi_oversold: float = 30):
        self.use_rsi_filter = use_rsi_filter
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.sma = SMAStrategy(use_rsi_filter=False)  # We'll apply RSI at combined level
        self.macd = MACDStrategy(use_rsi_filter=False)
        self.name = "Combined_SMA_MACD" + ("_RSI" if use_rsi_filter else "")
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        """Analyze using both strategies with RSI filter"""
        prices = df['close']
        rsi = calculate_rsi(prices)
        rsi_current = rsi.iloc[-1]
        
        sma_signal = self.sma.analyze(df)
        macd_signal = self.macd.analyze(df)
        
        # Combine signals
        sma_val = sma_signal.signal.value
        macd_val = macd_signal.signal.value
        
        combined_val = sma_val + macd_val
        
        if combined_val > 0:
            base_signal = Signal.LONG
            confidence = (sma_signal.confidence + macd_signal.confidence) / 2
            if sma_val == macd_val == 1:
                confidence = min(confidence + 0.15, 0.95)
                reason = "Both SMA and MACD bullish"
            else:
                reason = "Net bullish (mixed signals)"
        elif combined_val < 0:
            base_signal = Signal.SHORT
            confidence = (sma_signal.confidence + macd_signal.confidence) / 2
            if sma_val == macd_val == -1:
                confidence = min(confidence + 0.15, 0.95)
                reason = "Both SMA and MACD bearish"
            else:
                reason = "Net bearish (mixed signals)"
        else:
            base_signal = Signal.NEUTRAL
            confidence = 0.3
            reason = "Conflicting signals - staying neutral"
        
        # Apply RSI filter
        signal = base_signal
        if self.use_rsi_filter and not pd.isna(rsi_current):
            if base_signal == Signal.LONG and rsi_current > self.rsi_overbought:
                signal = Signal.NEUTRAL
                reason = f"RSI filter: Overbought ({rsi_current:.1f} > {self.rsi_overbought}) - blocking LONG"
                confidence = 0.3
            elif base_signal == Signal.SHORT and rsi_current < self.rsi_oversold:
                signal = Signal.NEUTRAL
                reason = f"RSI filter: Oversold ({rsi_current:.1f} < {self.rsi_oversold}) - blocking SHORT"
                confidence = 0.3
        
        return TradeSignal(
            signal=signal,
            strategy=self.name,
            confidence=confidence,
            reason=reason,
            price=sma_signal.price,
            indicators={
                **sma_signal.indicators,
                **macd_signal.indicators,
                "rsi": rsi_current,
                "sma_signal": sma_signal.signal.name,
                "macd_signal": macd_signal.signal.name,
                "rsi_filtered": signal != base_signal
            }
        )


def get_strategy(name: str):
    """Get strategy by name"""
    strategies = {
        "sma": SMAStrategy(use_rsi_filter=True),
        "macd": MACDStrategy(use_rsi_filter=True),
        "combined": CombinedStrategy(use_rsi_filter=True),
        # Legacy versions without RSI filter
        "sma_no_rsi": SMAStrategy(use_rsi_filter=False),
        "macd_no_rsi": MACDStrategy(use_rsi_filter=False),
        "combined_no_rsi": CombinedStrategy(use_rsi_filter=False),
    }
    return strategies.get(name.lower(), SMAStrategy())
