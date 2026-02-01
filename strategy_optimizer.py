#!/usr/bin/env python3
"""
Strategy Optimizer - Find the best parameters for 1000%+ annual returns
Target: 10x returns in 1 year

Strategies to test:
1. SMA Crossover with different periods
2. MACD with different settings
3. Combined strategies
4. With/without trailing stops
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))

from trader.backtest import Backtester

# Assets to test
ASSETS = ["BTC", "ETH", "DOGE", "XRP", "SOL", "ADA", "AVAX", "ATOM", "DOT", "LINK", "NEAR", "LTC"]

# SMA period combinations to test
SMA_PERIODS = [
    (5, 10),   # Ultra fast
    (5, 20),   # Fast
    (10, 20),  # Quick
    (10, 30),  # Medium-fast
    (15, 30),  # Medium
    (20, 50),  # Standard (current)
    (20, 60),  # Slower
    (30, 60),  # Slow
]

# MACD settings to test (fast, slow, signal)
MACD_SETTINGS = [
    (6, 13, 5),   # Fast MACD
    (8, 17, 9),   # Quick MACD
    (12, 26, 9),  # Standard (current)
    (5, 35, 5),   # Wide MACD
]

# Trailing stop percentages
TRAILING_STOPS = [0, 3, 5, 7, 10]  # 0 = no stop


def run_sma_optimization(days: int = 365, initial_capital: float = 91.0) -> pd.DataFrame:
    """Test all SMA period combinations"""
    results = []
    
    for asset in ASSETS:
        symbol = f"{asset}-USD"
        print(f"\n🔍 Testing {asset}...")
        
        try:
            bt = Backtester(symbol=symbol, initial_capital=initial_capital)
            bt.fetch_data(days=days)
            
            for fast, slow in SMA_PERIODS:
                try:
                    # Temporarily modify strategy
                    from trader.strategies import SMAStrategy
                    strategy = SMAStrategy(fast_period=fast, slow_period=slow, use_rsi_filter=False)
                    
                    result = bt.run_with_strategy(strategy)
                    
                    results.append({
                        'asset': asset,
                        'strategy': f'SMA_{fast}/{slow}',
                        'fast_period': fast,
                        'slow_period': slow,
                        'return_pct': result.total_return_pct,
                        'hold_pct': result.buy_hold_return_pct,
                        'outperform': result.outperformance_pct,
                        'trades': result.total_trades,
                        'max_dd': result.max_drawdown_pct,
                        'sharpe': result.sharpe_ratio,
                        'win_rate': result.win_rate_pct
                    })
                    
                    print(f"  SMA {fast}/{slow}: {result.total_return_pct:+.1f}%")
                    
                except Exception as e:
                    print(f"  SMA {fast}/{slow}: ERROR - {e}")
                    
        except Exception as e:
            print(f"  Failed to fetch {asset}: {e}")
    
    df = pd.DataFrame(results)
    df = df.sort_values('return_pct', ascending=False)
    return df


def run_quick_scan(days: int = 365, initial_capital: float = 91.0) -> pd.DataFrame:
    """Quick scan of all assets with standard strategies"""
    results = []
    
    for asset in ASSETS:
        symbol = f"{asset}-USD"
        print(f"🔍 {asset}...", end=" ")
        
        try:
            bt = Backtester(symbol=symbol, initial_capital=initial_capital)
            bt.fetch_data(days=days)
            
            # Test standard strategies
            for strategy_name in ['sma', 'macd', 'combined']:
                try:
                    result = bt.run(strategy_name)
                    results.append({
                        'asset': asset,
                        'strategy': strategy_name.upper(),
                        'return_pct': result.total_return_pct,
                        'hold_pct': result.buy_hold_return_pct,
                        'outperform': result.outperformance_pct,
                        'trades': result.total_trades,
                        'max_dd': result.max_drawdown_pct,
                        'sharpe': result.sharpe_ratio
                    })
                    print(f"{strategy_name}:{result.total_return_pct:+.0f}%", end=" ")
                except:
                    pass
            print()
            
            # Close figures to prevent memory issues
            plt.close('all')
            
        except Exception as e:
            print(f"ERROR: {e}")
    
    df = pd.DataFrame(results)
    df = df.sort_values('return_pct', ascending=False)
    return df


def analyze_results(df: pd.DataFrame) -> str:
    """Analyze optimization results"""
    report = []
    report.append("=" * 60)
    report.append("📊 STRATEGY OPTIMIZATION RESULTS")
    report.append("=" * 60)
    
    # Top 10 overall
    report.append("\n🏆 TOP 10 STRATEGIES (by return):")
    for i, row in df.head(10).iterrows():
        report.append(f"  {row['asset']} {row['strategy']}: {row['return_pct']:+.1f}% "
                     f"(Sharpe: {row['sharpe']:.2f}, DD: {row['max_dd']:.1f}%)")
    
    # Best per asset
    report.append("\n📈 BEST STRATEGY PER ASSET:")
    best_per_asset = df.loc[df.groupby('asset')['return_pct'].idxmax()]
    for _, row in best_per_asset.iterrows():
        report.append(f"  {row['asset']}: {row['strategy']} → {row['return_pct']:+.1f}%")
    
    # Strategies hitting 1000%+
    report.append("\n🎯 STRATEGIES WITH 1000%+ RETURNS:")
    mega_returns = df[df['return_pct'] >= 1000]
    if len(mega_returns) > 0:
        for _, row in mega_returns.iterrows():
            report.append(f"  🚀 {row['asset']} {row['strategy']}: {row['return_pct']:+.1f}%")
    else:
        report.append("  None found yet - need more optimization!")
        
        # Show path to 1000%
        best = df.iloc[0]
        current_best = best['return_pct']
        report.append(f"\n  Current best: {best['asset']} {best['strategy']} at {current_best:+.1f}%")
        report.append(f"  Gap to 1000%: {1000 - current_best:.1f}%")
        report.append(f"  Need to improve by: {(1000/current_best - 1)*100:.0f}%")
    
    return "\n".join(report)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["quick", "sma", "full"], default="quick")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--capital", type=float, default=91.0)
    args = parser.parse_args()
    
    print(f"🎯 Target: 1000%+ annual returns")
    print(f"📅 Testing {args.days} days of history")
    print(f"💰 Initial capital: ${args.capital}")
    print()
    
    if args.mode == "quick":
        df = run_quick_scan(args.days, args.capital)
    elif args.mode == "sma":
        df = run_sma_optimization(args.days, args.capital)
    else:
        # Full optimization
        df = run_sma_optimization(args.days, args.capital)
    
    # Save results
    output_file = f"optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(output_file, index=False)
    print(f"\n📁 Results saved to: {output_file}")
    
    # Print analysis
    print(analyze_results(df))
