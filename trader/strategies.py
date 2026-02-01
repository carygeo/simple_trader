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


class BreakoutStrategy:
    """
    30-Day Channel Breakout Strategy (Donchian Channel)
    
    This is the recommended strategy from optimization analysis:
    - Buy when price breaks above 30-day high
    - Sell when price breaks below 30-day low
    - Low frequency = minimal fee impact
    - Works best at 2-3x leverage
    
    Expected returns (ETH, 1 year):
    - 1x leverage: +55%
    - 2x leverage: +104%
    - 3x leverage: +133%
    """
    
    def __init__(self, lookback: int = 30):
        self.lookback = lookback
        self.name = f"BREAKOUT_{lookback}D"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        """Alias for generate_signal for compatibility"""
        return self.generate_signal(df)
    
    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        """Generate trading signal based on channel breakout"""
        if len(df) < self.lookback + 2:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Not enough data (need {self.lookback + 2} candles)",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        # Calculate channels (exclude current candle)
        high_channel = prices.iloc[:-1].rolling(window=self.lookback).max().iloc[-1]
        low_channel = prices.iloc[:-1].rolling(window=self.lookback).min().iloc[-1]
        
        # Mid-point for reference
        mid_channel = (high_channel + low_channel) / 2
        
        indicators = {
            "high_channel": high_channel,
            "low_channel": low_channel,
            "mid_channel": mid_channel,
            "current_price": current_price,
            "lookback": self.lookback
        }
        
        # Breakout signals
        if current_price > high_channel:
            # Bullish breakout
            confidence = min(0.6 + (current_price - high_channel) / high_channel * 10, 0.9)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Breakout above {self.lookback}-day high ({high_channel:.2f})",
                price=current_price,
                indicators=indicators
            )
        elif current_price < low_channel:
            # Bearish breakdown
            confidence = min(0.6 + (low_channel - current_price) / low_channel * 10, 0.9)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Breakdown below {self.lookback}-day low ({low_channel:.2f})",
                price=current_price,
                indicators=indicators
            )
        else:
            # Within channel
            position_in_channel = (current_price - low_channel) / (high_channel - low_channel)
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.3,
                reason=f"Within channel (position: {position_in_channel:.1%})",
                price=current_price,
                indicators=indicators
            )


def calculate_ichimoku(df: pd.DataFrame, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> dict:
    """
    Calculate Ichimoku Cloud components
    
    Args:
        df: DataFrame with OHLC data
        tenkan: Tenkan-sen period (default 9)
        kijun: Kijun-sen period (default 26)
        senkou_b: Senkou Span B period (default 52)
    
    Returns:
        dict with all Ichimoku components
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    tenkan_high = high.rolling(window=tenkan).max()
    tenkan_low = low.rolling(window=tenkan).min()
    tenkan_sen = (tenkan_high + tenkan_low) / 2
    
    # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    kijun_high = high.rolling(window=kijun).max()
    kijun_low = low.rolling(window=kijun).min()
    kijun_sen = (kijun_high + kijun_low) / 2
    
    # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2, shifted 26 periods ahead
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
    
    # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted 26 periods ahead
    senkou_b_high = high.rolling(window=senkou_b).max()
    senkou_b_low = low.rolling(window=senkou_b).min()
    senkou_span_b = ((senkou_b_high + senkou_b_low) / 2).shift(kijun)
    
    # Chikou Span (Lagging Span): Close shifted 26 periods back
    chikou_span = close.shift(-kijun)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }


class IchimokuStrategy:
    """
    Ichimoku Cloud Strategy - CROSSOVER ONLY Mode
    
    Based on Cary's Poloniex strategy. Key improvements:
    - ONLY signals on actual TK crossovers (not continuous position)
    - SMA crossover confirmation required
    - Momentum filter prevents signals in weak trends
    - Cloud position as additional filter
    
    This dramatically reduces trade frequency (target: <20 trades/year)
    
    Signal Rules:
    - LONG: Fresh TK bullish cross + SMA bullish + momentum positive
    - SHORT: Fresh TK bearish cross + SMA bearish + momentum negative
    - All other conditions: NEUTRAL (hold current position)
    """
    
    def __init__(self, tenkan: int = 9, kijun: int = 26, senkou_b: int = 52,
                 sma_fast: int = 20, sma_slow: int = 50, 
                 momentum_period: int = 48, min_momentum: float = 0.3,
                 cross_only: bool = True):
        self.tenkan = tenkan
        self.kijun = kijun
        self.senkou_b = senkou_b
        self.sma_fast = sma_fast
        self.sma_slow = sma_slow
        self.momentum_period = momentum_period  # Periods to calculate momentum direction
        self.min_momentum = min_momentum  # Minimum momentum strength (0-1) to signal
        self.cross_only = cross_only  # Only signal on actual crosses
        self.name = f"ICHIMOKU_CROSS" if cross_only else f"ICHIMOKU_{tenkan}/{kijun}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        """Alias for generate_signal for compatibility"""
        return self.generate_signal(df)
    
    def generate_signal(self, df: pd.DataFrame) -> TradeSignal:
        """
        Generate trading signal - CROSSOVER ONLY mode
        
        Key improvement: Only signal on ACTUAL TK crosses, not continuous position.
        This dramatically reduces trade frequency from 300+/year to ~10-20/year.
        """
        min_periods = max(self.senkou_b + self.kijun + 2, self.sma_slow + 2, self.momentum_period + 2)
        
        if len(df) < min_periods:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Not enough data (need {min_periods} candles)",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        ichimoku = calculate_ichimoku(df, self.tenkan, self.kijun, self.senkou_b)
        prices = df['close']
        
        current_price = prices.iloc[-1]
        tenkan_current = ichimoku['tenkan_sen'].iloc[-1]
        kijun_current = ichimoku['kijun_sen'].iloc[-1]
        span_a_current = ichimoku['senkou_span_a'].iloc[-1]
        span_b_current = ichimoku['senkou_span_b'].iloc[-1]
        
        # Previous values for crossover detection
        tenkan_prev = ichimoku['tenkan_sen'].iloc[-2]
        kijun_prev = ichimoku['kijun_sen'].iloc[-2]
        
        # SMA calculation for confirmation
        sma_fast = calculate_sma(prices, self.sma_fast)
        sma_slow = calculate_sma(prices, self.sma_slow)
        sma_fast_current = sma_fast.iloc[-1]
        sma_slow_current = sma_slow.iloc[-1]
        sma_bullish = sma_fast_current > sma_slow_current
        sma_bearish = sma_fast_current < sma_slow_current
        
        # Momentum calculation (from Cary's Poloniex strategy)
        # Sum of direction over momentum_period: +1 if fast>slow, -1 if fast<slow
        momentum_sum = 0
        for i in range(-self.momentum_period, 0):
            if i < -len(sma_fast) or i < -len(sma_slow):
                continue
            if pd.notna(sma_fast.iloc[i]) and pd.notna(sma_slow.iloc[i]):
                if sma_fast.iloc[i] > sma_slow.iloc[i]:
                    momentum_sum += 1
                elif sma_fast.iloc[i] < sma_slow.iloc[i]:
                    momentum_sum -= 1
        # Normalize momentum to -1 to 1 range
        momentum_strength = momentum_sum / self.momentum_period if self.momentum_period > 0 else 0
        
        # Handle NaN values
        if pd.isna(tenkan_current) or pd.isna(kijun_current) or pd.isna(span_a_current) or pd.isna(span_b_current):
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason="Insufficient data for Ichimoku calculation",
                price=current_price,
                indicators={}
            )
        
        # Cloud boundaries
        cloud_top = max(span_a_current, span_b_current)
        cloud_bottom = min(span_a_current, span_b_current)
        cloud_bullish = span_a_current > span_b_current
        
        # Price position relative to cloud
        price_above_cloud = current_price > cloud_top
        price_below_cloud = current_price < cloud_bottom
        
        # TK Cross detection - THE KEY FILTER
        tk_bullish_cross = tenkan_current > kijun_current and tenkan_prev <= kijun_prev
        tk_bearish_cross = tenkan_current < kijun_current and tenkan_prev >= kijun_prev
        
        indicators = {
            "tenkan_sen": tenkan_current,
            "kijun_sen": kijun_current,
            "cloud_top": cloud_top,
            "cloud_bottom": cloud_bottom,
            "sma_fast": sma_fast_current,
            "sma_slow": sma_slow_current,
            "momentum_strength": momentum_strength,
            "tk_bullish_cross": tk_bullish_cross,
            "tk_bearish_cross": tk_bearish_cross,
            "current_price": current_price
        }
        
        # CROSSOVER-ONLY SIGNAL LOGIC
        # Only generate signals on actual TK crosses with confirmations
        
        # BULLISH CROSS: TK crosses up + SMA confirms + momentum positive + price above cloud
        if tk_bullish_cross:
            confirmations = []
            confidence = 0.5
            
            if sma_bullish:
                confirmations.append("SMA bullish")
                confidence += 0.15
            if momentum_strength >= self.min_momentum:
                confirmations.append(f"momentum +{momentum_strength:.1%}")
                confidence += 0.15
            if price_above_cloud:
                confirmations.append("price above cloud")
                confidence += 0.1
            if cloud_bullish:
                confirmations.append("cloud green")
                confidence += 0.05
            
            # Require at least SMA confirmation to signal
            if sma_bullish and momentum_strength >= self.min_momentum:
                return TradeSignal(
                    signal=Signal.LONG,
                    strategy=self.name,
                    confidence=min(confidence, 0.9),
                    reason=f"TK BULLISH CROSS + {', '.join(confirmations)}",
                    price=current_price,
                    indicators=indicators
                )
        
        # BEARISH CROSS: TK crosses down + SMA confirms + momentum negative + price below cloud  
        if tk_bearish_cross:
            confirmations = []
            confidence = 0.5
            
            if sma_bearish:
                confirmations.append("SMA bearish")
                confidence += 0.15
            if momentum_strength <= -self.min_momentum:
                confirmations.append(f"momentum {momentum_strength:.1%}")
                confidence += 0.15
            if price_below_cloud:
                confirmations.append("price below cloud")
                confidence += 0.1
            if not cloud_bullish:
                confirmations.append("cloud red")
                confidence += 0.05
            
            # Require at least SMA confirmation to signal
            if sma_bearish and momentum_strength <= -self.min_momentum:
                return TradeSignal(
                    signal=Signal.SHORT,
                    strategy=self.name,
                    confidence=min(confidence, 0.9),
                    reason=f"TK BEARISH CROSS + {', '.join(confirmations)}",
                    price=current_price,
                    indicators=indicators
                )
        
        # NO CROSS = NO SIGNAL (this is the key to reducing trades!)
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="No TK cross - holding position",
            price=current_price,
            indicators=indicators
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
        # Breakout strategies (recommended)
        "breakout": BreakoutStrategy(lookback=30),
        "breakout_20": BreakoutStrategy(lookback=20),
        "breakout_30": BreakoutStrategy(lookback=30),
        "breakout_50": BreakoutStrategy(lookback=50),
        # Ichimoku Cloud strategy
        "ichimoku": IchimokuStrategy(),
        "ichimoku_9_26_52": IchimokuStrategy(9, 26, 52),  # Classic settings
        "ichimoku_fast": IchimokuStrategy(7, 22, 44),     # Faster for crypto
    }
    
    # Try to get from base strategies first
    if name.lower() in strategies:
        return strategies[name.lower()]
    
    # Try advanced strategies
    try:
        from .advanced_strategies import get_advanced_strategy
        adv = get_advanced_strategy(name)
        if adv:
            return adv
    except ImportError:
        pass
    
    return SMAStrategy()  # Default fallback
