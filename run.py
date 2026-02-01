#!/usr/bin/env python3
"""
Simple Trader - Entry Point

Usage:
    python run.py                    # Dry run (default)
    python run.py --live             # Live trading
    python run.py --once             # Single analysis
    python run.py --strategy macd    # Use MACD strategy
"""

import os
import argparse
from dotenv import load_dotenv

from trader.bot import SimpleTrader


def main():
    # Load environment variables
    load_dotenv()
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Simple Trader Bot")
    parser.add_argument("--live", action="store_true", help="Enable live trading (default: dry run)")
    parser.add_argument("--once", action="store_true", help="Run single analysis")
    parser.add_argument("--strategy", default="sma", choices=["sma", "macd", "combined"], help="Trading strategy")
    parser.add_argument("--pair", default="BTC-USDT", help="Trading pair")
    parser.add_argument("--amount", type=float, default=10.0, help="Trade amount in USD")
    parser.add_argument("--interval", type=int, default=5, help="Check interval in minutes")
    args = parser.parse_args()
    
    # Get credentials
    api_key_name = os.getenv("COINBASE_API_KEY_NAME")
    api_key_secret = os.getenv("COINBASE_API_KEY_SECRET")
    
    if not api_key_name or not api_key_secret:
        print("❌ Missing API credentials!")
        print("   Set COINBASE_API_KEY_NAME and COINBASE_API_KEY_SECRET in .env file")
        return 1
    
    # Fix newlines in key if needed
    api_key_secret = api_key_secret.replace("\\n", "\n")
    
    # Create trader
    trader = SimpleTrader(
        api_key_name=api_key_name,
        api_key_secret=api_key_secret,
        strategy_name=args.strategy,
        trading_pair=args.pair,
        trade_amount_usd=args.amount,
        dry_run=not args.live
    )
    
    # Run
    if args.once:
        trader.run_once()
    else:
        trader.run(interval_minutes=args.interval)
    
    return 0


if __name__ == "__main__":
    exit(main())
