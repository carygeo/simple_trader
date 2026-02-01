"""
Adaptive Strategies - From Strategy Inventory
Implements high-potential strategies from the 68-strategy list
Target: 500%+ annual returns with < 50 trades/year
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .strategies import Signal, TradeSignal, calculate_sma, calculate_ema, calculate_rsi
from .advanced_strategies import calculate_atr, calculate_adx, calculate_bollinger_bands


def calculate_roc(prices: pd.Series, period: int = 10) -> pd.Series:
    """Calculate Rate of Change (momentum)"""
    return (prices - prices.shift(period)) / prices.shift(period) * 100


def calculate_macd_histogram(prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD line, signal, and histogram"""
    ema_12 = calculate_ema(prices, 12)
    ema_26 = calculate_ema(prices, 26)
    macd_line = ema_12 - ema_26
    signal_line = calculate_ema(macd_line, 9)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic %K and %D"""
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    
    stoch_k = 100 * (df['close'] - low_min) / (high_max - low_min)
    stoch_d = stoch_k.rolling(window=d_period).mean()
    
    return stoch_k, stoch_d


def calculate_keltner_channels(df: pd.DataFrame, period: int = 20, multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Keltner Channels"""
    ema = calculate_ema(df['close'], period)
    atr = calculate_atr(df, period)
    
    upper = ema + (multiplier * atr)
    lower = ema - (multiplier * atr)
    
    return ema, upper, lower


def calculate_zscore(prices: pd.Series, period: int = 20) -> pd.Series:
    """Calculate Z-Score (standard deviations from mean)"""
    mean = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    return (prices - mean) / std


class AdaptiveMeanRevBollingerStrategy:
    """
    Bollinger Band Mean Reversion - Classic and effective
    
    Entry: Price touches lower band + RSI oversold
    Exit: Price reaches middle band or upper band
    
    Key insight: Combine multiple confirmation signals to filter false entries
    """
    
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0, 
                 rsi_period: int = 14, rsi_oversold: float = 30, rsi_overbought: float = 70):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.name = f"MEAN_REV_BOLLINGER"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.bb_period, self.rsi_period) + 5
        
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
        
        # Bollinger Bands
        middle, upper, lower = calculate_bollinger_bands(prices, self.bb_period, self.bb_std)
        bb_mid = middle.iloc[-1]
        bb_upper = upper.iloc[-1]
        bb_lower = lower.iloc[-1]
        
        # RSI for confirmation
        rsi = calculate_rsi(prices, self.rsi_period)
        rsi_current = rsi.iloc[-1]
        
        # Position in band (0 = lower, 1 = upper)
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        
        indicators = {
            "bb_upper": bb_upper,
            "bb_middle": bb_mid,
            "bb_lower": bb_lower,
            "bb_position": bb_position,
            "rsi": rsi_current,
            "price": current_price
        }
        
        # LONG: Price at/below lower band + RSI oversold
        if current_price <= bb_lower and rsi_current <= self.rsi_oversold:
            confidence = 0.75 + min((self.rsi_oversold - rsi_current) / 30, 0.2)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Mean rev: Price at lower BB + RSI {rsi_current:.0f} oversold",
                price=current_price,
                indicators=indicators
            )
        
        # SHORT: Price at/above upper band + RSI overbought
        if current_price >= bb_upper and rsi_current >= self.rsi_overbought:
            confidence = 0.75 + min((rsi_current - self.rsi_overbought) / 30, 0.2)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Mean rev: Price at upper BB + RSI {rsi_current:.0f} overbought",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason=f"No mean reversion setup (BB pos: {bb_position:.1%}, RSI: {rsi_current:.0f})",
            price=current_price,
            indicators=indicators
        )


class AdaptiveMomentumDivergenceStrategy:
    """
    Momentum Divergence Strategy - Catch reversals early
    
    Bullish divergence: Price makes lower low, RSI makes higher low
    Bearish divergence: Price makes higher high, RSI makes lower high
    
    Very powerful for catching trend reversals!
    """
    
    def __init__(self, rsi_period: int = 14, lookback: int = 20, min_divergence: float = 5.0):
        self.rsi_period = rsi_period
        self.lookback = lookback
        self.min_divergence = min_divergence  # Min RSI difference for divergence
        self.name = f"MOMENTUM_DIVERGENCE"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.rsi_period, self.lookback) + 10
        
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
        
        rsi = calculate_rsi(prices, self.rsi_period)
        rsi_current = rsi.iloc[-1]
        
        # Look for price and RSI swings in lookback period
        price_window = prices.iloc[-self.lookback:]
        rsi_window = rsi.iloc[-self.lookback:]
        
        # Find local minima and maxima
        price_min_idx = price_window.idxmin()
        price_max_idx = price_window.idxmax()
        
        # Recent vs older values
        recent_price = prices.iloc[-5:].mean()
        older_price = prices.iloc[-self.lookback:-10].mean()
        recent_rsi = rsi.iloc[-5:].mean()
        older_rsi = rsi.iloc[-self.lookback:-10].mean()
        
        indicators = {
            "rsi": rsi_current,
            "recent_price": recent_price,
            "older_price": older_price,
            "recent_rsi": recent_rsi,
            "older_rsi": older_rsi,
            "price": current_price
        }
        
        # BULLISH DIVERGENCE: Price lower, RSI higher
        if recent_price < older_price and recent_rsi > older_rsi + self.min_divergence:
            divergence_strength = recent_rsi - older_rsi
            confidence = 0.6 + min(divergence_strength / 30, 0.3)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"BULLISH DIVERGENCE: Price down, RSI up by {divergence_strength:.1f}",
                price=current_price,
                indicators=indicators
            )
        
        # BEARISH DIVERGENCE: Price higher, RSI lower
        if recent_price > older_price and recent_rsi < older_rsi - self.min_divergence:
            divergence_strength = older_rsi - recent_rsi
            confidence = 0.6 + min(divergence_strength / 30, 0.3)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"BEARISH DIVERGENCE: Price up, RSI down by {divergence_strength:.1f}",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="No divergence detected",
            price=current_price,
            indicators=indicators
        )


class AdaptiveMomentumMACDStrategy:
    """
    MACD Momentum Strategy - Enhanced with histogram analysis
    
    Key insight: MACD histogram direction change often precedes price moves
    """
    
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal
        self.name = f"MOMENTUM_MACD_{fast}_{slow}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = self.slow + self.signal_period + 5
        
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
        
        macd_line, signal_line, histogram = calculate_macd_histogram(prices)
        
        macd_current = macd_line.iloc[-1]
        signal_current = signal_line.iloc[-1]
        hist_current = histogram.iloc[-1]
        hist_prev = histogram.iloc[-2]
        hist_prev2 = histogram.iloc[-3]
        
        indicators = {
            "macd": macd_current,
            "signal": signal_current,
            "histogram": hist_current,
            "hist_prev": hist_prev,
            "price": current_price
        }
        
        # Histogram turning positive (from negative)
        if hist_current > 0 and hist_prev <= 0:
            confidence = 0.8
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason="MACD histogram crossed positive",
                price=current_price,
                indicators=indicators
            )
        
        # Histogram increasing while positive (momentum accelerating)
        if hist_current > hist_prev > hist_prev2 and hist_current > 0:
            confidence = 0.7
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason="MACD histogram accelerating positive",
                price=current_price,
                indicators=indicators
            )
        
        # Histogram turning negative (from positive)
        if hist_current < 0 and hist_prev >= 0:
            confidence = 0.8
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason="MACD histogram crossed negative",
                price=current_price,
                indicators=indicators
            )
        
        # Histogram decreasing while negative (momentum accelerating down)
        if hist_current < hist_prev < hist_prev2 and hist_current < 0:
            confidence = 0.7
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason="MACD histogram accelerating negative",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="MACD momentum unclear",
            price=current_price,
            indicators=indicators
        )


class AdaptiveMeanRevZScoreStrategy:
    """
    Z-Score Mean Reversion - Statistical approach
    
    Buy when Z-Score < -2 (price is 2 std devs below mean)
    Sell when Z-Score > 2 (price is 2 std devs above mean)
    
    Very clean statistical framework with proven track record.
    """
    
    def __init__(self, period: int = 20, entry_z: float = 2.0, exit_z: float = 0.5):
        self.period = period
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.name = f"MEAN_REV_ZSCORE_{entry_z}"
    
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
        
        zscore = calculate_zscore(prices, self.period)
        z_current = zscore.iloc[-1]
        z_prev = zscore.iloc[-2]
        
        indicators = {
            "zscore": z_current,
            "entry_threshold": self.entry_z,
            "price": current_price
        }
        
        # LONG: Z-Score extremely negative (oversold)
        if z_current <= -self.entry_z:
            confidence = 0.65 + min(abs(z_current) / 4, 0.3)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Z-Score {z_current:.2f} extremely oversold",
                price=current_price,
                indicators=indicators
            )
        
        # SHORT: Z-Score extremely positive (overbought)
        if z_current >= self.entry_z:
            confidence = 0.65 + min(z_current / 4, 0.3)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Z-Score {z_current:.2f} extremely overbought",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason=f"Z-Score {z_current:.2f} within normal range",
            price=current_price,
            indicators=indicators
        )


class AdaptiveMeanRevKeltnerStrategy:
    """
    Keltner Channel Mean Reversion
    
    Similar to Bollinger but uses ATR for bands (better for volatile crypto)
    """
    
    def __init__(self, period: int = 20, multiplier: float = 2.0, rsi_period: int = 14):
        self.period = period
        self.multiplier = multiplier
        self.rsi_period = rsi_period
        self.name = f"MEAN_REV_KELTNER"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.period, self.rsi_period) + 5
        
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
        
        middle, upper, lower = calculate_keltner_channels(df, self.period, self.multiplier)
        k_mid = middle.iloc[-1]
        k_upper = upper.iloc[-1]
        k_lower = lower.iloc[-1]
        
        rsi = calculate_rsi(prices, self.rsi_period)
        rsi_current = rsi.iloc[-1]
        
        indicators = {
            "keltner_upper": k_upper,
            "keltner_middle": k_mid,
            "keltner_lower": k_lower,
            "rsi": rsi_current,
            "price": current_price
        }
        
        # LONG: Price at/below lower channel + RSI not overbought
        if current_price <= k_lower and rsi_current < 70:
            confidence = 0.7 + min((k_lower - current_price) / current_price * 10, 0.25)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Keltner: Price at lower channel, RSI {rsi_current:.0f}",
                price=current_price,
                indicators=indicators
            )
        
        # SHORT: Price at/above upper channel + RSI not oversold
        if current_price >= k_upper and rsi_current > 30:
            confidence = 0.7 + min((current_price - k_upper) / current_price * 10, 0.25)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Keltner: Price at upper channel, RSI {rsi_current:.0f}",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="Within Keltner channels",
            price=current_price,
            indicators=indicators
        )


class AdaptiveMomentumROCStrategy:
    """
    Rate of Change Momentum Strategy
    
    Simple but effective: trade the momentum of price change
    """
    
    def __init__(self, roc_period: int = 10, threshold: float = 5.0, sma_period: int = 20):
        self.roc_period = roc_period
        self.threshold = threshold  # % change threshold
        self.sma_period = sma_period
        self.name = f"MOMENTUM_ROC_{roc_period}"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = max(self.roc_period, self.sma_period) + 5
        
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
        
        roc = calculate_roc(prices, self.roc_period)
        roc_current = roc.iloc[-1]
        roc_prev = roc.iloc[-2]
        
        # SMA for trend filter
        sma = calculate_sma(prices, self.sma_period)
        sma_current = sma.iloc[-1]
        above_sma = current_price > sma_current
        
        indicators = {
            "roc": roc_current,
            "roc_threshold": self.threshold,
            "sma": sma_current,
            "above_sma": above_sma,
            "price": current_price
        }
        
        # LONG: Strong positive ROC + above SMA
        if roc_current > self.threshold and above_sma:
            confidence = 0.65 + min(roc_current / 20, 0.3)
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Strong momentum: ROC {roc_current:.1f}% + above SMA",
                price=current_price,
                indicators=indicators
            )
        
        # SHORT: Strong negative ROC + below SMA
        if roc_current < -self.threshold and not above_sma:
            confidence = 0.65 + min(abs(roc_current) / 20, 0.3)
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Strong negative momentum: ROC {roc_current:.1f}% + below SMA",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason=f"ROC {roc_current:.1f}% not strong enough",
            price=current_price,
            indicators=indicators
        )


class MultiTimeframeMACDRSIStrategy:
    """
    Multi-Timeframe MACD RSI Strategy (from inventory)
    
    Simulates multi-TF by using different period lengths
    Requires alignment across timeframes for entry
    """
    
    def __init__(self):
        self.name = "MULTI_TF_MACD_RSI"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        if len(df) < 100:
            return TradeSignal(
                signal=Signal.NEUTRAL,
                strategy=self.name,
                confidence=0.0,
                reason="Need 100 candles",
                price=df['close'].iloc[-1] if len(df) > 0 else 0,
                indicators={}
            )
        
        prices = df['close']
        current_price = prices.iloc[-1]
        
        # "Fast" timeframe (simulated with shorter periods)
        rsi_fast = calculate_rsi(prices, 7)
        macd_f, signal_f, hist_f = calculate_macd_histogram(prices)
        
        # "Slow" timeframe (simulated with longer periods)  
        rsi_slow = calculate_rsi(prices, 21)
        prices_4h = prices.iloc[::4]  # Simulate 4-hour data
        if len(prices_4h) > 30:
            macd_s, signal_s, hist_s = calculate_macd_histogram(prices_4h)
            hist_slow = hist_s.iloc[-1] if len(hist_s) > 0 else 0
        else:
            hist_slow = 0
        
        rsi_f = rsi_fast.iloc[-1]
        rsi_s = rsi_slow.iloc[-1]
        hist_fast = hist_f.iloc[-1]
        
        indicators = {
            "rsi_fast": rsi_f,
            "rsi_slow": rsi_s,
            "macd_hist_fast": hist_fast,
            "macd_hist_slow": hist_slow,
            "price": current_price
        }
        
        # BULLISH: Both timeframes agree
        if hist_fast > 0 and hist_slow > 0 and rsi_f > 50 and rsi_s > 50:
            confidence = 0.75
            if rsi_f > 60 and rsi_s > 55:
                confidence = 0.85
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"Multi-TF bullish: RSI fast {rsi_f:.0f}, slow {rsi_s:.0f}, MACD positive",
                price=current_price,
                indicators=indicators
            )
        
        # BEARISH: Both timeframes agree
        if hist_fast < 0 and hist_slow < 0 and rsi_f < 50 and rsi_s < 50:
            confidence = 0.75
            if rsi_f < 40 and rsi_s < 45:
                confidence = 0.85
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"Multi-TF bearish: RSI fast {rsi_f:.0f}, slow {rsi_s:.0f}, MACD negative",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason="Timeframes not aligned",
            price=current_price,
            indicators=indicators
        )


class StochasticRSIStrategy:
    """
    Stochastic RSI Strategy - Popular crypto indicator
    
    Combines RSI with Stochastic for double smoothing
    Very effective for timing entries in trending markets
    """
    
    def __init__(self, rsi_period: int = 14, stoch_period: int = 14, 
                 overbought: float = 80, oversold: float = 20):
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.overbought = overbought
        self.oversold = oversold
        self.name = f"STOCH_RSI"
    
    def analyze(self, df: pd.DataFrame) -> TradeSignal:
        min_periods = self.rsi_period + self.stoch_period + 5
        
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
        
        # Calculate RSI
        rsi = calculate_rsi(prices, self.rsi_period)
        
        # Calculate Stochastic of RSI
        rsi_min = rsi.rolling(window=self.stoch_period).min()
        rsi_max = rsi.rolling(window=self.stoch_period).max()
        stoch_rsi = 100 * (rsi - rsi_min) / (rsi_max - rsi_min)
        
        stoch_rsi_k = stoch_rsi.iloc[-1]
        stoch_rsi_d = stoch_rsi.rolling(window=3).mean().iloc[-1]
        stoch_rsi_prev = stoch_rsi.iloc[-2]
        
        indicators = {
            "stoch_rsi_k": stoch_rsi_k,
            "stoch_rsi_d": stoch_rsi_d,
            "rsi": rsi.iloc[-1],
            "price": current_price
        }
        
        # LONG: StochRSI crosses up from oversold
        if stoch_rsi_k > stoch_rsi_d and stoch_rsi_prev <= self.oversold and stoch_rsi_k > self.oversold:
            confidence = 0.75
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"StochRSI crossed up from oversold ({stoch_rsi_k:.0f})",
                price=current_price,
                indicators=indicators
            )
        
        # Already oversold and turning up
        if stoch_rsi_k <= self.oversold and stoch_rsi_k > stoch_rsi_prev:
            confidence = 0.65
            return TradeSignal(
                signal=Signal.LONG,
                strategy=self.name,
                confidence=confidence,
                reason=f"StochRSI oversold and turning up ({stoch_rsi_k:.0f})",
                price=current_price,
                indicators=indicators
            )
        
        # SHORT: StochRSI crosses down from overbought
        if stoch_rsi_k < stoch_rsi_d and stoch_rsi_prev >= self.overbought and stoch_rsi_k < self.overbought:
            confidence = 0.75
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"StochRSI crossed down from overbought ({stoch_rsi_k:.0f})",
                price=current_price,
                indicators=indicators
            )
        
        # Already overbought and turning down
        if stoch_rsi_k >= self.overbought and stoch_rsi_k < stoch_rsi_prev:
            confidence = 0.65
            return TradeSignal(
                signal=Signal.SHORT,
                strategy=self.name,
                confidence=confidence,
                reason=f"StochRSI overbought and turning down ({stoch_rsi_k:.0f})",
                price=current_price,
                indicators=indicators
            )
        
        return TradeSignal(
            signal=Signal.NEUTRAL,
            strategy=self.name,
            confidence=0.3,
            reason=f"StochRSI neutral ({stoch_rsi_k:.0f})",
            price=current_price,
            indicators=indicators
        )


# Registry of adaptive strategies
ADAPTIVE_STRATEGIES = {
    "mean_rev_bollinger": AdaptiveMeanRevBollingerStrategy(),
    "momentum_divergence": AdaptiveMomentumDivergenceStrategy(),
    "momentum_macd": AdaptiveMomentumMACDStrategy(),
    "mean_rev_zscore": AdaptiveMeanRevZScoreStrategy(),
    "mean_rev_zscore_1.5": AdaptiveMeanRevZScoreStrategy(entry_z=1.5),
    "mean_rev_zscore_2.5": AdaptiveMeanRevZScoreStrategy(entry_z=2.5),
    "mean_rev_keltner": AdaptiveMeanRevKeltnerStrategy(),
    "momentum_roc": AdaptiveMomentumROCStrategy(),
    "momentum_roc_3": AdaptiveMomentumROCStrategy(threshold=3.0),
    "multi_tf_macd_rsi": MultiTimeframeMACDRSIStrategy(),
    "stoch_rsi": StochasticRSIStrategy(),
}


def get_adaptive_strategy(name: str):
    """Get adaptive strategy by name"""
    return ADAPTIVE_STRATEGIES.get(name.lower())
