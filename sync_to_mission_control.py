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


def load_backtest_results() -> list:
    """Load backtest results"""
    csv_path = os.path.join(os.path.dirname(__file__), "asset_strategy_scan.csv")
    try:
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            df = df.sort_values('return_pct', ascending=False)
            return df.to_dict('records')
    except:
        pass
    return []


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
    """Load trader state"""
    state_path = os.path.join(os.path.dirname(__file__), "trader_state.json")
    try:
        if os.path.exists(state_path):
            with open(state_path) as f:
                return json.load(f)
    except:
        pass
    return {}


def sync_to_mission_control():
    """Sync all trader data to Mission Control"""
    print(f"📊 Syncing trader data to Mission Control...")
    
    # Gather all data
    running = is_trader_running()
    balances = get_balances()
    prices = get_prices()
    strategies = load_backtest_results()
    trades = load_trade_history()
    state = load_trader_state()
    
    # Calculate portfolio value
    portfolio_value = 0
    for currency, amount in balances.items():
        if currency in ["USD", "USDT", "USDC"]:
            portfolio_value += amount
        elif currency in prices:
            portfolio_value += amount * prices[currency]
    
    # Build payload
    payload = {
        "running": running,
        "portfolioValue": portfolio_value,
        "position": state.get("position", "NONE"),
        "tradingPair": state.get("trading_pair", "BTC-USDT"),
        "entryPrice": state.get("entry_price", 0),
        "balances": balances,
        "prices": prices,
        "strategies": strategies[:20],  # Top 20
        "trades": trades[-50:]  # Last 50
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
