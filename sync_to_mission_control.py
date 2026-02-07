#!/usr/bin/env python3
"""
Sync trader data to Mission Control

Usage:
    python sync_to_mission_control.py         # Sync once
    python sync_to_mission_control.py --loop  # Continuous sync every 60s
"""

import os
import json
import subprocess
import argparse
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

MISSION_CONTROL_URL = "https://mission-control-board.fly.dev/api/trade"
STATUS_SECRET = os.getenv("MISSION_CONTROL_SECRET", "abel-mission-2026")


def is_trader_running() -> bool:
    """Check if trader process is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python.*run.py"],
            capture_output=True, text=True
        )
        return bool(result.stdout.strip())
    except:
        return False


def get_balances() -> dict:
    """Get Coinbase balances"""
    try:
        from trader.coinbase import CoinbaseClient
        
        api_key = os.getenv("COINBASE_API_KEY_NAME")
        api_secret = os.getenv("COINBASE_API_KEY_SECRET", "").replace("\\n", "\n")
        
        if not api_key or not api_secret:
            return {}
        
        client = CoinbaseClient(api_key, api_secret)
        accounts = client.get_accounts()
        
        balances = {}
        for acc in accounts:
            currency = acc.get("currency", "")
            balance = float(acc.get("available_balance", {}).get("value", 0))
            if balance > 0.0001:
                balances[currency] = balance
        
        return balances
    except Exception as e:
        print(f"Error getting balances: {e}")
        return {}


def get_prices() -> dict:
    """Get current prices"""
    try:
        import yfinance as yf
        
        prices = {}
        for sym in ["BTC-USD", "ETH-USD", "XRP-USD", "DOGE-USD", "SOL-USD"]:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="1d")
            if not hist.empty:
                prices[sym.replace("-USD", "")] = float(hist['Close'].iloc[-1])
        
        return prices
    except:
        return {}


def load_backtest_results() -> dict:
    """Load backtest results for all timeframes and modes"""
    base_dir = os.path.dirname(__file__)
    backtest_dir = os.path.join(base_dir, "backtest_results")
    
    results = {}
    timeframes = ["1mo", "6mo", "1yr"]
    modes = ["long_only", "leveraged"]
    
    col_map = {
        'strategy_return_pct': 'return_pct',
        'hold_return_pct': 'hold_pct',
        'outperformance_pct': 'outperform',
        'total_trades': 'trades',
        'max_drawdown_pct': 'max_dd'
    }
    
    # Load by timeframe (legacy)
    for tf in timeframes:
        tf_dir = os.path.join(backtest_dir, tf)
        csv_path = os.path.join(tf_dir, f"backtest_summary_{tf}.csv")
        
        try:
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                df = df.rename(columns=col_map)
                df = df.sort_values('return_pct', ascending=False)
                results[tf] = df.to_dict('records')
            else:
                results[tf] = []
        except Exception as e:
            print(f"Warning: Could not load {tf} CSV: {e}")
            results[tf] = []
    
    # Load by mode (new structure)
    for mode in modes:
        for tf in timeframes:
            key = f"{mode}_{tf}"
            mode_dir = os.path.join(backtest_dir, mode, tf)
            csv_path = os.path.join(mode_dir, "summary.csv")
            
            try:
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    df = df.rename(columns=col_map)
                    df = df.sort_values('return_pct', ascending=False)
                    # Add mode to each record
                    records = df.to_dict('records')
                    for r in records:
                        r['mode'] = mode
                    results[key] = records
                else:
                    results[key] = []
            except Exception as e:
                print(f"Warning: Could not load {key} CSV: {e}")
                results[key] = []
    
    return results


def load_trade_history() -> list:
    """Load trade history"""
    history_path = os.path.join(os.path.dirname(__file__), "trade_history.json")
    try:
        if os.path.exists(history_path):
            with open(history_path) as f:
                return json.load(f)
    except:
        pass
    return []


def load_trader_state() -> dict:
    """Load trader state (legacy)"""
    state_path = os.path.join(os.path.dirname(__file__), "trader_state.json")
    try:
        if os.path.exists(state_path):
            with open(state_path) as f:
                return json.load(f)
    except:
        pass
    return {}


def load_bot_state(bot_name: str) -> dict:
    """Load state for a specific bot"""
    base_dir = os.path.dirname(__file__)
    state_path = os.path.join(base_dir, bot_name, "state.json")
    try:
        if os.path.exists(state_path):
            with open(state_path) as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {bot_name} state: {e}")
    return {}


def is_bot_running(bot_name: str) -> bool:
    """Check if a specific bot process is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"python.*{bot_name}/run.py"],
            capture_output=True, text=True
        )
        return bool(result.stdout.strip())
    except:
        return False


def sync_to_mission_control():
    """Sync all trader data to Mission Control"""
    print(f"📊 Syncing trader data to Mission Control...")
    
    # Gather all data
    running = is_trader_running()
    balances = get_balances()
    prices = get_prices()
    backtest_results = load_backtest_results()
    trades = load_trade_history()
    state = load_trader_state()
    
    # Calculate portfolio value
    portfolio_value = 0
    for currency, amount in balances.items():
        if currency in ["USD", "USDT", "USDC"]:
            portfolio_value += amount
        elif currency in prices:
            portfolio_value += amount * prices[currency]
    
    # Get Kraken balance
    kraken_balance = 0
    kraken_position = "NONE"
    try:
        from trader.kraken import KrakenClient
        kraken_client = KrakenClient()
        kraken_balances = kraken_client.get_balance()
        for currency, amount in kraken_balances.items():
            val = float(amount)
            if val > 0.01:
                if currency in ["USDT", "USD", "ZUSD"]:
                    kraken_balance += val
        # Load Kraken state if exists
        kraken_state_path = os.path.join(os.path.dirname(__file__), "kraken_state.json")
        if os.path.exists(kraken_state_path):
            with open(kraken_state_path) as f:
                kraken_state = json.load(f)
                kraken_position = kraken_state.get("position", "NONE")
    except Exception as e:
        print(f"Note: Kraken balance check: {e}")
    
    # Build payload with all timeframes
    payload = {
        "running": running,
        "portfolioValue": portfolio_value + kraken_balance,
        "position": state.get("position", "NONE"),
        "tradingPair": state.get("trading_pair", "BTC-USDT"),
        "entryPrice": state.get("entry_price", 0),
        "activeStrategy": state.get("strategy", "NONE"),
        "lastUpdated": state.get("updated_at", ""),
        "dryRun": state.get("dry_run", True),
        "balances": balances,
        "prices": prices,
        "strategies": backtest_results.get("1mo", [])[:10],
        "strategies_1mo": backtest_results.get("1mo", [])[:15],
        "strategies_6mo": backtest_results.get("6mo", [])[:15],
        "strategies_1yr": backtest_results.get("1yr", [])[:15],
        # Mode-specific strategies (top 10 each)
        "long_only_1yr": backtest_results.get("long_only_1yr", [])[:10],
        "long_only_6mo": backtest_results.get("long_only_6mo", [])[:10],
        "long_only_1mo": backtest_results.get("long_only_1mo", [])[:10],
        "leveraged_1yr": backtest_results.get("leveraged_1yr", [])[:10],
        "leveraged_6mo": backtest_results.get("leveraged_6mo", [])[:10],
        "leveraged_1mo": backtest_results.get("leveraged_1mo", [])[:10],
        "trades": trades[-20:],
        # Load individual bot states
        "coinbase_bot": load_bot_state("coinbase_bot"),
        "kraken_bot": load_bot_state("kraken_bot"),
        # Dual exchange data (formatted for dashboard)
        "bots": [
            {
                "name": "Long Only",
                "exchange": "coinbase",
                "running": is_bot_running("coinbase_bot"),
                "portfolioValue": portfolio_value,
                "position": load_bot_state("coinbase_bot").get("position", state.get("position", "NONE")),
                "tradingPair": load_bot_state("coinbase_bot").get("trading_pair", state.get("trading_pair", "DOGE-USDT")),
                "entryPrice": load_bot_state("coinbase_bot").get("entry_price", state.get("entry_price", 0)),
                "strategy": load_bot_state("coinbase_bot").get("strategy", state.get("strategy", "SMA_20/50")),
                "mode": "long_only",
                "leverage": 1,
                "balances": balances
            },
            {
                "name": "Leveraged Short",
                "exchange": "kraken",
                "running": is_bot_running("kraken_bot"),
                "portfolioValue": kraken_balance,
                "position": load_bot_state("kraken_bot").get("position", kraken_position),
                "tradingPair": load_bot_state("kraken_bot").get("trading_pair", "LTC-USD"),
                "entryPrice": load_bot_state("kraken_bot").get("entry_price", 0),
                "strategy": load_bot_state("kraken_bot").get("strategy", "SMA_3X_SHORT"),
                "mode": "leveraged",
                "leverage": load_bot_state("kraken_bot").get("leverage", 3),
                "unrealizedPnl": load_bot_state("kraken_bot").get("unrealized_pnl", 0),
                "balances": {"USDT": kraken_balance}
            }
        ],
        # Legacy fields for backward compatibility
        "coinbase": {
            "running": is_bot_running("coinbase_bot"),
            "portfolioValue": portfolio_value,
            "position": load_bot_state("coinbase_bot").get("position", state.get("position", "NONE")),
            "tradingPair": load_bot_state("coinbase_bot").get("trading_pair", state.get("trading_pair", "DOGE-USDT")),
            "entryPrice": load_bot_state("coinbase_bot").get("entry_price", state.get("entry_price", 0)),
            "strategy": load_bot_state("coinbase_bot").get("strategy", state.get("strategy", "SMA_20/50")),
            "balances": balances
        },
        "kraken": {
            "running": is_bot_running("kraken_bot"),
            "portfolioValue": kraken_balance,
            "position": load_bot_state("kraken_bot").get("position", kraken_position),
            "tradingPair": load_bot_state("kraken_bot").get("trading_pair", "LTC-USD"),
            "strategy": load_bot_state("kraken_bot").get("strategy", "SMA_3X_SHORT"),
            "leverage": load_bot_state("kraken_bot").get("leverage", 3),
            "balances": {"USDT": kraken_balance}
        }
    }
    
    # Send to Mission Control
    try:
        response = requests.post(
            MISSION_CONTROL_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Status-Secret": STATUS_SECRET
            },
            timeout=30
        )
        
        if response.ok:
            print(f"✅ Synced! Portfolio: ${portfolio_value:,.2f}, Position: {state.get('position', 'NONE')}")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Failed to sync: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Continuous sync")
    parser.add_argument("--interval", type=int, default=60, help="Sync interval in seconds")
    args = parser.parse_args()
    
    if args.loop:
        print(f"🔄 Starting continuous sync (every {args.interval}s)")
        while True:
            sync_to_mission_control()
            time.sleep(args.interval)
    else:
        sync_to_mission_control()


if __name__ == "__main__":
    main()
