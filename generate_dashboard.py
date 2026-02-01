#!/usr/bin/env python3
"""
Generate Trader Dashboard HTML

Usage:
    python generate_dashboard.py         # Generate dashboard.html
    python generate_dashboard.py --open  # Generate and open in browser
"""

import os
import json
import subprocess
import argparse
import webbrowser
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# Load environment
load_dotenv()

print("📊 Generating Trader Dashboard...")


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
    print("   💰 Fetching balances from Coinbase...")
    try:
        from trader.coinbase import CoinbaseClient
        
        api_key = os.getenv("COINBASE_API_KEY_NAME")
        api_secret = os.getenv("COINBASE_API_KEY_SECRET", "").replace("\\n", "\n")
        
        if not api_key or not api_secret:
            print("   ⚠️  No API credentials found")
            return {}
        
        client = CoinbaseClient(api_key, api_secret)
        accounts = client.get_accounts()
        
        balances = {}
        for acc in accounts:
            currency = acc.get("currency", "")
            balance = float(acc.get("available_balance", {}).get("value", 0))
            if balance > 0.0001:
                balances[currency] = balance
        
        print(f"   ✅ Found {len(balances)} currencies with balances")
        return balances
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {}


def get_prices() -> dict:
    """Get current prices"""
    print("   📈 Fetching current prices...")
    try:
        import yfinance as yf
        
        prices = {}
        for sym in ["BTC-USD", "ETH-USD", "XRP-USD", "DOGE-USD"]:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="1d")
            if not hist.empty:
                prices[sym.replace("-USD", "")] = hist['Close'].iloc[-1]
        
        print(f"   ✅ Got prices for {len(prices)} assets")
        return prices
    except Exception as e:
        print(f"   ⚠️  Price fetch error: {e}")
        return {}


def load_backtest_results() -> pd.DataFrame:
    """Load backtest results"""
    csv_path = os.path.join(os.path.dirname(__file__), "asset_strategy_scan.csv")
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()


def load_trade_history() -> list:
    """Load trade history"""
    history_path = os.path.join(os.path.dirname(__file__), "trade_history.json")
    if os.path.exists(history_path):
        with open(history_path) as f:
            return json.load(f)
    return []


def generate_html():
    """Generate the dashboard HTML"""
    # Status
    running = is_trader_running()
    status_badge = '<span style="background:rgba(34,197,94,0.2);color:#22c55e;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;">🟢 RUNNING</span>' if running else '<span style="background:rgba(239,68,68,0.2);color:#ef4444;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;">⚪ STOPPED</span>'
    
    # Balances
    balances = get_balances()
    prices = get_prices()
    
    total_value = 0
    balance_html = ""
    for currency, amount in sorted(balances.items(), key=lambda x: -x[1] if isinstance(x[1], (int, float)) else 0):
        if currency in ["USD", "USDT", "USDC"]:
            value = amount
        elif currency in prices:
            value = amount * prices[currency]
        else:
            value = 0
        
        total_value += value
        
        if value > 0.01:
            balance_html += f'<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.1);"><span style="font-weight:600;">{currency}</span><span style="color:#9ca3af;">{amount:,.6f} (~${value:,.2f})</span></div>'
    
    if not balance_html:
        balance_html = '<p style="color:#9ca3af;">No balances found. Check API credentials.</p>'
    
    # Backtest results
    df = load_backtest_results()
    strategy_html = ""
    best_return = 0
    best_strategy = "N/A"
    best_asset = "N/A"
    hold_return = 0
    
    if not df.empty:
        df = df.sort_values('return_pct', ascending=False)
        best = df.iloc[0]
        best_return = best['return_pct']
        best_strategy = best['strategy']
        best_asset = best['asset']
        hold_return = best['hold_pct']
        
        for _, row in df.head(10).iterrows():
            ret_color = "#22c55e" if row['return_pct'] > 0 else "#ef4444"
            hold_color = "#22c55e" if row['hold_pct'] > 0 else "#ef4444"
            strategy_html += f'''<tr>
                <td><strong>{row['asset']}</strong></td>
                <td>{row['strategy']}</td>
                <td style="color:{ret_color}">{row['return_pct']:+.1f}%</td>
                <td style="color:{hold_color}">{row['hold_pct']:+.1f}%</td>
                <td>{int(row['trades'])}</td>
                <td style="color:#ef4444">{row['max_dd']:.1f}%</td>
            </tr>'''
    
    if not strategy_html:
        strategy_html = '<tr><td colspan="6" style="color:#9ca3af;">No backtest data. Run: python -m trader.backtest</td></tr>'
    
    # Trade history
    trades = load_trade_history()
    trade_html = ""
    if trades:
        for trade in trades[-10:]:
            sig_color = "#22c55e" if trade.get("signal") == "LONG" else "#ef4444"
            trade_html += f'''<tr>
                <td>{trade.get('timestamp', 'N/A')[:19]}</td>
                <td style="color:{sig_color}">{trade.get('signal', 'N/A')}</td>
                <td>${trade.get('price', 0):,.2f}</td>
                <td>{trade.get('strategy', 'N/A')}</td>
            </tr>'''
        trade_html = f'<table style="width:100%;border-collapse:collapse;font-size:0.9rem;"><thead><tr><th style="text-align:left;padding:12px;border-bottom:1px solid rgba(255,255,255,0.1);color:#9ca3af;">Time</th><th style="text-align:left;padding:12px;border-bottom:1px solid rgba(255,255,255,0.1);color:#9ca3af;">Signal</th><th style="text-align:left;padding:12px;border-bottom:1px solid rgba(255,255,255,0.1);color:#9ca3af;">Price</th><th style="text-align:left;padding:12px;border-bottom:1px solid rgba(255,255,255,0.1);color:#9ca3af;">Strategy</th></tr></thead><tbody>{trade_html}</tbody></table>'
    else:
        trade_html = '<p style="color:#9ca3af;">No trade history yet. Start the bot: python run.py</p>'
    
    # Current position
    position = "NONE"
    entry_price = 0
    trading_pair = "BTC-USDT"
    
    state_path = os.path.join(os.path.dirname(__file__), "trader_state.json")
    if os.path.exists(state_path):
        with open(state_path) as f:
            state = json.load(f)
            position = state.get("position", "NONE")
            entry_price = state.get("entry_price", 0)
            trading_pair = state.get("trading_pair", "BTC-USDT")
    
    pos_color = "#22c55e" if position == "LONG" else "#ef4444" if position == "SHORT" else "#9ca3af"
    hold_color = "#22c55e" if hold_return > 0 else "#ef4444"
    outperform = best_return - hold_return
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trader Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e5e5e5; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ font-size: 1.8rem; margin-bottom: 20px; display: flex; align-items: center; gap: 12px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 20px; }}
        .card {{ background: #1a1b23; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; }}
        .card h2 {{ font-size: 0.9rem; color: #9ca3af; margin-bottom: 12px; text-transform: uppercase; }}
        .card .value {{ font-size: 2rem; font-weight: 700; }}
        .card .sub {{ font-size: 0.85rem; color: #9ca3af; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }}
        th {{ color: #9ca3af; font-weight: 500; font-size: 0.8rem; text-transform: uppercase; }}
        .refresh {{ font-size: 0.75rem; color: #9ca3af; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 Trader Dashboard {status_badge}</h1>
        
        <div class="grid">
            <div class="card">
                <h2>💰 Total Portfolio Value</h2>
                <div class="value">${total_value:,.2f}</div>
                <div class="sub">Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
            </div>
            <div class="card">
                <h2>📊 Current Position</h2>
                <div class="value" style="color:{pos_color}">{position}</div>
                <div class="sub">{trading_pair} @ ${entry_price:,.2f}</div>
            </div>
            <div class="card">
                <h2>🎯 Best Strategy (30d Backtest)</h2>
                <div class="value" style="color:#22c55e">+{best_return:.1f}%</div>
                <div class="sub">{best_strategy} on {best_asset}</div>
            </div>
            <div class="card">
                <h2>📉 Buy & Hold Comparison</h2>
                <div class="value" style="color:{hold_color}">{hold_return:+.1f}%</div>
                <div class="sub">Strategy outperforms by {outperform:.1f}%</div>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 20px;">
            <h2>💵 Account Balances</h2>
            <div style="max-height: 200px; overflow-y: auto;">{balance_html}</div>
        </div>
        
        <div class="card" style="margin-bottom: 20px;">
            <h2>🏆 Top Performing Strategies (30-Day Backtest)</h2>
            <table>
                <thead><tr><th>Asset</th><th>Strategy</th><th>Return</th><th>vs Hold</th><th>Trades</th><th>Max DD</th></tr></thead>
                <tbody>{strategy_html}</tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>📜 Recent Trades</h2>
            {trade_html}
        </div>
        
        <div class="refresh">
            Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} • Re-run script to refresh
        </div>
    </div>
</body>
</html>'''
    
    return html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true", help="Open in browser")
    args = parser.parse_args()
    
    html = generate_html()
    
    output_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard generated: {output_path}")
    
    if args.open:
        webbrowser.open(f"file://{output_path}")
        print("   🌐 Opened in browser")
    else:
        print(f"   Open in browser: file://{output_path}")


if __name__ == "__main__":
    main()
