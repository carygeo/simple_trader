# Enhanced Strategies (Experimental)

## Overview

These strategies attempted to improve the original SMA strategy by adding filters and confirmation signals. 

⚠️ **Result: FAILED** - Both versions performed worse than the original.

The key lesson: **Simpler is often better.** Adding complexity created more signals, not fewer.

---

## Enhanced Strategy v1

**File:** `trader/enhanced_strategies.py`  
**Class:** `EnhancedSMAStrategy`

### Enhancements Added
1. RSI confirmation filter
2. MACD confirmation
3. Slope filter (trending only)
4. 2% risk rule position sizing

### Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| fast_period | 20 | Fast SMA |
| slow_period | 50 | Slow SMA |
| rsi_period | 14 | RSI calculation period |
| rsi_overbought | 70 | Block longs above |
| rsi_oversold | 30 | Block shorts below |
| slope_threshold | 0.5 | Min slope % for trending |
| use_macd_confirm | True | Require MACD agreement |
| use_slope_filter | True | Skip flat markets |
| risk_per_trade | 0.02 | 2% risk rule |

### What Went Wrong

**Expected:** Fewer, higher-quality signals  
**Actual:** More signals, worse entries

| Asset | Original | Enhanced v1 | Change |
|-------|----------|-------------|--------|
| LTC | +211% | -97% | -308% |
| ETH | +146% | -49% | -195% |
| LINK | +124% | -96% | -220% |

### Why It Failed
The filters were **additive**, not restrictive:
- Each filter could generate its own signal adjustments
- Confidence scoring created more entry points
- Result: 427 trades instead of 9

---

## Enhanced Strategy v2

**File:** `run_enhanced_backtests_v2.py`

### Additional Improvements Attempted
Based on research, we added:

1. **Signal Confirmation** (2 bars)
   - Wait for signal to persist 2 candles
   
2. **Cooldown Period** (10 bars)
   - Minimum bars between trades
   
3. **Higher Confidence Threshold** (0.65)
   - Only take high-probability setups
   
4. **ATR Volatility Filter**
   - Skip if ATR > 1.5x average
   
5. **Pullback Entries**
   - Wait for 2% pullback before entering
   
6. **Volume Confirmation**
   - Skip if volume < 80% average

### Results

| Asset | Original | v1 | v2 | Trades |
|-------|----------|-----|-----|--------|
| LTC | +211% | -97% | -101% | 12 |
| ETH | +146% | -49% | -99% | 19 |
| LINK | +124% | -96% | -100% | 28 |

### Progress Made
- Trades reduced from 427 → 12-28 ✓
- Still losing money ✗

### Why It Still Failed
The **base signal generation** was still wrong:
- Using hourly candles (too noisy)
- Strategy was fundamentally generating bad signals
- Filters couldn't fix bad underlying logic

---

## Key Lessons Learned

### 1. Data Granularity Matters
| Candle Type | Data Points | Trades | Result |
|-------------|-------------|--------|--------|
| Hourly | 8,729 | 800+ | -100% |
| Daily | 366 | 3-5 | +231% |

**Lesson:** Use daily candles for swing trading strategies.

### 2. Crossover-Only Beats Continuous
| Signal Type | Description | Trades | Result |
|-------------|-------------|--------|--------|
| Continuous | LONG every candle when fast > slow | 800+ | -100% |
| Crossover | LONG only when fast crosses above slow | 3 | +231% |

**Lesson:** Only trade on actual crossovers, then HOLD.

### 3. Simple > Complex
Adding RSI, MACD, slope, volatility, and volume filters made things **worse**, not better.

The winning strategy is dead simple:
```
IF sma_20 crosses above sma_50: GO LONG
IF sma_20 crosses below sma_50: GO SHORT
OTHERWISE: HOLD
```

### 4. The Research Wasn't Wrong
The improvements from research (confirmation, cooldown, pullback) are valid concepts. But they need to be applied to a **working base strategy**.

We were adding complexity to a broken foundation.

---

## When to Use Enhanced Strategies

### Don't Use For:
- ❌ Hourly data
- ❌ High-frequency trading
- ❌ Replacing a working simple strategy

### Consider For:
- ✅ Additional confirmation on daily crossovers
- ✅ Risk management layer on top of working strategy
- ✅ Reducing position size in volatile conditions

---

## File Locations

```
trader/enhanced_strategies.py    # v1 implementation
run_enhanced_backtests.py        # v1 backtest runner
run_enhanced_backtests_v2.py     # v2 backtest runner
backtest_results/enhanced/       # v1 results
backtest_results/improved_v2/    # v2 results
```

---

## Recommendation

**Use `CROSSOVER_STRATEGIES.md` instead.**

The crossover-only SMA 20/50 strategy with daily candles achieved:
- LTC: +231% (3 trades)
- LINK: +221% (5 trades)

Sometimes the simplest solution is the best one.
