#!/usr/bin/env python3
"""
Trader Dashboard - Monitor your crypto trading bot

Usage:
    python dashboard.py              # Start dashboard server
    python dashboard.py --port 8888  # Custom port
"""

import os
import json
import subprocess
import argparse
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from dotenv import load_dotenv
import pandas as pd

# Load environment
load_dotenv()

# Dashboard CSS (separate to avoid escaping issues)
DASHBOARD_CSS = """
:root {
    --bg: #0f1117;
    --card: #1a1b23;
    --border: rgba(255,255,255,0.1);
    --text: #e5e5e5;
    --muted: #9ca3af;
    --green: #22c55e;
    --red: #ef4444;
    --blue: #3b82f6;
    --yellow: #eab308;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 20px;
}
.container { max-width: 1200px; margin: 0 auto; }
h1 { 
    font-size: 1.8rem; 
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.status-badge {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
}
.status-running { background: rgba(34, 197, 94, 0.2); color: var(--green); }
.status-stopped { background: rgba(239, 68, 68, 0.2); color: var(--red); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 20px; }
.card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
}
.card h2 { font-size: 0.9rem; color: var(--muted); margin-bottom: 12px; text-transform: uppercase; }
.card .value { font-size: 2rem; font-weight: 700; }
.card .sub { font-size: 0.85rem; color: var(--muted); margin-top: 4px; }
.positive { color: var(--green); }
.negative { color: var(--red); }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 500; font-size: 0.8rem; text-transform: uppercase; }
tr:hover { background: rgba(255,255,255,0.03); }
.refresh { font-size: 0.75rem; color: var(--muted); margin-top: 20px; text-align: center; }
.balance-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border); }
.balance-row:last-child { border-bottom: none; }
.balance-currency { font-weight: 600; }
.balance-value { color: var(--muted); }
.position-long { color: var(--green); }
.position-short { color: var(--red); }
.position-none { color: var(--muted); }
"""


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
            return {"USD": 0.0}
        
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
        return {"Error": str(e)}


def get_prices() -> dict:
    """Get current prices for major assets"""
    try:
        import yfinance as yf
        
        prices = {}
        symbols = ["BTC-USD", "ETH-USD"]
        
        for sym in symbols:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="1d")
            if not hist.empty:
                prices[sym.replace("-USD", "")] = hist['Close'].iloc[-1]
        
        return prices
    except:
        return {}


def load_backtest_results() -> pd.DataFrame:
    """Load backtest results from CSV"""
    csv_path = os.path.join(os.path.dirname(__file__), "asset_strategy_scan.csv")
    try:
        if os.path.exists(csv_path):
            return pd.read_csv(csv_path)
    except:
        pass
    return pd.DataFrame()


def load_trade_history() -> list:
    """Load trade history if available"""
    history_path = os.path.join(os.path.dirname(__file__), "trade_history.json")
    try:
        if os.path.exists(history_path):
            with open(history_path) as f:
                return json.load(f)
    except:
        pass
    return []


def generate_dashboard() -> str:
    """Generate the dashboard HTML"""
    # Check status
    running = is_trader_running()
    status_class = "status-running" if running else "status-stopped"
    status_text = "🟢 RUNNING" if running else "⚪ STOPPED"
    
    # Get balances
    balances = get_balances()
    prices = get_prices()
    
    # Calculate total value
    total_value = 0
    balance_rows = []
    for currency, amount in sorted(balances.items(), key=lambda x: -x[1] if isinstance(x[1], (int, float)) else 0):
        if currency in ["USD", "USDT", "USDC"]:
            value = amount if isinstance(amount, (int, float)) else 0
        elif currency in prices:
            value = amount * prices[currency] if isinstance(amount, (int, float)) else 0
        else:
            value = 0
        
        total_value += value
        
        if isinstance(amount, (int, float)) and value > 0.01:
            balance_rows.append(f'''
                <div class="balance-row">
                    <span class="balance-currency">{currency}</span>
                    <span class="balance-value">{amount:,.6f} (~${value:,.2f})</span>
                </div>
            ''')
    
    # Load backtest results
    df = load_backtest_results()
    
    strategy_rows = []
    best_return = 0
    best_strategy = "SMA"
    best_asset = "BTC"
    hold_return = 0
    
    if not df.empty:
        df = df.sort_values('return_pct', ascending=False).head(10)
        best = df.iloc[0]
        best_return = best['return_pct']
        best_strategy = best['strategy']
        best_asset = best['asset']
        hold_return = best['hold_pct']
        
        for _, row in df.iterrows():
            return_class = "positive" if row['return_pct'] > 0 else "negative"
            hold_class = "positive" if row['hold_pct'] > 0 else "negative"
            
            strategy_rows.append(f'''
                <tr>
                    <td><strong>{row['asset']}</strong></td>
                    <td>{row['strategy']}</td>
                    <td class="{return_class}">{row['return_pct']:+.1f}%</td>
                    <td class="{hold_class}">{row['hold_pct']:+.1f}%</td>
                    <td>{int(row['trades'])}</td>
                    <td class="negative">{row['max_dd']:.1f}%</td>
                </tr>
            ''')
    
    # Trade history
    trades = load_trade_history()
    if trades:
        trade_html = "<table><thead><tr><th>Time</th><th>Signal</th><th>Price</th><th>Strategy</th></tr></thead><tbody>"
        for trade in trades[-10:]:
            signal_class = "positive" if trade.get("signal") == "LONG" else "negative"
            trade_html += f'''
                <tr>
                    <td>{trade.get('timestamp', 'N/A')[:19]}</td>
                    <td class="{signal_class}">{trade.get('signal', 'N/A')}</td>
                    <td>${trade.get('price', 0):,.2f}</td>
                    <td>{trade.get('strategy', 'N/A')}</td>
                </tr>
            '''
        trade_html += "</tbody></table>"
    else:
        trade_html = '<p style="color: var(--muted);">No trade history yet. Start the bot to begin trading.</p>'
    
    # Current position
    position = "NONE"
    entry_price = 0
    trading_pair = "BTC-USDT"
    
    state_path = os.path.join(os.path.dirname(__file__), "trader_state.json")
    try:
        if os.path.exists(state_path):
            with open(state_path) as f:
                state = json.load(f)
                position = state.get("position", "NONE")
                entry_price = state.get("entry_price", 0)
                trading_pair = state.get("trading_pair", "BTC-USDT")
    except:
        pass
    
    position_class = position.lower() if position in ["LONG", "SHORT"] else "none"
    outperform = best_return - hold_return
    hold_class = "positive" if hold_return > 0 else "negative"
    
    # Build HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trader Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>{DASHBOARD_CSS}</style>
</head>
<body>
    <div class="container">
        <h1>
            📈 Trader Dashboard
            <span class="status-badge {status_class}">{status_text}</span>
        </h1>
        
        <div class="grid">
            <div class="card">
                <h2>💰 Total Portfolio Value</h2>
                <div class="value">${total_value:,.2f}</div>
                <div class="sub">Last updated: {datetime.now().strftime("%H:%M:%S")}</div>
            </div>
            <div class="card">
                <h2>📊 Current Position</h2>
                <div class="value position-{position_class}">{position}</div>
                <div class="sub">{trading_pair} @ ${entry_price:,.2f}</div>
            </div>
            <div class="card">
                <h2>🎯 Best Strategy (30d)</h2>
                <div class="value positive">+{best_return:.1f}%</div>
                <div class="sub">{best_strategy} on {best_asset}</div>
            </div>
            <div class="card">
                <h2>📉 Buy & Hold Comparison</h2>
                <div class="value {hold_class}">{hold_return:+.1f}%</div>
                <div class="sub">Strategy outperforms by {outperform:.1f}%</div>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 20px;">
            <h2>💵 Account Balances</h2>
            <div style="max-height: 200px; overflow-y: auto;">
                {"".join(balance_rows) or '<p style="color: var(--muted);">No balances found</p>'}
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 20px;">
            <h2>🏆 Top Performing Strategies (30-Day Backtest)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Asset</th>
                        <th>Strategy</th>
                        <th>Return</th>
                        <th>vs Hold</th>
                        <th>Trades</th>
                        <th>Max Drawdown</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(strategy_rows) or '<tr><td colspan="6">No backtest data</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>📜 Recent Trades</h2>
            {trade_html}
        </div>
        
        <div class="refresh">
            Auto-refreshes every 30 seconds • {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
</body>
</html>'''
    
    return html


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for dashboard"""
    
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(generate_dashboard().encode())
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            data = {
                "running": is_trader_running(),
                "balances": get_balances(),
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(data).encode())
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="Trader Dashboard")
    parser.add_argument("--port", type=int, default=8765, help="Port to run on")
    args = parser.parse_args()
    
    print(f"🚀 Starting Trader Dashboard on http://localhost:{args.port}")
    print(f"   Press Ctrl+C to stop")
    
    server = HTTPServer(("0.0.0.0", args.port), DashboardHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⛔ Dashboard stopped")


if __name__ == "__main__":
    main()
