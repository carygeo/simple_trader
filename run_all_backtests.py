#!/usr/bin/env python3
"""
Run backtests for all assets, strategies, and timeframes.
Generates plots and CSV summary for Mission Control.
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(__file__))

from trader.backtest import Backtester

ASSETS = ["BTC", "ETH", "DOGE", "XRP", "SOL", "ADA", "AVAX", "ATOM", "DOT", "LINK", "NEAR", "LTC"]
STRATEGIES = ["sma", "macd", "combined"]
TIMEFRAMES = {
    "1mo": 30,
    "6mo": 180,
    "1yr": 365
}

def run_all_backtests(initial_capital: float = 91.0):
    """Run backtests for all combinations"""
    
    base_dir = os.path.dirname(__file__)
    results_dir = os.path.join(base_dir, "backtest_results")
    
    for tf_name, days in TIMEFRAMES.items():
        print(f"\n{'='*60}")
        print(f"📊 Running {tf_name} ({days} days) backtests...")
        print(f"{'='*60}")
        
        # Create timeframe directory
        tf_dir = os.path.join(results_dir, tf_name)
        os.makedirs(tf_dir, exist_ok=True)
        
        all_results = []
        
        for asset in ASSETS:
            symbol = f"{asset}-USD"
            print(f"\n🔄 {asset}...")
            
            try:
                bt = Backtester(symbol=symbol, initial_capital=initial_capital)
                bt.fetch_data(days=days)
                
                for strategy in STRATEGIES:
                    try:
                        result = bt.run(strategy)
                        
                        # Save plot
                        plot_file = os.path.join(tf_dir, f"{asset}_{strategy.upper()}_backtest.png")
                        bt.plot(save_path=plot_file, show=False)
                        
                        # Collect result
                        all_results.append({
                            "asset": asset,
                            "strategy": strategy.upper(),
                            "start_date": result.start_date,
                            "end_date": result.end_date,
                            "trading_days": days,
                            "candles": len(bt.df) if bt.df is not None else 0,
                            "initial_capital": result.initial_capital,
                            "final_value": result.final_value,
                            "hold_final_value": result.initial_capital * (1 + result.buy_hold_return_pct/100),
                            "strategy_return_pct": result.total_return_pct,
                            "hold_return_pct": result.buy_hold_return_pct,
                            "outperformance_pct": result.outperformance_pct,
                            "total_trades": result.total_trades,
                            "buy_signals": result.winning_trades + result.losing_trades,
                            "sell_signals": result.total_trades,
                            "max_drawdown_pct": result.max_drawdown_pct,
                            "sharpe_ratio": result.sharpe_ratio,
                            "plot_file": plot_file
                        })
                        
                        print(f"   ✅ {strategy.upper()}: {result.total_return_pct:+.1f}% (Sharpe: {result.sharpe_ratio:.2f})")
                        
                    except Exception as e:
                        print(f"   ❌ {strategy.upper()}: {e}")
                        
            except Exception as e:
                print(f"   ❌ Failed to fetch {asset}: {e}")
        
        # Save CSV summary
        if all_results:
            df = pd.DataFrame(all_results)
            df = df.sort_values("strategy_return_pct", ascending=False)
            
            csv_file = os.path.join(tf_dir, f"backtest_summary_{tf_name}.csv")
            df.to_csv(csv_file, index=False)
            print(f"\n📁 Saved {len(all_results)} results to {csv_file}")
            
            # Also save to main results dir with timestamp
            main_csv = os.path.join(results_dir, f"comprehensive_backtest_{tf_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            df.to_csv(main_csv, index=False)


def run_single_timeframe(tf_name: str, initial_capital: float = 91.0):
    """Run backtests for a single timeframe"""
    if tf_name not in TIMEFRAMES:
        print(f"Unknown timeframe: {tf_name}. Use: {list(TIMEFRAMES.keys())}")
        return
    
    days = TIMEFRAMES[tf_name]
    base_dir = os.path.dirname(__file__)
    results_dir = os.path.join(base_dir, "backtest_results")
    tf_dir = os.path.join(results_dir, tf_name)
    os.makedirs(tf_dir, exist_ok=True)
    
    print(f"📊 Running {tf_name} ({days} days) backtests...")
    
    all_results = []
    
    for asset in ASSETS:
        symbol = f"{asset}-USD"
        print(f"\n🔄 {asset}...")
        
        try:
            bt = Backtester(symbol=symbol, initial_capital=initial_capital)
            bt.fetch_data(days=days)
            
            for strategy in STRATEGIES:
                try:
                    result = bt.run(strategy)
                    
                    # Save plot
                    plot_file = os.path.join(tf_dir, f"{asset}_{strategy.upper()}_backtest.png")
                    bt.plot(save_path=plot_file, show=False)
                    
                    all_results.append({
                        "asset": asset,
                        "strategy": strategy.upper(),
                        "start_date": result.start_date,
                        "end_date": result.end_date,
                        "trading_days": days,
                        "candles": len(bt.df) if bt.df is not None else 0,
                        "initial_capital": result.initial_capital,
                        "final_value": result.final_value,
                        "hold_final_value": result.initial_capital * (1 + result.buy_hold_return_pct/100),
                        "strategy_return_pct": result.total_return_pct,
                        "hold_return_pct": result.buy_hold_return_pct,
                        "outperformance_pct": result.outperformance_pct,
                        "total_trades": result.total_trades,
                        "buy_signals": result.winning_trades + result.losing_trades,
                        "sell_signals": result.total_trades,
                        "max_drawdown_pct": result.max_drawdown_pct,
                        "sharpe_ratio": result.sharpe_ratio,
                        "plot_file": plot_file
                    })
                    
                    print(f"   ✅ {strategy.upper()}: {result.total_return_pct:+.1f}%")
                    
                except Exception as e:
                    print(f"   ❌ {strategy.upper()}: {e}")
                    
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    # Save CSV
    if all_results:
        df = pd.DataFrame(all_results)
        df = df.sort_values("strategy_return_pct", ascending=False)
        csv_file = os.path.join(tf_dir, f"backtest_summary_{tf_name}.csv")
        df.to_csv(csv_file, index=False)
        print(f"\n📁 Saved {len(all_results)} results to {csv_file}")
        return df
    
    return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", "-t", choices=["1mo", "6mo", "1yr", "all"], default="all")
    parser.add_argument("--capital", type=float, default=91.0)
    args = parser.parse_args()
    
    if args.timeframe == "all":
        run_all_backtests(args.capital)
    else:
        run_single_timeframe(args.timeframe, args.capital)
