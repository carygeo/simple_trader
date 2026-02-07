#!/usr/bin/env python3
"""
Run backtests with Enhanced SMA Strategy
Generates plots and compares to original SMA performance
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from trader.backtest import Backtester
from trader.enhanced_strategies import EnhancedSMAStrategy, Signal

# Top performers to test
ASSETS = ["LTC", "ETH", "LINK"]
TIMEFRAME_DAYS = 365


def run_enhanced_backtest(symbol: str, initial_capital: float = 100.0, leverage: float = 3.0):
    """Run backtest with enhanced strategy"""
    
    print(f"\n📊 Testing {symbol} with Enhanced SMA 3X...")
    
    # Fetch data
    bt = Backtester(symbol=f"{symbol}-USD", initial_capital=initial_capital, mode="leveraged", leverage=leverage)
    bt.fetch_data(days=TIMEFRAME_DAYS)
    
    if bt.df is None or len(bt.df) < 100:
        print(f"   ❌ Not enough data for {symbol}")
        return None
    
    # Initialize strategy
    strategy = EnhancedSMAStrategy(
        fast_period=20,
        slow_period=50,
        use_rsi_filter=True,
        use_macd_confirm=True,
        use_slope_filter=True,
        risk_per_trade=0.02
    )
    
    # Manual backtest with enhanced strategy
    df = bt.df.copy()
    
    # Initialize tracking
    capital = initial_capital
    position = 0  # 1 = long, -1 = short, 0 = flat
    entry_price = 0
    trades = []
    equity_curve = [capital]
    
    # Run through data
    for i in range(60, len(df)):  # Start after warmup period
        window_df = df.iloc[:i+1].copy()
        current_price = df['close'].iloc[i]
        
        # Get signal
        signal_result = strategy.analyze(window_df)
        
        # Execute trades
        if signal_result.signal == Signal.LONG and position != 1:
            # Close short if exists
            if position == -1:
                pnl = (entry_price - current_price) / entry_price * leverage * capital
                capital += pnl
                trades.append({'type': 'close_short', 'price': current_price, 'pnl': pnl})
            
            # Open long
            position = 1
            entry_price = current_price
            trades.append({'type': 'open_long', 'price': current_price, 'confidence': signal_result.confidence})
            
        elif signal_result.signal == Signal.SHORT and position != -1:
            # Close long if exists
            if position == 1:
                pnl = (current_price - entry_price) / entry_price * leverage * capital
                capital += pnl
                trades.append({'type': 'close_long', 'price': current_price, 'pnl': pnl})
            
            # Open short
            position = -1
            entry_price = current_price
            trades.append({'type': 'open_short', 'price': current_price, 'confidence': signal_result.confidence})
            
        elif signal_result.signal == Signal.NEUTRAL and position != 0:
            # Close any position
            if position == 1:
                pnl = (current_price - entry_price) / entry_price * leverage * capital
                capital += pnl
                trades.append({'type': 'close_long', 'price': current_price, 'pnl': pnl})
            elif position == -1:
                pnl = (entry_price - current_price) / entry_price * leverage * capital
                capital += pnl
                trades.append({'type': 'close_short', 'price': current_price, 'pnl': pnl})
            position = 0
            entry_price = 0
        
        equity_curve.append(capital)
    
    # Close any remaining position
    if position != 0:
        current_price = df['close'].iloc[-1]
        if position == 1:
            pnl = (current_price - entry_price) / entry_price * leverage * capital
        else:
            pnl = (entry_price - current_price) / entry_price * leverage * capital
        capital += pnl
        equity_curve[-1] = capital
    
    # Calculate metrics
    final_capital = capital
    total_return = (final_capital - initial_capital) / initial_capital * 100
    
    # Buy & hold comparison
    buy_hold_return = (df['close'].iloc[-1] - df['close'].iloc[60]) / df['close'].iloc[60] * 100 * leverage
    
    # Max drawdown
    equity_series = pd.Series(equity_curve)
    rolling_max = equity_series.expanding().max()
    drawdowns = (equity_series - rolling_max) / rolling_max * 100
    max_drawdown = drawdowns.min()
    
    # Trade count
    trade_count = len([t for t in trades if 'open' in t['type']])
    
    results = {
        'asset': symbol,
        'strategy': 'ENHANCED_SMA_3X_SHORT',
        'return_pct': total_return,
        'hold_pct': buy_hold_return,
        'trades': trade_count,
        'max_dd_pct': max_drawdown,
        'final_capital': final_capital,
        'equity_curve': equity_curve,
        'df': df
    }
    
    print(f"   Return: {total_return:+.1f}%")
    print(f"   Max DD: {max_drawdown:.1f}%")
    print(f"   Trades: {trade_count}")
    
    return results


def generate_comparison_plot(results: dict, original_return: float, save_path: str):
    """Generate comparison plot: Enhanced vs Original"""
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    asset = results['asset']
    
    # Plot 1: Equity curve
    ax1 = axes[0]
    ax1.plot(results['equity_curve'], label=f"Enhanced SMA 3X: {results['return_pct']:+.1f}%", color='green', linewidth=2)
    ax1.axhline(y=100, color='gray', linestyle='--', alpha=0.5, label='Starting Capital')
    ax1.set_title(f"{asset} Enhanced SMA Strategy - Equity Curve", fontsize=14, fontweight='bold')
    ax1.set_xlabel('Periods')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Comparison bar chart
    ax2 = axes[1]
    strategies = ['Original SMA 3X', 'Enhanced SMA 3X']
    returns = [original_return, results['return_pct']]
    colors = ['#3498db', '#2ecc71' if results['return_pct'] > original_return else '#e74c3c']
    
    bars = ax2.bar(strategies, returns, color=colors, edgecolor='black', linewidth=1.5)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title(f"{asset} Strategy Comparison", fontsize=14, fontweight='bold')
    ax2.set_ylabel('Return (%)')
    
    # Add value labels on bars
    for bar, val in zip(bars, returns):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:+.1f}%', ha='center', va='bottom' if height > 0 else 'top',
                fontsize=12, fontweight='bold')
    
    # Add improvement annotation
    improvement = results['return_pct'] - original_return
    ax2.text(0.5, 0.02, f"Improvement: {improvement:+.1f}%", 
             transform=ax2.transAxes, ha='center', fontsize=11,
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"   📊 Saved plot: {save_path}")


def main():
    """Run all enhanced backtests and generate plots"""
    
    print("=" * 60)
    print("🧪 ENHANCED SMA STRATEGY BACKTESTS")
    print("=" * 60)
    
    # Original results for comparison (from previous backtests)
    original_results = {
        'LTC': 210.86,  # Original SMA_3X_SHORT
        'ETH': 145.65,  # Original BREAKOUT_3X_SHORT  
        'LINK': 123.54  # Original SMA_3X_SHORT
    }
    
    base_dir = os.path.dirname(__file__)
    results_dir = os.path.join(base_dir, "backtest_results", "enhanced")
    os.makedirs(results_dir, exist_ok=True)
    
    all_results = []
    
    for asset in ASSETS:
        results = run_enhanced_backtest(asset)
        
        if results:
            # Generate plot
            plot_path = os.path.join(results_dir, f"{asset}_ENHANCED_SMA_3X_backtest.png")
            generate_comparison_plot(results, original_results.get(asset, 0), plot_path)
            
            all_results.append({
                'asset': asset,
                'strategy': 'ENHANCED_SMA_3X_SHORT',
                'return_pct': results['return_pct'],
                'original_pct': original_results.get(asset, 0),
                'improvement': results['return_pct'] - original_results.get(asset, 0),
                'trades': results['trades'],
                'max_dd_pct': results['max_dd_pct']
            })
    
    # Save summary CSV
    if all_results:
        df = pd.DataFrame(all_results)
        csv_path = os.path.join(results_dir, "enhanced_summary.csv")
        df.to_csv(csv_path, index=False)
        print(f"\n📁 Saved summary: {csv_path}")
        
        # Print summary table
        print("\n" + "=" * 60)
        print("📊 RESULTS SUMMARY")
        print("=" * 60)
        print(f"{'Asset':<8} {'Original':>12} {'Enhanced':>12} {'Change':>12} {'Trades':>8}")
        print("-" * 60)
        for r in all_results:
            print(f"{r['asset']:<8} {r['original_pct']:>+11.1f}% {r['return_pct']:>+11.1f}% {r['improvement']:>+11.1f}% {r['trades']:>8}")
        print("=" * 60)
    
    return all_results


if __name__ == "__main__":
    main()
