"""
Advanced Trading Strategies - High-Profit Low-Frequency
Target: 500%+ annual returns with < 50 trades/year
"""

import pandas as pd
import numpy as np
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from .strategies import Signal, TradeSignal, calculate_sma, calculate_ema, calculate_rsi


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range for volatility measurement"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def calculate_adx(df: pd.DataFrame, period: int = 14) -> tuple:
    """
    Calculate ADX (Average Directional Index) for trend strength
    Returns: (ADX, +DI, -DI)
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # Calculate +DM and -DM
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    # Calculate ATR
    atr = calculate_atr(df, period)
    
    # Calculate +DI and -DI
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    # Calculate DX and ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return adx, plus_di, minus_di


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> tuple:
    """Calculate Bollinger Bands: (middle, upper, lower)"""
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return middle, upper, lower


def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple:
    """
    Calculate SuperTrend indicator
    Returns: (supertrend, direction) where direction is 1 (bullish) or -1 (bearish)
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    atr = calculate_atr(df, period)
    
    hl2 = (high + low) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(period, len(df)):
        if close.iloc[i] > upper_band.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower_band.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1] if i > period else 1
        
        if direction.iloc[i] == 1:
            supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1] if i > period and not pd.isna(supertrend.iloc[i-1]) else lower_band.iloc[i])
        else:
            supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1] if i > period and not pd.isna(supertrend.iloc[i-1]) else upper_band.iloc[i])
    
    return supertrend, direction


class MomentumBreakoutStrategy:
    """
    Momentum Breakout Strategy - Catches strong directional moves
    
    Entry: Price breaks N-day high/low + RSI confirms momentum
    Exit: Opposite signal or trailing stop
    
    Target: 300%+ annual with ~30 trades/year
    """
    
    def __init__(self, breakout_period: int = 20, rsi_period: int = 14,
                 rsi_bull_threshold: float = 55, rsi_bear_threshold: float = 45):
        self.breakout_period = breakout_period
        self.rsi_period = rsi_period
        self.rsi_bull = rsi_bull_threshold
        self.rsi_bear = rsi_bear_threshold
        self.name = f"MOMENTUM_BREAKOUT_{breakout_period}D"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.breakout_period + 2, self.rsi_period + 2)
        
        if len(df) < min_periods:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Need {min_periods} candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        # Breakout levels (exclude current candle)
        high_level = prices.iloc[:-1].rolling(window=self.breakout_period).max().iloc[-1]
        low_level = prices.iloc[:-1].rolling(window=self.breakout_period).min().iloc[-1]
        
        # RSI for momentum confirmation
        rsi = calculate_rsi(prices, self.rsi_period)
        rsi_current = rsi.iloc[-1]
        
        # Previous RSI for crossover detection
        rsi_prev = rsi.iloc[-2] if len(rsi) > 1 else rsi_current
        
        indicators = {
            "high_level": high_level,
            "low_level": low_level,
            "rsi": rsi_current,
            "price": current_price
        }
        
        # BULLISH: Price breaks above high + RSI > threshold (momentum confirms)
        if current_price > high_level and rsi_current > self.rsi_bull:
            confidence = 0.7 + min((current_price - high_level) / high_level * 5, 0.2)
            if rsi_current > 60:  # Strong momentum
                confidence = min(confidence + 0.1, 0.95)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Breakout above {self.breakout_period}D high + RSI {rsi_current:.0f} confirms",
                price=current_price,
                indicators=indicators
            )
        
        # BEARISH: Price breaks below low + RSI < threshold
        if current_price < low_level and rsi_current < self.rsi_bear:
            confidence = 0.7 + min((low_level - current_price) / low_level * 5, 0.2)
            if rsi_current < 40:  # Strong momentum
                confidence = min(confidence + 0.1, 0.95)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Breakdown below {self.breakout_period}D low + RSI {rsi_current:.0f} confirms",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="No momentum breakout",
            price=current_price,
            indicators=indicators
        )


class SuperTrendStrategy:
    """
    SuperTrend Strategy - Popular trend-following indicator
    
    Very clean signals, works well with leverage in trending markets.
    Low trade frequency makes it fee-efficient.
    
    Target: 400%+ annual with ~40 trades/year
    """
    
    def __init__(self, period: int = 10, multiplier: float = 3.0):
        self.period = period
        self.multiplier = multiplier
        self.name = f"SUPERTREND_{period}_{multiplier}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self.period + 5:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Need {self.period + 5} candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        supertrend, direction = calculate_supertrend(df, self.period, self.multiplier)
        
        current_dir = direction.iloc[-1]
        prev_dir = direction.iloc[-2]
        st_value = supertrend.iloc[-1]
        
        indicators = {
            "supertrend": st_value,
            "direction": current_dir,
            "price": current_price
        }
        
        # Signal on direction change or continue with direction
        if current_dir == 1:
            confidence = 0.65
            if prev_dir == -1:  # Flip!
                confidence = 0.85
                reason = "SuperTrend FLIP to BULLISH"
            else:
                reason = "SuperTrend bullish"
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=reason,
                price=current_price,
                indicators=indicators
            )
        else:
            confidence = 0.65
            if prev_dir == 1:  # Flip!
                confidence = 0.85
                reason = "SuperTrend FLIP to BEARISH"
            else:
                reason = "SuperTrend bearish"
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=reason,
                price=current_price,
                indicators=indicators
            )


class ADXTrendStrategy:
    """
    ADX Trend Strategy - Only trades when trend is strong
    
    Key insight: Most losses come from trading in choppy markets.
    ADX > 25 = strong trend, ADX < 20 = no trade
    
    Combined with SMA for direction, this catches big moves only.
    
    Target: 350%+ annual with ~25 trades/year
    """
    
    def __init__(self, adx_period: int = 14, adx_threshold: float = 25,
                 sma_fast: int = 10, sma_slow: int = 30):
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.sma_fast = sma_fast
        self.sma_slow = sma_slow
        self.name = f"ADX_TREND_{adx_threshold}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.adx_period * 2, self.sma_slow) + 5
        
        if len(df) < min_periods:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Need {min_periods} candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        # Calculate ADX
        adx, plus_di, minus_di = calculate_adx(df, self.adx_period)
        adx_current = adx.iloc[-1]
        plus_di_current = plus_di.iloc[-1]
        minus_di_current = minus_di.iloc[-1]
        
        # Calculate SMAs for direction
        sma_fast = calculate_sma(prices, self.sma_fast)
        sma_slow = calculate_sma(prices, self.sma_slow)
        
        fast_current = sma_fast.iloc[-1]
        slow_current = sma_slow.iloc[-1]
        
        indicators = {
            "adx": adx_current,
            "plus_di": plus_di_current,
            "minus_di": minus_di_current,
            "sma_fast": fast_current,
            "sma_slow": slow_current,
            "price": current_price
        }
        
        # Only trade when ADX > threshold (strong trend)
        if pd.isna(adx_current) or adx_current < self.adx_threshold:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.3,
                reason=f"ADX {adx_current:.1f} < {self.adx_threshold} - weak trend, no trade",
                price=current_price,
                indicators=indicators
            )
        
        # Direction from SMA + DI
        if fast_current > slow_current and plus_di_current > minus_di_current:
            confidence = 0.6 + min((adx_current - self.adx_threshold) / 50, 0.3)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Strong uptrend: ADX {adx_current:.0f}, +DI > -DI, SMA bullish",
                price=current_price,
                indicators=indicators
            )
        elif fast_current < slow_current and minus_di_current > plus_di_current:
            confidence = 0.6 + min((adx_current - self.adx_threshold) / 50, 0.3)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Strong downtrend: ADX {adx_current:.0f}, -DI > +DI, SMA bearish",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="Mixed signals despite strong ADX",
            price=current_price,
            indicators=indicators
        )


class VolatilityBreakoutStrategy:
    """
    Volatility Breakout (Turtle Trading inspired)
    
    Buy when price moves > 2 ATR above 20-day average
    Sell when price moves > 2 ATR below 20-day average
    
    The key is using ATR for dynamic thresholds based on volatility.
    Works exceptionally well in trending crypto markets.
    
    Target: 500%+ annual with ~35 trades/year
    """
    
    def __init__(self, lookback: int = 20, atr_period: int = 14, atr_multiplier: float = 2.0):
        self.lookback = lookback
        self.atr_period = atr_period
        self.atr_mult = atr_multiplier
        self.name = f"VOLATILITY_BREAKOUT_{atr_multiplier}ATR"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.lookback, self.atr_period) + 5
        
        if len(df) < min_periods:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Need {min_periods} candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        # Calculate average price and ATR
        avg_price = prices.rolling(window=self.lookback).mean().iloc[-1]
        atr = calculate_atr(df, self.atr_period).iloc[-1]
        
        # Breakout thresholds
        upper_threshold = avg_price + (atr * self.atr_mult)
        lower_threshold = avg_price - (atr * self.atr_mult)
        
        indicators = {
            "avg_price": avg_price,
            "atr": atr,
            "upper_threshold": upper_threshold,
            "lower_threshold": lower_threshold,
            "price": current_price
        }
        
        # Check for breakouts
        if current_price > upper_threshold:
            distance = (current_price - upper_threshold) / atr
            confidence = 0.7 + min(distance * 0.1, 0.25)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Volatility breakout UP: {self.atr_mult}ATR above average",
                price=current_price,
                indicators=indicators
            )
        elif current_price < lower_threshold:
            distance = (lower_threshold - current_price) / atr
            confidence = 0.7 + min(distance * 0.1, 0.25)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Volatility breakdown DOWN: {self.atr_mult}ATR below average",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="Within volatility range",
            price=current_price,
            indicators=indicators
        )


class TripleSMAStrategy:
    """
    Triple SMA Strategy - Better trend confirmation
    
    Uses 3 SMAs (fast/medium/slow) for stronger trend signals.
    Only trades when all 3 align (reduces false signals).
    
    Target: 350%+ annual with ~30 trades/year
    """
    
    def __init__(self, fast: int = 10, medium: int = 20, slow: int = 50):
        self.fast = fast
        self.medium = medium
        self.slow = slow
        self.name = f"TRIPLE_SMA_{fast}_{medium}_{slow}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self.slow + 5:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Need {self.slow + 5} candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        sma_fast = calculate_sma(prices, self.fast).iloc[-1]
        sma_medium = calculate_sma(prices, self.medium).iloc[-1]
        sma_slow = calculate_sma(prices, self.slow).iloc[-1]
        
        # Previous values for crossover detection
        sma_fast_prev = calculate_sma(prices, self.fast).iloc[-2]
        sma_medium_prev = calculate_sma(prices, self.medium).iloc[-2]
        
        indicators = {
            "sma_fast": sma_fast,
            "sma_medium": sma_medium,
            "sma_slow": sma_slow,
            "price": current_price
        }
        
        # All 3 aligned bullish: fast > medium > slow
        if sma_fast > sma_medium > sma_slow:
            confidence = 0.7
            # Extra confidence on crossovers
            if sma_fast_prev <= sma_medium_prev:
                confidence = 0.85
                reason = "Triple SMA: Fast crossed above Medium (all bullish aligned)"
            else:
                reason = "Triple SMA: Strong uptrend (fast > medium > slow)"
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=reason,
                price=current_price,
                indicators=indicators
            )
        
        # All 3 aligned bearish: fast < medium < slow
        elif sma_fast < sma_medium < sma_slow:
            confidence = 0.7
            if sma_fast_prev >= sma_medium_prev:
                confidence = 0.85
                reason = "Triple SMA: Fast crossed below Medium (all bearish aligned)"
            else:
                reason = "Triple SMA: Strong downtrend (fast < medium < slow)"
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=reason,
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="SMAs not aligned - no clear trend",
            price=current_price,
            indicators=indicators
        )


class RSIMomentumStrategy:
    """
    RSI Momentum Strategy - Trade strong momentum moves
    
    Not mean reversion! Uses RSI to confirm momentum.
    RSI > 60 = strong bullish momentum, buy
    RSI < 40 = strong bearish momentum, sell
    
    Combined with price above/below SMA for direction confirmation.
    
    Target: 400%+ annual with ~40 trades/year
    """
    
    def __init__(self, rsi_period: int = 14, sma_period: int = 20,
                 bull_threshold: float = 60, bear_threshold: float = 40):
        self.rsi_period = rsi_period
        self.sma_period = sma_period
        self.bull_threshold = bull_threshold
        self.bear_threshold = bear_threshold
        self.name = f"RSI_MOMENTUM_{bull_threshold}_{bear_threshold}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.rsi_period, self.sma_period) + 5
        
        if len(df) < min_periods:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Need {min_periods} candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        rsi = calculate_rsi(prices, self.rsi_period).iloc[-1]
        sma = calculate_sma(prices, self.sma_period).iloc[-1]
        
        price_above_sma = current_price > sma
        price_below_sma = current_price < sma
        
        indicators = {
            "rsi": rsi,
            "sma": sma,
            "price": current_price
        }
        
        # Strong bullish momentum: RSI > bull_threshold + price above SMA
        if rsi > self.bull_threshold and price_above_sma:
            confidence = 0.6 + min((rsi - self.bull_threshold) / 40, 0.3)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Bullish momentum: RSI {rsi:.0f} > {self.bull_threshold}, price above SMA",
                price=current_price,
                indicators=indicators
            )
        
        # Strong bearish momentum: RSI < bear_threshold + price below SMA
        elif rsi < self.bear_threshold and price_below_sma:
            confidence = 0.6 + min((self.bear_threshold - rsi) / 40, 0.3)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Bearish momentum: RSI {rsi:.0f} < {self.bear_threshold}, price below SMA",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason=f"RSI {rsi:.0f} in neutral zone or conflicting with trend",
            price=current_price,
            indicators=indicators
        )


# Strategy registry for easy access
ADVANCED_STRATEGIES = {
    "momentum_breakout": MomentumBreakoutStrategy(),
    "momentum_breakout_10": MomentumBreakoutStrategy(breakout_period=10),
    "momentum_breakout_30": MomentumBreakoutStrategy(breakout_period=30),
    "supertrend": SuperTrendStrategy(),
    "supertrend_fast": SuperTrendStrategy(period=7, multiplier=2.5),
    "supertrend_slow": SuperTrendStrategy(period=14, multiplier=3.5),
    "adx_trend": ADXTrendStrategy(),
    "adx_trend_20": ADXTrendStrategy(adx_threshold=20),
    "adx_trend_30": ADXTrendStrategy(adx_threshold=30),
    "volatility_breakout": VolatilityBreakoutStrategy(),
    "volatility_breakout_1.5": VolatilityBreakoutStrategy(atr_multiplier=1.5),
    "volatility_breakout_2.5": VolatilityBreakoutStrategy(atr_multiplier=2.5),
    "triple_sma": TripleSMAStrategy(),
    "triple_sma_fast": TripleSMAStrategy(fast=5, medium=10, slow=30),
    "triple_sma_slow": TripleSMAStrategy(fast=20, medium=50, slow=100),
    "rsi_momentum": RSIMomentumStrategy(),
    "rsi_momentum_55_45": RSIMomentumStrategy(bull_threshold=55, bear_threshold=45),
    "rsi_momentum_65_35": RSIMomentumStrategy(bull_threshold=65, bear_threshold=35),
}


def get_advanced_strategy(name: str):
    """Get advanced strategy by name"""
    return ADVANCED_STRATEGIES.get(name.lower())
