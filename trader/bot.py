"""Simple Trader Bot - Main trading logic"""

import os
import time
import logging
from datetime import datetime
from typing import Optional
import pandas as pd

from .coinbase import CoinbaseClient
from .strategies import get_strategy, Signal, TradeSignal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimpleTrader:
    """Main trading bot"""
    
    def __init__(
        self,
        api_key_name: str,
        api_key_secret: str,
        strategy_name: str = "sma",
        trading_pair: str = "BTC-USDT",
        trade_amount_usd: float = 10.0,
        dry_run: bool = True
    ):
        self.client = CoinbaseClient(api_key_name, api_key_secret)
        self.strategy = get_strategy(strategy_name)
        self.trading_pair = trading_pair
        self.trade_amount_usd = trade_amount_usd
        self.dry_run = dry_run
        
        # Parse trading pair
        self.base_currency = trading_pair.split("-")[0]  # BTC
        self.quote_currency = trading_pair.split("-")[1]  # USDT
        
        # Track position
        self.current_position: Optional[Signal] = None
        self.entry_price: Optional[float] = None
        self.trades: list = []
        
        logger.info(f"🤖 SimpleTrader initialized")
        logger.info(f"   Strategy: {self.strategy.name}")
        logger.info(f"   Pair: {self.trading_pair}")
        logger.info(f"   Trade size: ${self.trade_amount_usd}")
        logger.info(f"   Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    
    def get_historical_data(self, limit: int = 100) -> pd.DataFrame:
        """Fetch historical price data using yfinance (more reliable)"""
        import yfinance as yf
        
        try:
            # Map trading pair to yfinance symbol
            symbol_map = {
                "BTC-USDT": "BTC-USD",
                "BTC-USD": "BTC-USD",
                "ETH-USDT": "ETH-USD",
                "ETH-USD": "ETH-USD",
            }
            yf_symbol = symbol_map.get(self.trading_pair, f"{self.base_currency}-USD")
            
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period="7d", interval="1h")
            
            if df.empty:
                logger.warning("No data returned from yfinance")
                return pd.DataFrame()
            
            df = df.reset_index()
            df.columns = [c.lower() for c in df.columns]
            df = df.rename(columns={'datetime': 'start', 'date': 'start'})
            
            # Ensure we have required columns
            if 'close' not in df.columns:
                logger.error("Missing 'close' column in data")
                return pd.DataFrame()
            
            return df.tail(limit)
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def get_balances(self) -> dict:
        """Get current balances"""
        balances = {}
        try:
            accounts = self.client.get_accounts()
            for acc in accounts:
                currency = acc.get("currency")
                balance = float(acc.get("available_balance", {}).get("value", 0))
                if balance > 0 or currency in [self.base_currency, self.quote_currency]:
                    balances[currency] = balance
        except Exception as e:
            logger.error(f"Error fetching balances: {e}")
        return balances
    
    def execute_trade(self, signal: TradeSignal) -> bool:
        """Execute a trade based on signal"""
        try:
            current_price = signal.price
            
            # Check if position change is needed
            if self.current_position == signal.signal:
                logger.info(f"Already in {signal.signal.name} position, no action needed")
                return False
            
            # Log the signal
            logger.info(f"📊 Signal: {signal.signal.name} | {signal.reason}")
            logger.info(f"   Confidence: {signal.confidence:.0%} | Price: ${current_price:,.2f}")
            
            if self.dry_run:
                logger.info(f"🔸 DRY RUN - Would execute {signal.signal.name}")
                self._record_trade(signal, dry_run=True)
                self.current_position = signal.signal
                self.entry_price = current_price
                return True
            
            # Execute real trade
            if signal.signal == Signal.LONG:
                # Close short if exists, go long
                if self.current_position == Signal.SHORT:
                    # Buy to close short (simplified - in spot we sell base)
                    pass
                
                # Buy
                logger.info(f"🟢 BUYING ${self.trade_amount_usd} of {self.base_currency}")
                result = self.client.buy(self.trading_pair, self.trade_amount_usd)
                logger.info(f"   Order result: {result.get('success', result)}")
                
            elif signal.signal == Signal.SHORT:
                # For spot trading, "short" means sell to USDT
                base_balance = self.get_balances().get(self.base_currency, 0)
                
                if base_balance > 0:
                    logger.info(f"🔴 SELLING {base_balance} {self.base_currency}")
                    result = self.client.sell(self.trading_pair, base_balance)
                    logger.info(f"   Order result: {result.get('success', result)}")
                else:
                    logger.info(f"🔴 SHORT signal but no {self.base_currency} to sell - holding USDT")
            
            self._record_trade(signal, dry_run=False)
            self.current_position = signal.signal
            self.entry_price = current_price
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    def _record_trade(self, signal: TradeSignal, dry_run: bool = True):
        """Record trade in history"""
        trade = {
            "timestamp": datetime.now().isoformat(),
            "signal": signal.signal.name,
            "price": signal.price,
            "strategy": signal.strategy,
            "reason": signal.reason,
            "confidence": signal.confidence,
            "dry_run": dry_run
        }
        self.trades.append(trade)
        
        # Save state and trade history for dashboard
        self._save_state()
        self._save_trade_history()
    
    def _save_state(self):
        """Save current state for dashboard"""
        import json
        state = {
            "position": self.current_position.name if self.current_position else "NONE",
            "entry_price": self.entry_price or 0,
            "trading_pair": self.trading_pair,
            "strategy": self.strategy.name,
            "dry_run": self.dry_run,
            "updated_at": datetime.now().isoformat()
        }
        state_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trader_state.json")
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _save_trade_history(self):
        """Save trade history for dashboard"""
        import json
        history_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trade_history.json")
        with open(history_path, 'w') as f:
            json.dump(self.trades[-100:], f, indent=2)  # Keep last 100 trades
    
    def analyze(self) -> Optional[TradeSignal]:
        """Analyze market and return signal"""
        df = self.get_historical_data(limit=100)
        
        if df.empty or len(df) < 60:
            logger.warning("Insufficient data for analysis")
            return None
        
        return self.strategy.analyze(df)
    
    def run_once(self) -> bool:
        """Run single analysis and trade cycle"""
        logger.info(f"\n{'='*50}")
        logger.info(f"🔍 Analyzing {self.trading_pair}...")
        
        # Get current balances
        balances = self.get_balances()
        logger.info(f"💰 Balances: {balances}")
        
        # Analyze market
        signal = self.analyze()
        
        if signal is None:
            logger.warning("No signal generated")
            return False
        
        # Execute trade if needed
        return self.execute_trade(signal)
    
    def run(self, interval_minutes: int = 5):
        """Run continuous trading loop"""
        logger.info(f"\n🚀 Starting trading bot (interval: {interval_minutes}m)")
        
        while True:
            try:
                self.run_once()
                
                # Wait for next cycle
                logger.info(f"⏰ Next analysis in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("\n⛔ Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def get_stats(self) -> dict:
        """Get trading statistics"""
        if not self.trades:
            return {"total_trades": 0}
        
        return {
            "total_trades": len(self.trades),
            "current_position": self.current_position.name if self.current_position else "NONE",
            "entry_price": self.entry_price,
            "last_trade": self.trades[-1] if self.trades else None
        }
