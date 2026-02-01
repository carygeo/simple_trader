"""
Backtesting Module - Test strategies against historical data

Usage:
    python -m trader.backtest --strategy sma --days 30
    python -m trader.backtest --strategy macd --pair ETH-USD --plot
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Optional, Tuple
from dataclasses import dataclass
import yfinance as yf

from .strategies import (
    SMAStrategy, MACDStrategy, CombinedStrategy,
    Signal, TradeSignal, get_strategy
)


@dataclass
class BacktestResult:
    """Results from a backtest run"""
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    total_return_pct: float
    buy_hold_return_pct: float
    outperformance_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    avg_trade_return_pct: float
    
    def __str__(self):
        return f"""
{'='*60}
📊 BACKTEST RESULTS: {self.strategy_name}
{'='*60}
Period: {self.start_date} to {self.end_date}

💰 RETURNS
   Initial Capital:    ${self.initial_capital:,.2f}
   Final Value:        ${self.final_value:,.2f}
   Strategy Return:    {self.total_return_pct:+.2f}%
   Buy & Hold Return:  {self.buy_hold_return_pct:+.2f}%
   Outperformance:     {self.outperformance_pct:+.2f}%

📈 TRADING STATS
   Total Trades:       {self.total_trades}
   Winning Trades:     {self.winning_trades}
   Losing Trades:      {self.losing_trades}
   Win Rate:           {self.win_rate_pct:.1f}%

⚠️ RISK METRICS
   Max Drawdown:       {self.max_drawdown_pct:.2f}%
   Sharpe Ratio:       {self.sharpe_ratio:.2f}
   Profit Factor:      {self.profit_factor:.2f}
   Avg Trade Return:   {self.avg_trade_return_pct:+.3f}%
{'='*60}
"""


class Backtester:
    """Backtest trading strategies against historical data"""
    
    def __init__(
        self,
        symbol: str = "BTC-USD",
        initial_capital: float = 1000.0,
        mode: str = "long_only",  # "long_only" or "leveraged"
        leverage: float = 1.0  # Leverage multiplier (1.0 = no leverage, 3.0 = 3x)
    ):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.mode = mode  # "long_only" = only long positions, "leveraged" = long + short
        self.leverage = leverage if mode == "leveraged" else 1.0  # Only apply leverage in leveraged mode
        self.df: Optional[pd.DataFrame] = None
        self.trades: list = []
        self.last_strategy_name: str = ""
    
    def fetch_data(self, days: int = 30, interval: str = "1h") -> pd.DataFrame:
        """Fetch historical price data"""
        print(f"📥 Fetching {days} days of {self.symbol} data...")
        
        ticker = yf.Ticker(self.symbol)
        
        # yfinance period options
        if days <= 7:
            period = "7d"
        elif days <= 30:
            period = "1mo"
        elif days <= 90:
            period = "3mo"
        else:
            period = "1y"
        
        df = ticker.history(period=period, interval=interval)
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        
        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'timestamp'})
        elif 'date' in df.columns:
            df = df.rename(columns={'date': 'timestamp'})
        
        self.df = df
        print(f"   Got {len(df)} candles")
        return df
    
    def run(self, strategy_name: str = "sma") -> BacktestResult:
        """Run backtest with specified strategy"""
        if self.df is None or len(self.df) < 60:
            raise ValueError("Insufficient data. Call fetch_data() first.")
        
        strategy = get_strategy(strategy_name)
        df = self.df.copy()
        
        print(f"🔄 Running backtest: {strategy.name}...")
        
        # Store strategy name for plotting
        self.last_strategy_name = strategy.name
        
        # Calculate signals for entire period
        signals = []
        for i in range(60, len(df)):
            window = df.iloc[:i+1].copy()
            signal = strategy.analyze(window)
            sig_value = signal.signal.value
            
            # Long Only mode: convert SHORT (-1) to NEUTRAL (0)
            if self.mode == "long_only" and sig_value == -1:
                sig_value = 0
            
            signals.append(sig_value)
        
        # Pad beginning with neutral
        signals = [0] * 60 + signals
        df['signal'] = signals
        
        # Detect trades (signal changes)
        df['trade'] = df['signal'].diff().fillna(0)
        
        # Calculate returns (apply leverage multiplier)
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['signal'].shift(1) * df['returns'] * self.leverage
        
        # Calculate cumulative returns
        df['cum_returns'] = (1 + df['returns']).cumprod()
        df['cum_strategy'] = (1 + df['strategy_returns']).cumprod()
        
        # Portfolio value
        df['portfolio_value'] = self.initial_capital * df['cum_strategy']
        df['hold_value'] = self.initial_capital * df['cum_returns']
        
        # Calculate metrics
        final_value = df['portfolio_value'].iloc[-1]
        hold_final = df['hold_value'].iloc[-1]
        
        total_return = ((final_value / self.initial_capital) - 1) * 100
        hold_return = ((hold_final / self.initial_capital) - 1) * 100
        
        # Trade analysis
        trade_points = df[df['trade'] != 0]
        total_trades = len(trade_points)
        
        # Win/loss calculation
        trade_returns = []
        for i in range(1, len(trade_points)):
            start_idx = trade_points.index[i-1]
            end_idx = trade_points.index[i]
            period_return = df.loc[start_idx:end_idx, 'strategy_returns'].sum()
            trade_returns.append(period_return)
        
        winning = sum(1 for r in trade_returns if r > 0)
        losing = sum(1 for r in trade_returns if r < 0)
        win_rate = (winning / len(trade_returns) * 100) if trade_returns else 0
        
        # Max drawdown
        rolling_max = df['portfolio_value'].cummax()
        drawdown = (df['portfolio_value'] - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        
        # Sharpe ratio (annualized, assuming hourly data)
        hourly_returns = df['strategy_returns'].dropna()
        if len(hourly_returns) > 0 and hourly_returns.std() > 0:
            sharpe = (hourly_returns.mean() / hourly_returns.std()) * np.sqrt(24 * 365)
        else:
            sharpe = 0
        
        # Profit factor
        gross_profit = sum(r for r in trade_returns if r > 0)
        gross_loss = abs(sum(r for r in trade_returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Average trade return
        avg_trade = np.mean(trade_returns) * 100 if trade_returns else 0
        
        # Store results
        self.results_df = df
        self.trade_points = trade_points
        
        return BacktestResult(
            strategy_name=strategy.name,
            start_date=df['timestamp'].iloc[0].strftime('%Y-%m-%d'),
            end_date=df['timestamp'].iloc[-1].strftime('%Y-%m-%d'),
            initial_capital=self.initial_capital,
            final_value=final_value,
            total_return_pct=total_return,
            buy_hold_return_pct=hold_return,
            outperformance_pct=total_return - hold_return,
            total_trades=total_trades,
            winning_trades=winning,
            losing_trades=losing,
            win_rate_pct=win_rate,
            max_drawdown_pct=max_drawdown,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor if profit_factor != float('inf') else 99.99,
            avg_trade_return_pct=avg_trade
        )
    
    def plot(self, save_path: Optional[str] = None, show: bool = True):
        """Generate backtest visualization"""
        if self.results_df is None:
            raise ValueError("No results to plot. Run backtest first.")
        
        df = self.results_df
        
        # Build descriptive title with mode and leverage
        if self.mode == "long_only":
            mode_label = "[Long Only]"
        else:
            mode_label = f"[Leveraged {self.leverage:.0f}x Short]" if self.leverage > 1 else "[Leveraged Short]"
        asset = self.symbol.replace("-USD", "")
        strategy_name = self.last_strategy_name.replace("_", " ").title()
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        fig.suptitle(f'{asset} - {strategy_name} ({mode_label})', fontsize=16, fontweight='bold')
        
        # Plot 1: Price with Buy/Sell signals
        ax1 = axes[0]
        ax1.plot(df['timestamp'], df['close'], label='Price', linewidth=1.5, color='#333')
        
        # Buy signals (going long)
        buys = df[df['trade'] > 0]
        ax1.scatter(buys['timestamp'], buys['close'], marker='^', s=150, 
                   c='green', label=f'BUY ({len(buys)})', zorder=5, edgecolors='darkgreen')
        
        # Sell signals (going short)
        sells = df[df['trade'] < 0]
        ax1.scatter(sells['timestamp'], sells['close'], marker='v', s=150,
                   c='red', label=f'SELL ({len(sells)})', zorder=5, edgecolors='darkred')
        
        ax1.set_title('Price Chart with Trading Signals', fontsize=12)
        ax1.set_ylabel('Price ($)')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Plot 2: Portfolio Value
        ax2 = axes[1]
        ax2.plot(df['timestamp'], df['portfolio_value'], label='Strategy', linewidth=2, color='blue')
        ax2.plot(df['timestamp'], df['hold_value'], label='Buy & Hold', linewidth=2, color='gray', linestyle='--')
        ax2.axhline(y=self.initial_capital, color='black', linestyle='-', alpha=0.3)
        
        # Fill profit/loss areas
        ax2.fill_between(df['timestamp'], self.initial_capital, df['portfolio_value'],
                        where=(df['portfolio_value'] > self.initial_capital),
                        alpha=0.3, color='green', label='Profit')
        ax2.fill_between(df['timestamp'], self.initial_capital, df['portfolio_value'],
                        where=(df['portfolio_value'] < self.initial_capital),
                        alpha=0.3, color='red', label='Loss')
        
        final_strat = df['portfolio_value'].iloc[-1]
        final_hold = df['hold_value'].iloc[-1]
        ax2.set_title(f'Portfolio Value: Strategy ${final_strat:,.2f} vs Hold ${final_hold:,.2f}', fontsize=12)
        ax2.set_ylabel('Value ($)')
        ax2.legend(loc='upper left')
        ax2.grid(True, alpha=0.3)
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
        
        # Plot 3: Drawdown
        ax3 = axes[2]
        rolling_max = df['portfolio_value'].cummax()
        drawdown = (df['portfolio_value'] - rolling_max) / rolling_max * 100
        
        ax3.fill_between(df['timestamp'], 0, drawdown, alpha=0.5, color='red')
        ax3.plot(df['timestamp'], drawdown, color='darkred', linewidth=1)
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        max_dd = drawdown.min()
        ax3.set_title(f'Drawdown (Max: {max_dd:.2f}%)', fontsize=12)
        ax3.set_ylabel('Drawdown %')
        ax3.set_xlabel('Date')
        ax3.grid(True, alpha=0.3)
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.0f}%'))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
            print(f"📊 Plot saved to: {save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def compare_strategies(self, strategies: list = None) -> pd.DataFrame:
        """Compare multiple strategies"""
        if strategies is None:
            strategies = ['sma', 'macd', 'combined']
        
        results = []
        for strat in strategies:
            result = self.run(strat)
            results.append({
                'Strategy': result.strategy_name,
                'Return %': f"{result.total_return_pct:+.2f}%",
                'vs Hold': f"{result.outperformance_pct:+.2f}%",
                'Trades': result.total_trades,
                'Win Rate': f"{result.win_rate_pct:.1f}%",
                'Max DD': f"{result.max_drawdown_pct:.2f}%",
                'Sharpe': f"{result.sharpe_ratio:.2f}"
            })
        
        return pd.DataFrame(results)


def main():
    """CLI entry point for backtesting"""
    parser = argparse.ArgumentParser(description="Backtest trading strategies")
    parser.add_argument("--strategy", default="sma", choices=["sma", "macd", "combined", "all"],
                       help="Strategy to test (default: sma)")
    parser.add_argument("--pair", default="BTC-USD", help="Trading pair (default: BTC-USD)")
    parser.add_argument("--days", type=int, default=30, help="Days of history (default: 30)")
    parser.add_argument("--capital", type=float, default=100, help="Initial capital (default: 100)")
    parser.add_argument("--plot", action="store_true", help="Show plot")
    parser.add_argument("--save", type=str, help="Save plot to file")
    args = parser.parse_args()
    
    # Create backtester
    bt = Backtester(symbol=args.pair, initial_capital=args.capital)
    bt.fetch_data(days=args.days)
    
    if args.strategy == "all":
        # Compare all strategies
        print("\n📊 Comparing all strategies...\n")
        comparison = bt.compare_strategies()
        print(comparison.to_string(index=False))
        print()
    else:
        # Run single strategy
        result = bt.run(args.strategy)
        print(result)
        
        if args.plot or args.save:
            bt.plot(save_path=args.save, show=args.plot)


if __name__ == "__main__":
    main()
