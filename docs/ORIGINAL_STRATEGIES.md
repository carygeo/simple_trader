# Original Trading Strategies

## Overview

The original strategy implementations in `trader/strategies.py`. These use continuous signals (LONG/SHORT every candle while in trend) rather than crossover-only signals.

⚠️ **Note:** These strategies generate many trades on hourly data. For better performance, see `CROSSOVER_STRATEGIES.md`.

---

## Strategy 1: SMA Strategy

**Class:** `SMAStrategy`

### Description
Simple Moving Average crossover with optional RSI filter. Signals LONG when fast SMA > slow SMA, SHORT when fast SMA < slow SMA.

### Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| fast_period | 20 | Fast SMA period |
| slow_period | 50 | Slow SMA period |
| use_rsi_filter | True | Filter overbought/oversold |
| rsi_overbought | 70 | RSI threshold for overbought |
| rsi_oversold | 30 | RSI threshold for oversold |

### Signal Logic
```
IF fast_sma > slow_sma AND rsi < 70:
    SIGNAL = LONG
ELIF fast_sma < slow_sma AND rsi > 30:
    SIGNAL = SHORT
ELSE:
    SIGNAL = NEUTRAL (filtered by RSI)
```

### Performance (1yr, Hourly Data)
| Asset | Return | Trades |
|-------|--------|--------|
| LTC | -100% | 832 |
| ETH | -100% | 800+ |

**Issue:** Continuous signals on hourly data = too many trades

---

## Strategy 2: MACD Strategy

**Class:** `MACDStrategy`

### Description
Moving Average Convergence Divergence strategy with RSI filter.

### Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| use_rsi_filter | True | Filter overbought/oversold |
| rsi_overbought | 70 | RSI threshold |
| rsi_oversold | 30 | RSI threshold |

### MACD Calculation
- Fast EMA: 12 periods
- Slow EMA: 26 periods
- Signal Line: 9-period EMA of MACD

### Signal Logic
```
IF macd > signal_line AND rsi < 70:
    SIGNAL = LONG
ELIF macd < signal_line AND rsi > 30:
    SIGNAL = SHORT
```

### Performance (1yr)
Generally underperformed SMA strategies in backtests.

---

## Strategy 3: Breakout Strategy

**Class:** `BreakoutStrategy`

### Description
Channel breakout strategy. Goes LONG on new highs, SHORT on new lows.

### Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| lookback | 30 | Days for channel calculation |

### Signal Logic
```
IF price > highest_high(lookback):
    SIGNAL = LONG (breakout up)
ELIF price < lowest_low(lookback):
    SIGNAL = SHORT (breakout down)
ELSE:
    SIGNAL = NEUTRAL (in channel)
```

### Performance (1yr, Long Only)
| Asset | Return | Trades |
|-------|--------|--------|
| ETH | +57.5% | 6 |
| LTC | -36% | 8 |

**Best for:** Long-only mode on trending assets like ETH

---

## Strategy 4: Combined Strategy

**Class:** `CombinedStrategy`

### Description
Combines SMA and MACD signals for confirmation. Requires both to agree.

### Signal Logic
```
IF sma_signal == LONG AND macd_signal == LONG:
    SIGNAL = LONG
ELIF sma_signal == SHORT AND macd_signal == SHORT:
    SIGNAL = SHORT
ELSE:
    SIGNAL = NEUTRAL (no agreement)
```

### Performance
Generally fewer trades than individual strategies but mixed results.

---

## Strategy 5: Ichimoku Strategy

**Class:** `IchimokuStrategy`

### Description
Ichimoku Cloud strategy with Tenkan/Kijun crossovers.

### Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| tenkan | 9 | Tenkan-sen period |
| kijun | 26 | Kijun-sen period |
| senkou_b | 52 | Senkou Span B period |

### Signal Logic
Based on TK crossovers and cloud position.

---

## Lessons Learned

### Problem: Continuous Signals
These strategies signal LONG/SHORT **every candle** while in a trend, not just on crossovers.

With hourly data (8,729 candles/year):
- Signal changes frequently due to noise
- Results in 800+ trades per year
- Fees eat all profits

### Solution
Use **crossover-only** strategies (see `CROSSOVER_STRATEGIES.md`):
- Only trade on actual SMA crosses
- Hold position until next cross
- Reduces trades from 800+ to 3-5

---

## File Location

```
trader/strategies.py
```

## Usage

```python
from trader.strategies import SMAStrategy, MACDStrategy, BreakoutStrategy

# Create strategy
strategy = SMAStrategy(fast_period=20, slow_period=50)

# Analyze
signal = strategy.analyze(df)  # df with OHLC data

print(signal.signal)     # Signal.LONG, Signal.SHORT, or Signal.NEUTRAL
print(signal.confidence) # 0.0 to 1.0
print(signal.reason)     # Human-readable explanation
```
