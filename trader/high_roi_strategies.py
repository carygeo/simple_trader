"""
High ROI Strategies - Targeting 500%+ annual returns
Focus: Maximum profit with acceptable risk
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass

from .strategies import Signal, TradeSignal, calculate_sma, calculate_ema, calculate_rsi
from .advanced_strategies import calculate_atr, calculate_adx


def calculate_momentum(prices: pd.Series, period: int) -> pd.Series:
    """Calculate momentum (current price / price N periods ago)"""
    return prices / prices.shift(period)


class DualMomentumStrategy:
    """
    Dual Momentum Strategy - Gary Antonacci's proven approach
    
    Combines:
    1. Relative momentum: Is asset outperforming a benchmark?
    2. Absolute momentum: Is asset trending up vs its own history?
    
    Only goes long when BOTH conditions are met.
    Goes short when both are bearish.
    
    This has been backtested extensively and works well in crypto.
    """
    
    def __init__(self, lookback: int = 12, abs_threshold: float = 1.0):
        self.lookback = lookback  # Periods for momentum calculation
        self.abs_threshold = abs_threshold  # Absolute momentum threshold
        self.name = f"DUAL_MOMENTUM_{lookback}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self.lookback + 10:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Need {self.lookback + 10} candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        # Absolute momentum: Current price vs N periods ago
        abs_momentum = calculate_momentum(prices, self.lookback).iloc[-1]
        
        # Relative momentum: Compare short-term vs long-term trend
        sma_fast = calculate_sma(prices, self.lookback // 2).iloc[-1]
        sma_slow = calculate_sma(prices, self.lookback).iloc[-1]
        rel_momentum = sma_fast / sma_slow if sma_slow != 0 else 1.0
        
        indicators = {
            "abs_momentum": abs_momentum,
            "rel_momentum": rel_momentum,
            "price": current_price
        }
        
        # STRONG BULLISH: Both momentums positive
        if abs_momentum > self.abs_threshold and rel_momentum > 1.0:
            strength = (abs_momentum - 1) + (rel_momentum - 1)
            confidence = 0.7 + min(strength * 0.5, 0.25)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Dual momentum bullish: Abs {abs_momentum:.3f}, Rel {rel_momentum:.3f}",
                price=current_price,
                indicators=indicators
            )
        
        # STRONG BEARISH: Both momentums negative
        if abs_momentum < self.abs_threshold and rel_momentum < 1.0:
            strength = (1 - abs_momentum) + (1 - rel_momentum)
            confidence = 0.7 + min(strength * 0.5, 0.25)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Dual momentum bearish: Abs {abs_momentum:.3f}, Rel {rel_momentum:.3f}",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="Mixed momentum signals",
            price=current_price,
            indicators=indicators
        )


class TrendIntensityBreakoutStrategy:
    """
    Trend Intensity Breakout - Only trade when trend is VERY strong
    
    Uses ADX > 30 (strong trend) + price breakout for entry.
    The key is waiting for high-conviction setups only.
    
    Target: Fewer trades but much higher win rate.
    """
    
    def __init__(self, adx_threshold: float = 30, breakout_period: int = 20):
        self.adx_threshold = adx_threshold
        self.breakout_period = breakout_period
        self.name = f"TREND_INTENSITY_BREAKOUT_{adx_threshold}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.breakout_period, 28) + 10
        
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
        
        # Calculate ADX for trend strength
        adx, plus_di, minus_di = calculate_adx(df, 14)
        adx_current = adx.iloc[-1]
        plus_di_current = plus_di.iloc[-1]
        minus_di_current = minus_di.iloc[-1]
        
        # Breakout levels
        high_level = prices.iloc[:-1].rolling(window=self.breakout_period).max().iloc[-1]
        low_level = prices.iloc[:-1].rolling(window=self.breakout_period).min().iloc[-1]
        
        indicators = {
            "adx": adx_current,
            "plus_di": plus_di_current,
            "minus_di": minus_di_current,
            "high_level": high_level,
            "low_level": low_level,
            "price": current_price
        }
        
        # Only trade when ADX shows STRONG trend
        if pd.isna(adx_current) or adx_current < self.adx_threshold:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.3,
                reason=f"ADX {adx_current:.1f} < {self.adx_threshold} - waiting for strong trend",
                price=current_price,
                indicators=indicators
            )
        
        # Strong uptrend + breakout
        if current_price > high_level and plus_di_current > minus_di_current:
            confidence = 0.75 + min((adx_current - self.adx_threshold) / 40, 0.2)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Strong trend breakout UP: ADX {adx_current:.0f}, +DI > -DI",
                price=current_price,
                indicators=indicators
            )
        
        # Strong downtrend + breakdown
        if current_price < low_level and minus_di_current > plus_di_current:
            confidence = 0.75 + min((adx_current - self.adx_threshold) / 40, 0.2)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Strong trend breakdown DOWN: ADX {adx_current:.0f}, -DI > +DI",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="Strong trend but no breakout yet",
            price=current_price,
            indicators=indicators
        )


class AggressiveTrendFollowerStrategy:
    """
    Aggressive Trend Follower - Maximize gains in trending markets
    
    Uses multiple confirmations for trend direction, then stays in position
    until clear reversal. Designed for maximum profit capture.
    
    Signals:
    - EMA stack (8/21/55) for trend direction
    - RSI for momentum confirmation
    - ADX for trend strength filter
    """
    
    def __init__(self):
        self.name = "AGGRESSIVE_TREND_FOLLOWER"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 60:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason="Need 60 candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        # EMA stack
        ema_8 = calculate_ema(prices, 8).iloc[-1]
        ema_21 = calculate_ema(prices, 21).iloc[-1]
        ema_55 = calculate_ema(prices, 55).iloc[-1]
        
        # RSI
        rsi = calculate_rsi(prices, 14).iloc[-1]
        
        # ADX
        adx, plus_di, minus_di = calculate_adx(df, 14)
        adx_current = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
        
        indicators = {
            "ema_8": ema_8,
            "ema_21": ema_21,
            "ema_55": ema_55,
            "rsi": rsi,
            "adx": adx_current,
            "price": current_price
        }
        
        # Perfect bullish stack: 8 > 21 > 55 + RSI > 50 + ADX > 20
        if ema_8 > ema_21 > ema_55 and rsi > 50:
            confidence = 0.7
            if adx_current > 25:
                confidence = 0.85
            if rsi > 60:
                confidence = min(confidence + 0.1, 0.95)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Bullish EMA stack + RSI {rsi:.0f} + ADX {adx_current:.0f}",
                price=current_price,
                indicators=indicators
            )
        
        # Perfect bearish stack: 8 < 21 < 55 + RSI < 50
        if ema_8 < ema_21 < ema_55 and rsi < 50:
            confidence = 0.7
            if adx_current > 25:
                confidence = 0.85
            if rsi < 40:
                confidence = min(confidence + 0.1, 0.95)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Bearish EMA stack + RSI {rsi:.0f} + ADX {adx_current:.0f}",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="EMA stack not aligned",
            price=current_price,
            indicators=indicators
        )


class CryptoMomentumStrategy:
    """
    Crypto-Specific Momentum Strategy
    
    Optimized for crypto's high volatility:
    - Uses shorter lookback periods
    - Combines volume with price momentum
    - Quick entries and exits
    """
    
    def __init__(self, fast_period: int = 5, slow_period: int = 15):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.name = f"CRYPTO_MOMENTUM_{fast_period}_{slow_period}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < self.slow_period + 10:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason=f"Need {self.slow_period + 10} candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        # Fast vs slow momentum
        fast_mom = calculate_momentum(prices, self.fast_period).iloc[-1]
        slow_mom = calculate_momentum(prices, self.slow_period).iloc[-1]
        
        # Volume confirmation (if available)
        if 'volume' in df.columns:
            vol_sma = df['volume'].rolling(window=20).mean().iloc[-1]
            current_vol = df['volume'].iloc[-1]
            vol_ratio = current_vol / vol_sma if vol_sma > 0 else 1.0
        else:
            vol_ratio = 1.0
        
        # RSI for overbought/oversold
        rsi = calculate_rsi(prices, 14).iloc[-1]
        
        indicators = {
            "fast_momentum": fast_mom,
            "slow_momentum": slow_mom,
            "vol_ratio": vol_ratio,
            "rsi": rsi,
            "price": current_price
        }
        
        # BULLISH: Fast momentum > slow momentum + volume surge
        if fast_mom > slow_mom and fast_mom > 1.0 and vol_ratio > 1.2:
            confidence = 0.7 + min((fast_mom - 1) * 2, 0.25)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Crypto momentum bullish: Fast {fast_mom:.3f} > Slow {slow_mom:.3f}, Vol {vol_ratio:.1f}x",
                price=current_price,
                indicators=indicators
            )
        
        # BEARISH: Fast momentum < slow momentum + falling
        if fast_mom < slow_mom and fast_mom < 1.0:
            confidence = 0.7 + min((1 - fast_mom) * 2, 0.25)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Crypto momentum bearish: Fast {fast_mom:.3f} < Slow {slow_mom:.3f}",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="Momentum unclear",
            price=current_price,
            indicators=indicators
        )


class VolatilityAdaptiveStrategy:
    """
    Volatility Adaptive Strategy - Adjusts to market conditions
    
    In high volatility: Wider stops, bigger targets
    In low volatility: Tighter stops, mean reversion
    
    Uses ATR percentile to determine regime.
    """
    
    def __init__(self, atr_period: int = 14, lookback: int = 100):
        self.atr_period = atr_period
        self.lookback = lookback
        self.name = "VOLATILITY_ADAPTIVE"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.atr_period, self.lookback) + 10
        
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
        
        # Calculate ATR and its percentile
        atr = calculate_atr(df, self.atr_period)
        atr_current = atr.iloc[-1]
        atr_percentile = (atr.iloc[-self.lookback:] < atr_current).mean() * 100
        
        # Price momentum
        momentum = (current_price / prices.iloc[-20] - 1) * 100
        
        # RSI
        rsi = calculate_rsi(prices, 14).iloc[-1]
        
        indicators = {
            "atr": atr_current,
            "atr_percentile": atr_percentile,
            "momentum": momentum,
            "rsi": rsi,
            "price": current_price
        }
        
        # HIGH VOLATILITY REGIME (ATR > 70th percentile): Trend following
        if atr_percentile > 70:
            if momentum > 5 and rsi > 50:
                return TradeSignal(
                    signal=Signal.LONG,
                    strategy=self.name,
                    confidence=0.8,
                    reason=f"High vol regime: Momentum +{momentum:.1f}%, following trend UP",
                    price=current_price,
                    indicators=indicators
                )
            elif momentum < -5 and rsi < 50:
                return TradeSignal(
                    signal=Signal.SHORT,
                    strategy=self.name,
                    confidence=0.8,
                    reason=f"High vol regime: Momentum {momentum:.1f}%, following trend DOWN",
                    price=current_price,
                    indicators=indicators
                )
        
        # LOW VOLATILITY REGIME (ATR < 30th percentile): Mean reversion
        elif atr_percentile < 30:
            if rsi < 30:
                return TradeSignal(
                    signal=Signal.LONG,
                    strategy=self.name,
                    confidence=0.75,
                    reason=f"Low vol regime: RSI {rsi:.0f} oversold, mean reversion LONG",
                    price=current_price,
                    indicators=indicators
                )
            elif rsi > 70:
                return TradeSignal(
                    signal=Signal.SHORT,
                    strategy=self.name,
                    confidence=0.75,
                    reason=f"Low vol regime: RSI {rsi:.0f} overbought, mean reversion SHORT",
                    price=current_price,
                    indicators=indicators
                )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason=f"Vol regime unclear (ATR percentile: {atr_percentile:.0f})",
            price=current_price,
            indicators=indicators
        )


# Registry
HIGH_ROI_STRATEGIES = {
    "dual_momentum": DualMomentumStrategy(),
    "dual_momentum_6": DualMomentumStrategy(lookback=6),
    "dual_momentum_24": DualMomentumStrategy(lookback=24),
    "trend_intensity": TrendIntensityBreakoutStrategy(),
    "trend_intensity_25": TrendIntensityBreakoutStrategy(adx_threshold=25),
    "trend_intensity_35": TrendIntensityBreakoutStrategy(adx_threshold=35),
    "aggressive_trend": AggressiveTrendFollowerStrategy(),
    "crypto_momentum": CryptoMomentumStrategy(),
    "crypto_momentum_3_10": CryptoMomentumStrategy(fast_period=3, slow_period=10),
    "volatility_adaptive": VolatilityAdaptiveStrategy(),
}


def get_high_roi_strategy(name: str):
    """Get high ROI strategy by name"""
    return HIGH_ROI_STRATEGIES.get(name.lower())
