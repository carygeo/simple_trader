#!/usr/bin/env python3
"""
Enhanced Backtest Runner v2 - With all improvements from Cary's research

Improvements implemented:
1. Signal confirmation (wait 2 bars)
2. Cooldown period (min 10 bars between trades)
3. Confidence threshold (0.65)
4. ATR volatility filter
5. Pullback entries (2% dip for longs, 2% rally for shorts)
6. Volume confirmation
7. Better parameters
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

# ===== IMPROVEMENT PARAMETERS =====
MIN_CONFIRMATION_BARS = 2      # Wait 2 bars to confirm signal
MIN_BARS_BETWEEN_TRADES = 10   # Cooldown period
MIN_CONFIDENCE = 0.65          # Only high-probability setups
VOLATILITY_MULTIPLIER = 1.5    # Skip if ATR > avg * 1.5
PULLBACK_PCT = 0.02            # Wait for 2% pullback
MIN_VOLUME_RATIO = 0.8         # Skip if volume < 80% of average


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range"""
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()


def run_improved_backtest(symbol: str, initial_capital: float = 100.0, leverage: float = 3.0):
    """Run backtest with ALL improvements"""
    
    print(f"\n📊 Testing {symbol} with Improved Strategy v2...")
    
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
    
    df = bt.df.copy()
    
    # Add ATR and volume averages
    df['atr'] = calculate_atr(df)
    df['volume_sma'] = df['volume'].rolling(20).mean()
    
    # Initialize tracking
    capital = initial_capital
    position = 0  # 1 = long, -1 = short, 0 = flat
    entry_price = 0
    trades = []
    equity_curve = [capital]
    
    # ===== IMPROVEMENT TRACKING =====
    signal_buffer = []  # For signal confirmation
    bars_since_last_trade = MIN_BARS_BETWEEN_TRADES  # Start ready to trade
    looking_to_long = False
    looking_to_short = False
    entry_trigger_price = 0
    
    # Run through data
    for i in range(60, len(df)):
        window_df = df.iloc[:i+1].copy()
        current_price = df['close'].iloc[i]
        current_atr = df['atr'].iloc[i]
        current_volume = df['volume'].iloc[i]
        avg_atr = df['atr'].iloc[max(0,i-50):i].mean()
        avg_volume = df['volume_sma'].iloc[i]
        
        bars_since_last_trade += 1
        
        # Get signal
        signal_result = strategy.analyze(window_df)
        
        # ===== IMPROVEMENT 1: Signal Confirmation =====
        signal_buffer.append(signal_result.signal)
        if len(signal_buffer) > MIN_CONFIRMATION_BARS:
            signal_buffer.pop(0)
        
        # Check if signal is confirmed (consistent for N bars)
        confirmed_signal = None
        if len(signal_buffer) == MIN_CONFIRMATION_BARS:
            if all(s == signal_buffer[0] for s in signal_buffer):
                confirmed_signal = signal_buffer[0]
        
        # ===== IMPROVEMENT 4: ATR Volatility Filter =====
        if current_atr > avg_atr * VOLATILITY_MULTIPLIER:
            confirmed_signal = None  # Skip - too volatile
        
        # ===== IMPROVEMENT 6: Volume Confirmation =====
        if avg_volume > 0 and current_volume < avg_volume * MIN_VOLUME_RATIO:
            confirmed_signal = None  # Skip - low volume
        
        # ===== IMPROVEMENT 3: Confidence Threshold =====
        if signal_result.confidence < MIN_CONFIDENCE:
            confirmed_signal = None  # Skip - low confidence
        
        # ===== IMPROVEMENT 2: Cooldown Period =====
        if bars_since_last_trade < MIN_BARS_BETWEEN_TRADES:
            confirmed_signal = None  # Still in cooldown
        
        # ===== IMPROVEMENT 5: Pullback Entry =====
        # Set up pending orders instead of immediate entry
        if confirmed_signal == Signal.LONG and position != 1 and not looking_to_long:
            looking_to_long = True
            looking_to_short = False
            entry_trigger_price = current_price * (1 - PULLBACK_PCT)  # Wait for dip
            
        elif confirmed_signal == Signal.SHORT and position != -1 and not looking_to_short:
            looking_to_short = True
            looking_to_long = False
            entry_trigger_price = current_price * (1 + PULLBACK_PCT)  # Wait for rally
        
        # Check if pullback entry triggered
        if looking_to_long and current_price <= entry_trigger_price:
            # Close short if exists
            if position == -1:
                pnl = (entry_price - current_price) / entry_price * leverage * capital
                capital += pnl
                trades.append({'type': 'close_short', 'price': current_price, 'pnl': pnl, 'bar': i})
            
            # Open long at pullback price
            position = 1
            entry_price = current_price
            trades.append({'type': 'open_long', 'price': current_price, 'confidence': signal_result.confidence, 'bar': i})
            looking_to_long = False
            bars_since_last_trade = 0
            
        elif looking_to_short and current_price >= entry_trigger_price:
            # Close long if exists
            if position == 1:
                pnl = (current_price - entry_price) / entry_price * leverage * capital
                capital += pnl
                trades.append({'type': 'close_long', 'price': current_price, 'pnl': pnl, 'bar': i})
            
            # Open short at rally price
            position = -1
            entry_price = current_price
            trades.append({'type': 'open_short', 'price': current_price, 'confidence': signal_result.confidence, 'bar': i})
            looking_to_short = False
            bars_since_last_trade = 0
        
        # Cancel pending order if signal reverses
        if confirmed_signal == Signal.SHORT:
            looking_to_long = False
        elif confirmed_signal == Signal.LONG:
            looking_to_short = False
        
        # Handle NEUTRAL signal - close positions
        if confirmed_signal == Signal.NEUTRAL and position != 0:
            if position == 1:
                pnl = (current_price - entry_price) / entry_price * leverage * capital
                capital += pnl
                trades.append({'type': 'close_long', 'price': current_price, 'pnl': pnl, 'bar': i})
            elif position == -1:
                pnl = (entry_price - current_price) / entry_price * leverage * capital
                capital += pnl
                trades.append({'type': 'close_short', 'price': current_price, 'pnl': pnl, 'bar': i})
            position = 0
            entry_price = 0
            looking_to_long = False
            looking_to_short = False
            bars_since_last_trade = 0
        
        # Update equity curve
        if position == 1:
            unrealized_pnl = (current_price - entry_price) / entry_price * leverage * capital
            equity_curve.append(capital + unrealized_pnl)
        elif position == -1:
            unrealized_pnl = (entry_price - current_price) / entry_price * leverage * capital
            equity_curve.append(capital + unrealized_pnl)
        else:
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
    
    # Trade count (only count entry trades)
    trade_count = len([t for t in trades if 'open' in t['type']])
    
    results = {
        'asset': symbol,
        'strategy': 'IMPROVED_SMA_3X_V2',
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


def generate_comparison_plot(results: dict, original_return: float, v1_return: float, save_path: str):
    """Generate comparison plot: Original vs V1 vs V2"""
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    asset = results['asset']
    
    # Plot 1: Equity curve
    ax1 = axes[0]
    ax1.plot(results['equity_curve'], label=f"Improved v2: {results['return_pct']:+.1f}%", color='green', linewidth=2)
    ax1.axhline(y=100, color='gray', linestyle='--', alpha=0.5, label='Starting Capital')
    ax1.set_title(f"{asset} Improved Strategy v2 - Equity Curve", fontsize=14, fontweight='bold')
    ax1.set_xlabel('Periods')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Comparison bar chart
    ax2 = axes[1]
    strategies = ['Original SMA 3X', 'Enhanced v1', 'Improved v2']
    returns = [original_return, v1_return, results['return_pct']]
    colors = ['#3498db', '#e74c3c', '#2ecc71' if results['return_pct'] > 0 else '#e74c3c']
    
    bars = ax2.bar(strategies, returns, color=colors, edgecolor='black', linewidth=1.5)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_title(f"{asset} Strategy Evolution", fontsize=14, fontweight='bold')
    ax2.set_ylabel('Return (%)')
    
    # Add value labels on bars
    for bar, val in zip(bars, returns):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:+.1f}%', ha='center', va='bottom' if height > 0 else 'top',
                fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"   📊 Saved plot: {save_path}")


def main():
    """Run all improved backtests and generate plots"""
    
    print("=" * 60)
    print("🧪 IMPROVED SMA STRATEGY v2 BACKTESTS")
    print("=" * 60)
    print("\nImprovements applied:")
    print(f"  • Signal confirmation: {MIN_CONFIRMATION_BARS} bars")
    print(f"  • Cooldown period: {MIN_BARS_BETWEEN_TRADES} bars")
    print(f"  • Min confidence: {MIN_CONFIDENCE}")
    print(f"  • Volatility filter: {VOLATILITY_MULTIPLIER}x ATR")
    print(f"  • Pullback entry: {PULLBACK_PCT*100}%")
    print(f"  • Volume filter: {MIN_VOLUME_RATIO*100}% avg")
    
    # Previous results for comparison
    original_results = {'LTC': 210.86, 'ETH': 145.65, 'LINK': 123.54}
    v1_results = {'LTC': -97.2, 'ETH': -48.5, 'LINK': -96.3}
    
    base_dir = os.path.dirname(__file__)
    results_dir = os.path.join(base_dir, "backtest_results", "improved_v2")
    os.makedirs(results_dir, exist_ok=True)
    
    all_results = []
    
    for asset in ASSETS:
        results = run_improved_backtest(asset)
        
        if results:
            # Generate plot
            plot_path = os.path.join(results_dir, f"{asset}_IMPROVED_V2_backtest.png")
            generate_comparison_plot(
                results, 
                original_results.get(asset, 0), 
                v1_results.get(asset, 0),
                plot_path
            )
            
            all_results.append({
                'asset': asset,
                'strategy': 'IMPROVED_SMA_3X_V2',
                'return_pct': results['return_pct'],
                'original_pct': original_results.get(asset, 0),
                'v1_pct': v1_results.get(asset, 0),
                'improvement_vs_v1': results['return_pct'] - v1_results.get(asset, 0),
                'trades': results['trades'],
                'max_dd_pct': results['max_dd_pct']
            })
    
    # Save summary CSV
    if all_results:
        df = pd.DataFrame(all_results)
        csv_path = os.path.join(results_dir, "improved_v2_summary.csv")
        df.to_csv(csv_path, index=False)
        print(f"\n📁 Saved summary: {csv_path}")
        
        # Print summary table
        print("\n" + "=" * 70)
        print("📊 RESULTS SUMMARY")
        print("=" * 70)
        print(f"{'Asset':<8} {'Original':>12} {'v1':>12} {'v2':>12} {'Trades':>8}")
        print("-" * 70)
        for r in all_results:
            print(f"{r['asset']:<8} {r['original_pct']:>+11.1f}% {r['v1_pct']:>+11.1f}% {r['return_pct']:>+11.1f}% {r['trades']:>8}")
        print("=" * 70)
    
    return all_results


if __name__ == "__main__":
    main()
