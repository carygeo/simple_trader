"""
Kraken Leveraged Trading Strategy

Optimized for margin trading with shorting capability.
Based on backtest results from 30-day analysis.

Top Performers (3x Leverage, 30-day):
1. ADA SMA: +62.8% (Sharpe: 4.11)
2. DOGE SMA: +30.3% (Sharpe: 2.68)
3. BTC SMA: +24.6% (Sharpe: 3.30)
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass

from .kraken import KrakenClient
from .strategies import get_strategy, Signal
from .backtest import Backtester


@dataclass
class KrakenPosition:
    """Current position state"""
    pair: str
    side: str  # "long", "short", or "none"
    entry_price: float
    volume: float
    leverage: int
    unrealized_pnl: float


class KrakenLeveragedTrader:
    """
    Kraken margin trader with leveraged long/short capability.
    
    Features:
    - SMA crossover strategy (best performer)
    - 3x leverage (configurable)
    - Can profit from both up AND down moves
    - Risk management with position sizing
    """
    
    # Default settings based on backtest optimization
    DEFAULT_PAIRS = ["ADA-USD", "DOGE-USD", "BTC-USD"]  # Top performers
    DEFAULT_LEVERAGE = 3
    DEFAULT_STRATEGY = "sma"
    MAX_POSITION_PCT = 0.30  # Max 30% of portfolio per trade
    
    def __init__(
        self,
        pairs: list = None,
        leverage: int = None,
        strategy: str = None,
        dry_run: bool = True
    ):
        self.client = KrakenClient()
        self.pairs = pairs or self.DEFAULT_PAIRS
        self.leverage = leverage or self.DEFAULT_LEVERAGE
        self.strategy_name = strategy or self.DEFAULT_STRATEGY
        self.dry_run = dry_run  # If True, don't execute real trades
        
        self.strategy = get_strategy(self.strategy_name)
        self.state_file = os.path.join(os.path.dirname(__file__), "..", "kraken_state.json")
        self.positions: Dict[str, KrakenPosition] = {}
        
        self._load_state()
    
    def _load_state(self):
        """Load saved state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file) as f:
                    data = json.load(f)
                    for pair, pos in data.get("positions", {}).items():
                        self.positions[pair] = KrakenPosition(**pos)
        except Exception as e:
            print(f"Warning: Could not load state: {e}")
    
    def _save_state(self):
        """Save current state"""
        try:
            data = {
                "positions": {
                    pair: {
                        "pair": pos.pair,
                        "side": pos.side,
                        "entry_price": pos.entry_price,
                        "volume": pos.volume,
                        "leverage": pos.leverage,
                        "unrealized_pnl": pos.unrealized_pnl
                    }
                    for pair, pos in self.positions.items()
                },
                "last_update": datetime.now().isoformat()
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def get_signal(self, pair: str) -> Signal:
        """Get current signal for a pair"""
        # Use backtester to fetch data and analyze
        bt = Backtester(symbol=pair, mode="leveraged")
        bt.fetch_data(days=7)  # Last week of data
        
        # Run strategy analysis on latest data
        signal_result = self.strategy.analyze(bt.df)
        return signal_result.signal
    
    def calculate_position_size(self, pair: str) -> float:
        """Calculate position size based on portfolio value"""
        try:
            portfolio = self.client.get_portfolio_value()
            max_position = portfolio * self.MAX_POSITION_PCT
            
            # Get current price
            price = self.client.get_price(pair)
            
            # Calculate volume (in base asset)
            volume = max_position / price
            
            return volume
        except Exception as e:
            print(f"Error calculating position size: {e}")
            return 0.0
    
    def execute_signal(self, pair: str, signal: Signal) -> Optional[dict]:
        """
        Execute a trading signal
        
        Returns order result or None if no action taken
        """
        current_pos = self.positions.get(pair)
        current_side = current_pos.side if current_pos else "none"
        
        action = None
        
        # Determine action based on signal and current position
        if signal == Signal.LONG:
            if current_side == "short":
                action = "close_short_open_long"
            elif current_side == "none":
                action = "open_long"
            # If already long, hold
        
        elif signal == Signal.SHORT:
            if current_side == "long":
                action = "close_long_open_short"
            elif current_side == "none":
                action = "open_short"
            # If already short, hold
        
        elif signal == Signal.NEUTRAL:
            if current_side in ["long", "short"]:
                action = f"close_{current_side}"
        
        if not action:
            return None
        
        # Execute the action
        print(f"📊 {pair}: Signal={signal.name}, Action={action}")
        
        if self.dry_run:
            print(f"   [DRY RUN] Would execute: {action}")
            return {"action": action, "dry_run": True}
        
        try:
            price = self.client.get_price(pair)
            volume = self.calculate_position_size(pair)
            
            if "close" in action and current_pos:
                # Close existing position
                result = self.client.close_position(
                    pair=pair,
                    volume=current_pos.volume,
                    position_side=current_pos.side,
                    leverage=current_pos.leverage
                )
                print(f"   ✅ Closed {current_pos.side} position")
                del self.positions[pair]
            
            if "open_long" in action:
                result = self.client.open_long(
                    pair=pair,
                    volume=volume,
                    leverage=self.leverage
                )
                self.positions[pair] = KrakenPosition(
                    pair=pair,
                    side="long",
                    entry_price=price,
                    volume=volume,
                    leverage=self.leverage,
                    unrealized_pnl=0.0
                )
                print(f"   ✅ Opened LONG {volume:.6f} @ ${price:.2f} ({self.leverage}x)")
            
            elif "open_short" in action:
                result = self.client.open_short(
                    pair=pair,
                    volume=volume,
                    leverage=self.leverage
                )
                self.positions[pair] = KrakenPosition(
                    pair=pair,
                    side="short",
                    entry_price=price,
                    volume=volume,
                    leverage=self.leverage,
                    unrealized_pnl=0.0
                )
                print(f"   ✅ Opened SHORT {volume:.6f} @ ${price:.2f} ({self.leverage}x)")
            
            self._save_state()
            return result
            
        except Exception as e:
            print(f"   ❌ Error executing {action}: {e}")
            return None
    
    def run_cycle(self) -> dict:
        """
        Run one trading cycle for all pairs
        
        Returns summary of actions taken
        """
        print(f"\n{'='*60}")
        print(f"🔄 Kraken Leveraged Trader - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"   Strategy: {self.strategy_name.upper()} | Leverage: {self.leverage}x")
        print(f"   Pairs: {', '.join(self.pairs)}")
        print(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"{'='*60}\n")
        
        results = {}
        
        for pair in self.pairs:
            try:
                signal = self.get_signal(pair)
                result = self.execute_signal(pair, signal)
                results[pair] = {
                    "signal": signal.name,
                    "action": result
                }
            except Exception as e:
                print(f"❌ Error processing {pair}: {e}")
                results[pair] = {"error": str(e)}
        
        return results
    
    def get_status(self) -> dict:
        """Get current trading status"""
        try:
            margin_info = self.client.get_margin_info()
            positions = self.client.get_open_positions()
            
            return {
                "equity": margin_info["equity"],
                "margin_used": margin_info["margin_used"],
                "margin_free": margin_info["margin_free"],
                "unrealized_pnl": margin_info["unrealized_pnl"],
                "positions": positions,
                "local_positions": {
                    pair: {
                        "side": pos.side,
                        "entry_price": pos.entry_price,
                        "volume": pos.volume,
                        "leverage": pos.leverage
                    }
                    for pair, pos in self.positions.items()
                }
            }
        except Exception as e:
            return {"error": str(e)}


def main():
    """Run the Kraken trader"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kraken Leveraged Trader")
    parser.add_argument("--live", action="store_true", help="Execute real trades (default: dry run)")
    parser.add_argument("--leverage", type=int, default=3, help="Leverage multiplier (default: 3)")
    parser.add_argument("--pairs", nargs="+", default=None, help="Trading pairs")
    parser.add_argument("--status", action="store_true", help="Show current status")
    args = parser.parse_args()
    
    trader = KrakenLeveragedTrader(
        pairs=args.pairs,
        leverage=args.leverage,
        dry_run=not args.live
    )
    
    if args.status:
        status = trader.get_status()
        print(json.dumps(status, indent=2))
    else:
        results = trader.run_cycle()
        print("\n📋 Results:")
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
