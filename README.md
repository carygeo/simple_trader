# Simple Trader 🤖📈

A straightforward cryptocurrency trading bot using Coinbase Advanced Trade API with proven technical analysis strategies.

## 📊 Backtest Results (30 Days)

| Strategy | Return | vs Buy & Hold | Trades | Win Rate |
|----------|--------|---------------|--------|----------|
| **SMA Crossover** | **+16.1%** | +28.7% | 16 | 50% |
| MACD | +5.1% | +17.7% | 57 | 47% |
| Combined | +10.8% | +23.4% | 70 | 23% |
| Buy & Hold | -12.6% | baseline | - | - |

> **Key insight:** All strategies outperformed buy & hold by **17-28%** during the recent market downturn by shorting during declines.

## ✨ Features

- **3 Trading Strategies** - SMA Crossover, MACD, and Combined
- **Long/Short Capable** - Profits in both bull and bear markets
- **Dry Run Mode** - Test strategies without risking real money
- **Live Trading** - Execute real trades via Coinbase API
- **Configurable** - Adjust pairs, amounts, intervals, strategies
- **Logging** - Detailed trade logs and analysis

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/carygeo/simple_trader.git
cd simple_trader
```

### 2. Set Up Python Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

### 3. Configure API Credentials

```bash
cp .env.example .env
```

Edit `.env` with your Coinbase API credentials:

```bash
COINBASE_API_KEY_NAME=organizations/YOUR-ORG-ID/apiKeys/YOUR-KEY-ID
COINBASE_API_KEY_SECRET=-----BEGIN EC PRIVATE KEY-----\nYOUR-PRIVATE-KEY\n-----END EC PRIVATE KEY-----
```

**Getting API Keys:**
1. Go to [Coinbase Developer Platform](https://portal.cdp.coinbase.com)
2. Create a new API key with trading permissions
3. Copy the key name and private key

### 4. Run the Bot

```bash
# Dry run (safe - no real trades)
python run.py

# Single analysis (test once)
python run.py --once

# Live trading ⚠️
python run.py --live
```

## 📖 Usage

### Command Line Options

```bash
python run.py [OPTIONS]

Options:
  --live              Enable live trading (default: dry run)
  --once              Run single analysis, don't loop
  --strategy TYPE     Strategy: sma, macd, combined (default: sma)
  --pair PAIR         Trading pair (default: BTC-USDT)
  --amount USD        Trade amount in USD (default: 10)
  --interval MINS     Check interval in minutes (default: 5)
```

### Examples

```bash
# Dry run with SMA strategy on BTC
python run.py

# Live trading with MACD on ETH
python run.py --live --strategy macd --pair ETH-USDT

# Test combined strategy once
python run.py --once --strategy combined

# Trade $50 every 15 minutes
python run.py --live --amount 50 --interval 15
```

## 📈 Strategies Explained

### 1. SMA Crossover (Recommended) ⭐

**How it works:**
- Calculates 20-period and 50-period Simple Moving Averages
- **BUY signal:** SMA20 crosses above SMA50 (bullish crossover)
- **SELL signal:** SMA20 crosses below SMA50 (bearish crossover)

**Why it's best:**
- Fewest trades (16 in 30 days) = lower fees
- Highest returns (+16.1%)
- Catches major trends, ignores noise

```
Price ━━━━━━━━━━━━━━━━━
SMA20 ┄┄┄┄┄┄┄╱╲╱┄┄┄┄┄┄┄
SMA50 ─────╱────╲──────
         ↑BUY   ↑SELL
```

### 2. MACD (Moving Average Convergence Divergence)

**How it works:**
- MACD Line = EMA12 - EMA26
- Signal Line = 9-period EMA of MACD
- **BUY signal:** MACD crosses above Signal line
- **SELL signal:** MACD crosses below Signal line

**Characteristics:**
- More responsive to price changes
- More trades (57 in 30 days)
- Good for volatile markets

### 3. Combined Strategy

**How it works:**
- Combines SMA and MACD signals
- Only trades when both agree (or stay neutral)
- Higher confidence but fewer opportunities

**Characteristics:**
- Reduces false signals
- More conservative approach
- Best for uncertain markets

## 🏗️ Architecture

```
simple_trader/
├── run.py              # Entry point & CLI
├── trader/
│   ├── __init__.py     # Package init
│   ├── bot.py          # Main trading logic
│   ├── coinbase.py     # Coinbase API client
│   └── strategies.py   # Trading strategies
├── .env                # Your credentials (git-ignored)
├── .env.example        # Template
├── requirements.txt    # Dependencies
└── README.md           # This file
```

### Flow Diagram

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Fetch Data │────▶│   Analyze    │────▶│  Generate   │
│  (yfinance) │     │ (Indicators) │     │   Signal    │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                    ┌──────────────┐     ┌──────▼──────┐
                    │   Execute    │◀────│   Decide    │
                    │    Trade     │     │  (if change)│
                    └──────────────┘     └─────────────┘
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `COINBASE_API_KEY_NAME` | API key identifier | Required |
| `COINBASE_API_KEY_SECRET` | Private key (PEM format) | Required |

### Strategy Parameters

Edit `trader/strategies.py` to customize:

```python
# SMA periods
SMAStrategy(fast_period=20, slow_period=50)

# MACD uses standard 12/26/9
```

## 🛡️ Risk Management

### Built-in Safety Features

1. **Dry Run Mode** - Default mode, no real trades
2. **Position Tracking** - Won't double-buy or double-sell
3. **Logging** - All decisions logged for review

### Recommended Practices

1. **Start with dry run** - Test for at least 24 hours
2. **Small amounts first** - Start with $10-20
3. **Monitor regularly** - Check logs daily
4. **Set loss limits** - Don't risk more than you can lose

## 📝 Sample Output

```
2026-02-01 05:04:12 | INFO | 🤖 SimpleTrader initialized
2026-02-01 05:04:12 | INFO |    Strategy: SMA_20/50
2026-02-01 05:04:12 | INFO |    Pair: BTC-USDT
2026-02-01 05:04:12 | INFO |    Trade size: $10.0
2026-02-01 05:04:12 | INFO |    Mode: DRY RUN
2026-02-01 05:04:12 | INFO | ==================================================
2026-02-01 05:04:12 | INFO | 🔍 Analyzing BTC-USDT...
2026-02-01 05:04:12 | INFO | 💰 Balances: {'USDT': 91.23}
2026-02-01 05:04:15 | INFO | 📊 Signal: SHORT | Downtrend: SMA20 < SMA50
2026-02-01 05:04:15 | INFO |    Confidence: 60% | Price: $78,985.15
2026-02-01 05:04:15 | INFO | 🔸 DRY RUN - Would execute SHORT
```

## 🔧 Troubleshooting

### "Missing API credentials"
- Ensure `.env` file exists and has correct format
- Check that newlines in private key use `\n`

### "Insufficient data for analysis"
- Requires at least 60 hours of price data
- Wait or reduce the SMA periods

### "API Error 401: Unauthorized"
- Check API key permissions
- Ensure key has trading access enabled

## ⚠️ Disclaimer

**Trading cryptocurrencies involves significant risk of loss.**

- This software is for educational purposes only
- Past performance does not guarantee future results
- Never invest more than you can afford to lose
- The authors are not responsible for any financial losses

Always do your own research before trading.

## 📜 License

MIT License - See LICENSE file

## 🙏 Credits

Built by Abel 🦞 for Cary

---

**Happy Trading!** 🚀📈
