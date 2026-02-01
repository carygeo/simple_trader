# Simple Trader 🤖

A straightforward cryptocurrency trading bot using Coinbase Advanced Trade API.

## Features

- **SMA Crossover Strategy** - Best performer (+16% vs -12% buy & hold)
- **MACD Strategy** - Momentum-based signals
- **Combined Strategy** - Uses both for confirmation
- **Long/Short capable** - Profits in both bull and bear markets
- **Dry run mode** - Test without real money

## Quick Start

```bash
# Clone
git clone https://github.com/carygeo/simple_trader.git
cd simple_trader

# Setup
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Coinbase API credentials

# Run (dry run mode)
python run.py

# Run live trading
python run.py --live
```

## Configuration

Edit `.env` file:

```bash
COINBASE_API_KEY_NAME=organizations/xxx/apiKeys/xxx
COINBASE_API_KEY_SECRET=-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----
```

## Usage

```bash
# Dry run with SMA strategy (default)
python run.py

# Live trading with MACD
python run.py --live --strategy macd

# Single analysis (no loop)
python run.py --once

# Custom settings
python run.py --strategy combined --pair ETH-USDT --amount 25 --interval 15
```

## Strategies

### SMA Crossover (Recommended)
- Uses 20/50 period Simple Moving Averages
- **Backtest result: +16.1%** (vs -12.6% buy & hold)
- Fewer trades (16), lower fees
- Best for trending markets

### MACD
- Uses 12/26 EMA with 9-period signal
- **Backtest result: +5.1%**
- More trades (57), catches momentum
- Good for volatile markets

### Combined
- Requires agreement from both SMA and MACD
- **Backtest result: +10.8%**
- Higher confidence signals
- Fewer false positives

## How It Works

1. Fetches hourly price data from Coinbase
2. Calculates technical indicators (SMA, MACD)
3. Generates BUY/SELL signals
4. Executes trades (or logs in dry run mode)
5. Repeats every N minutes

## Risk Warning

⚠️ **Trading cryptocurrencies involves significant risk.** This bot is for educational purposes. Always:
- Start with small amounts
- Use dry run mode first
- Never invest more than you can afford to lose
- Monitor the bot regularly

## License

MIT
