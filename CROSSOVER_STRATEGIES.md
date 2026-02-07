# Crossover-Only SMA Strategies

## Overview

These strategies use Simple Moving Average (SMA) crossovers to generate trading signals. The key insight is to **only trade on actual crossovers**, then **hold the position** until the next crossover occurs.

This approach dramatically reduces trade frequency and improves performance by avoiding whipsaw trades during sideways markets.

---

## Strategy 1: SMA 20/50 Crossover (Recommended)

**File:** `trader/crossover_strategies.py` → `SMA2050CrossoverStrategy`

### Description
A medium-term crossover strategy using 20-day and 50-day Simple Moving Averages. Optimized for 1-year timeframes with daily candles.

### Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| Fast SMA | 20 days | Short-term trend |
| Slow SMA | 50 days | Medium-term trend |
| Leverage | 3x | Kraken margin trading |
| Candles | Daily | Reduces noise vs hourly |

### Signal Rules
| Condition | Signal | Action |
|-----------|--------|--------|
| SMA20 crosses **above** SMA50 | LONG | Buy / Close Short |
| SMA20 crosses **below** SMA50 | SHORT | Sell / Close Long |
| No crossover | HOLD | Maintain position |

### Backtest Results (1 Year, 3x Leverage)

| Asset | Return | Trades | Max Drawdown |
|-------|--------|--------|--------------|
| **LTC** | **+231%** | 3 | ~58% |
| **LINK** | **+221%** | 5 | ~70% |
| ETH | +44% | 5 | ~40% |

### Why It Works
1. **Daily candles** filter out intraday noise
2. **Crossover-only signals** prevent overtrading
3. **20/50 periods** balance responsiveness vs stability
4. **3x leverage** amplifies gains on strong trends

### Usage
```python
from trader.crossover_strategies import SMA2050CrossoverStrategy

strategy = SMA2050CrossoverStrategy(leverage=3.0)
signal = strategy.analyze(df)  # df = DataFrame with OHLC data

if signal.signal == Signal.LONG:
    # Open long position
elif signal.signal == Signal.SHORT:
    # Open short position
```

---

## Strategy 2: SMA 50/200 Trend Following

**File:** `trader/crossover_strategies.py` → `SMA50200TrendStrategy`

### Description
A long-term trend following strategy using the classic "Golden Cross" and "Death Cross" signals. Uses 50-day and 200-day SMAs.

### Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| Fast SMA | 50 days | Medium-term trend |
| Slow SMA | 200 days | Long-term trend |
| Leverage | 3x | Kraken margin trading |
| Candles | Daily | Required for 200-day SMA |

### Signal Rules
| Condition | Signal | Name |
|-----------|--------|------|
| SMA50 crosses **above** SMA200 | LONG | **Golden Cross** |
| SMA50 crosses **below** SMA200 | SHORT | **Death Cross** |
| No crossover | HOLD | Maintain position |

### Data Requirements
⚠️ **Requires 2+ years of historical data** to generate meaningful signals.

With only 1 year of data, the 200-day SMA doesn't have enough history to produce crossovers.

### Expected Performance
- **Trades per year:** 1-3 (very low frequency)
- **Best for:** Long-term trend capture
- **Avoid:** Choppy/ranging markets

### Usage
```python
from trader.crossover_strategies import SMA50200TrendStrategy

strategy = SMA50200TrendStrategy(leverage=3.0)
signal = strategy.analyze(df)  # Need 200+ days of data

if signal.signal == Signal.LONG:
    print("Golden Cross - Go Long!")
elif signal.signal == Signal.SHORT:
    print("Death Cross - Go Short!")
```

---

## Key Insights from Development

### Problem: Original Strategy Had Too Many Trades
- Running SMA on **hourly candles** (8,729 data points) produced **832 trades**
- Result: **-100% return** (total loss due to fees and whipsaws)

### Solution: Two Key Fixes

1. **Use Daily Candles**
   - Reduces data points from 8,729 to 366
   - Filters out intraday noise
   - Cleaner signals

2. **Crossover-Only Signals**
   - Old: Signal LONG every candle when SMA20 > SMA50
   - New: Signal LONG only when SMA20 **crosses above** SMA50, then HOLD
   - Reduced trades from 832 to 3

### Results Comparison

| Approach | Candles | Trades | Return |
|----------|---------|--------|--------|
| Hourly + Continuous | 8,729 | 832 | -100% |
| Daily + Continuous | 366 | 30 | -4% |
| **Daily + Crossover** | **366** | **3** | **+231%** |

---

## Risk Management

### Position Sizing (2% Rule)
```
Position Size = (Account Balance × 0.02) / Stop Distance
```

With $71 account and 3x leverage:
- Max risk per trade: $1.42 (2%)
- Effective buying power: $213

### Recommended Stop Loss
- **Trend Following:** Below/above the slow SMA (50 or 200)
- **Tighter:** 5-10% from entry

### Max Drawdown Warning
These strategies can experience significant drawdowns:
- SMA 20/50: Up to 58% drawdown
- SMA 50/200: Up to 70% drawdown

**Only use capital you can afford to lose.**

---

## Quick Reference

### Best Use Cases
| Strategy | Timeframe | Best For | Data Needed |
|----------|-----------|----------|-------------|
| SMA 20/50 | 1 year | Active trading | 60+ days |
| SMA 50/200 | 2+ years | Long-term holding | 210+ days |

### Asset Recommendations
Based on backtest results:
1. **LTC** - Best performer (+231%)
2. **LINK** - Strong performer (+221%)
3. **ETH** - Moderate (+44%)

---

## Files

```
simple_trader/
├── trader/
│   └── crossover_strategies.py    # Strategy implementations
├── CROSSOVER_STRATEGIES.md        # This documentation
└── backtest_results/
    └── improved_v2/               # Latest backtest plots
```

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-07 | 1.0 | Initial release with SMA 20/50 and 50/200 strategies |

---

*Created by Abel for Cary's Kraken trading bot*
