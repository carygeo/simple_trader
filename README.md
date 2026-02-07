# Simple Trader

Automated cryptocurrency trading bot with backtested strategies for Coinbase (long-only) and Kraken (leveraged/short).

## 🏆 Best Performing Strategy

**SMA 20/50 Crossover with Daily Candles**

| Asset | Return (1yr) | Trades | Leverage |
|-------|--------------|--------|----------|
| LTC | **+231%** | 3 | 3x |
| LINK | **+221%** | 5 | 3x |
| ETH | +44% | 5 | 3x |

See: [CROSSOVER_STRATEGIES.md](CROSSOVER_STRATEGIES.md)

---

## 📁 Project Structure

```
simple_trader/
├── trader/
│   ├── strategies.py           # Original SMA/MACD/Breakout strategies
│   ├── crossover_strategies.py # ✅ WINNING crossover-only strategies
│   ├── enhanced_strategies.py  # Experimental (didn't work)
│   ├── backtest.py             # Backtesting engine
│   ├── coinbase.py             # Coinbase API client
│   ├── kraken.py               # Kraken API client
│   └── kraken_strategy.py      # Kraken trading bot
│
├── backtest_results/
│   ├── long_only/              # Coinbase-compatible results
│   ├── leveraged/              # Kraken-compatible results
│   ├── enhanced/               # Failed v1 experiments
│   └── improved_v2/            # Failed v2 experiments
│
├── docs/
│   ├── ORIGINAL_STRATEGIES.md  # Original strategy documentation
│   └── ENHANCED_STRATEGIES.md  # What we learned from failures
│
├── CROSSOVER_STRATEGIES.md     # ✅ WINNING strategy documentation
├── STRATEGY_OPTIMIZATION_PLAN.md # Optimization roadmap
└── README.md                   # This file
```

---

## 🎯 Strategy Overview

### What Works ✅

| Strategy | File | Best For |
|----------|------|----------|
| SMA 20/50 Crossover | `crossover_strategies.py` | 1-year swing trading |
| SMA 50/200 Trend | `crossover_strategies.py` | Long-term (2+ years) |

### What Doesn't Work ❌

| Strategy | Issue |
|----------|-------|
| Continuous SMA | Too many trades (800+/year) |
| Enhanced v1 | Added complexity, worse results |
| Enhanced v2 | Still wrong base signals |

---

## 🔑 Key Insights

### 1. Daily Candles > Hourly
- Hourly: 8,729 candles → 832 trades → -100%
- Daily: 366 candles → 3 trades → +231%

### 2. Crossover-Only > Continuous
- Continuous signals: Trade every candle in trend
- Crossover-only: Trade ONLY on actual SMA crosses

### 3. Simple > Complex
The winning strategy is just:
```python
if sma_20 crosses above sma_50: LONG
if sma_20 crosses below sma_50: SHORT
else: HOLD
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd simple_trader
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
cp .env.example .env
# Edit .env with your Coinbase/Kraken API keys
```

### 3. Run Backtest
```python
from trader.backtest import Backtester
from trader.crossover_strategies import SMA2050CrossoverStrategy

bt = Backtester(symbol='LTC-USD', initial_capital=100, mode='leveraged', leverage=3.0)
bt.fetch_data(days=365, interval='1d')  # Daily candles!

strategy = SMA2050CrossoverStrategy()
# Run manual backtest with crossover logic
```

### 4. Live Trading (Kraken)
```python
from trader.kraken_strategy import KrakenLeveragedTrader

trader = KrakenLeveragedTrader(
    pairs=['LTC-USD'],
    leverage=3,
    dry_run=True  # Set False for real trades
)
trader.run()
```

---

## 📊 Exchanges

### Coinbase (Long Only)
- Spot trading only
- No leverage, no shorting
- Use `mode='long_only'` in backtests

### Kraken (Leveraged + Short)
- Margin trading enabled
- Up to 5x leverage
- Can profit from both directions
- Use `mode='leveraged'` in backtests

---

## 📈 Mission Control Integration

Results sync to: https://mission-control-board.fly.dev/trade

```bash
python sync_to_mission_control.py
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [CROSSOVER_STRATEGIES.md](CROSSOVER_STRATEGIES.md) | ✅ Winning strategies |
| [docs/ORIGINAL_STRATEGIES.md](docs/ORIGINAL_STRATEGIES.md) | Original implementations |
| [docs/ENHANCED_STRATEGIES.md](docs/ENHANCED_STRATEGIES.md) | Failed experiments & lessons |
| [STRATEGY_OPTIMIZATION_PLAN.md](STRATEGY_OPTIMIZATION_PLAN.md) | Optimization roadmap |

---

## ⚠️ Risk Warning

- Cryptocurrency trading involves significant risk
- Past performance does not guarantee future results
- Max drawdowns of 50-70% are possible
- Only trade with capital you can afford to lose
- This is experimental software - use at your own risk

---

## 📝 Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-07 | 2.0 | Added crossover-only strategies (+231% LTC) |
| 2026-02-01 | 1.0 | Initial release with SMA/MACD/Breakout |

---

*Built by Abel for Cary's trading experiments*
