"""
Kraken Exchange Client

Supports:
- Spot trading
- Margin trading (leverage up to 5x)
- Short selling
- Futures trading

API Docs: https://docs.kraken.com/rest/
"""

import os
import time
import hmac
import base64
import hashlib
import urllib.parse
from typing import Optional, Dict, List
import requests
from dotenv import load_dotenv

load_dotenv()


class KrakenClient:
    """Kraken Exchange API Client"""
    
    BASE_URL = "https://api.kraken.com"
    
    # Asset pair mappings (Kraken uses different names)
    PAIR_MAP = {
        "BTC-USD": "XXBTZUSD",
        "ETH-USD": "XETHZUSD",
        "SOL-USD": "SOLUSD",
        "DOGE-USD": "XDGUSD",
        "XRP-USD": "XXRPZUSD",
        "ADA-USD": "ADAUSD",
        "AVAX-USD": "AVAXUSD",
        "DOT-USD": "DOTUSD",
        "LINK-USD": "LINKUSD",
        "LTC-USD": "XLTCZUSD",
        "ATOM-USD": "ATOMUSD",
        "NEAR-USD": "NEARUSD",
    }
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or os.getenv("KRAKEN_API_KEY")
        self.api_secret = api_secret or os.getenv("KRAKEN_PRIVATE_KEY")
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Kraken API credentials not configured")
    
    def _get_signature(self, url_path: str, data: dict, nonce: str) -> str:
        """Generate API signature"""
        post_data = urllib.parse.urlencode(data)
        encoded = (str(nonce) + post_data).encode()
        message = url_path.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _request(self, endpoint: str, data: dict = None, private: bool = False) -> dict:
        """Make API request"""
        url = f"{self.BASE_URL}{endpoint}"
        
        if private:
            if data is None:
                data = {}
            
            nonce = str(int(time.time() * 1000))
            data["nonce"] = nonce
            
            headers = {
                "API-Key": self.api_key,
                "API-Sign": self._get_signature(endpoint, data, nonce),
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = requests.post(url, headers=headers, data=data, timeout=30)
        else:
            response = requests.get(url, params=data, timeout=30)
        
        result = response.json()
        
        if result.get("error"):
            raise Exception(f"Kraken API error: {result['error']}")
        
        return result.get("result", {})
    
    # ==================== PUBLIC ENDPOINTS ====================
    
    def get_ticker(self, pair: str) -> dict:
        """Get ticker info for a pair"""
        kraken_pair = self.PAIR_MAP.get(pair, pair)
        return self._request("/0/public/Ticker", {"pair": kraken_pair})
    
    def get_ohlc(self, pair: str, interval: int = 60) -> dict:
        """Get OHLC data (interval in minutes)"""
        kraken_pair = self.PAIR_MAP.get(pair, pair)
        return self._request("/0/public/OHLC", {
            "pair": kraken_pair,
            "interval": interval
        })
    
    def get_order_book(self, pair: str, count: int = 10) -> dict:
        """Get order book"""
        kraken_pair = self.PAIR_MAP.get(pair, pair)
        return self._request("/0/public/Depth", {
            "pair": kraken_pair,
            "count": count
        })
    
    # ==================== PRIVATE ENDPOINTS ====================
    
    def get_balance(self) -> dict:
        """Get account balance"""
        return self._request("/0/private/Balance", private=True)
    
    def get_trade_balance(self, asset: str = "USD") -> dict:
        """Get trade balance (includes margin info)"""
        return self._request("/0/private/TradeBalance", {"asset": asset}, private=True)
    
    def get_open_orders(self) -> dict:
        """Get open orders"""
        return self._request("/0/private/OpenOrders", private=True)
    
    def get_open_positions(self) -> dict:
        """Get open margin positions"""
        return self._request("/0/private/OpenPositions", private=True)
    
    # ==================== TRADING ====================
    
    def place_order(
        self,
        pair: str,
        side: str,  # "buy" or "sell"
        order_type: str,  # "market" or "limit"
        volume: float,
        price: float = None,
        leverage: int = None,  # 2, 3, 4, or 5
        reduce_only: bool = False,
        validate: bool = False  # Validate only, don't execute
    ) -> dict:
        """
        Place an order
        
        Args:
            pair: Trading pair (e.g., "BTC-USD")
            side: "buy" or "sell"
            order_type: "market" or "limit"
            volume: Order size
            price: Price for limit orders
            leverage: Leverage multiplier (2-5x for margin)
            reduce_only: Only reduce existing position
            validate: Validate order without executing
        
        Returns:
            Order result with txid
        """
        kraken_pair = self.PAIR_MAP.get(pair, pair)
        
        data = {
            "pair": kraken_pair,
            "type": side,
            "ordertype": order_type,
            "volume": str(volume),
        }
        
        if order_type == "limit" and price:
            data["price"] = str(price)
        
        if leverage:
            data["leverage"] = str(leverage)
        
        if reduce_only:
            data["reduce_only"] = "true"
        
        if validate:
            data["validate"] = "true"
        
        return self._request("/0/private/AddOrder", data, private=True)
    
    def cancel_order(self, txid: str) -> dict:
        """Cancel an order"""
        return self._request("/0/private/CancelOrder", {"txid": txid}, private=True)
    
    def cancel_all_orders(self) -> dict:
        """Cancel all open orders"""
        return self._request("/0/private/CancelAll", private=True)
    
    # ==================== MARGIN TRADING ====================
    
    def open_long(
        self,
        pair: str,
        volume: float,
        leverage: int = 3,
        order_type: str = "market"
    ) -> dict:
        """Open a leveraged long position"""
        return self.place_order(
            pair=pair,
            side="buy",
            order_type=order_type,
            volume=volume,
            leverage=leverage
        )
    
    def open_short(
        self,
        pair: str,
        volume: float,
        leverage: int = 3,
        order_type: str = "market"
    ) -> dict:
        """Open a leveraged short position (profit when price drops)"""
        return self.place_order(
            pair=pair,
            side="sell",
            order_type=order_type,
            volume=volume,
            leverage=leverage
        )
    
    def close_position(
        self,
        pair: str,
        volume: float,
        position_side: str,  # "long" or "short"
        leverage: int = 3
    ) -> dict:
        """Close a margin position"""
        # To close a long, we sell. To close a short, we buy.
        side = "sell" if position_side == "long" else "buy"
        
        return self.place_order(
            pair=pair,
            side=side,
            order_type="market",
            volume=volume,
            leverage=leverage,
            reduce_only=True
        )
    
    # ==================== HELPERS ====================
    
    def get_price(self, pair: str) -> float:
        """Get current price for a pair"""
        kraken_pair = self.PAIR_MAP.get(pair, pair)
        ticker = self.get_ticker(pair)
        
        # Kraken returns nested data
        for key, data in ticker.items():
            if "c" in data:  # c = last trade closed [price, lot volume]
                return float(data["c"][0])
        
        raise ValueError(f"Could not get price for {pair}")
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value in USD"""
        balance = self.get_trade_balance("ZUSD")
        return float(balance.get("eb", 0))  # eb = equivalent balance
    
    def get_margin_info(self) -> dict:
        """Get margin account info"""
        balance = self.get_trade_balance("ZUSD")
        return {
            "equity": float(balance.get("eb", 0)),
            "margin_used": float(balance.get("m", 0)),
            "margin_free": float(balance.get("mf", 0)),
            "margin_level": float(balance.get("ml", 0)) if balance.get("ml") else None,
            "unrealized_pnl": float(balance.get("n", 0))
        }


def test_connection():
    """Test Kraken API connection"""
    try:
        client = KrakenClient()
        
        # Test public endpoint
        ticker = client.get_ticker("BTC-USD")
        print(f"✅ Public API works - BTC ticker retrieved")
        
        # Test private endpoint
        balance = client.get_balance()
        print(f"✅ Private API works - Balance retrieved")
        print(f"   Balances: {balance}")
        
        # Test trade balance
        trade_bal = client.get_trade_balance()
        print(f"✅ Trade balance: {trade_bal}")
        
        return True
        
    except Exception as e:
        print(f"❌ Kraken connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
