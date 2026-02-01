"""Coinbase Advanced Trade API Client"""

import json
import time
import jwt
import requests
from typing import Optional
from cryptography.hazmat.primitives import serialization


class CoinbaseClient:
    """Client for Coinbase Advanced Trade API"""
    
    BASE_URL = "https://api.coinbase.com"
    
    def __init__(self, api_key_name: str, api_key_secret: str):
        self.api_key_name = api_key_name
        self.private_key = serialization.load_pem_private_key(
            api_key_secret.encode(), password=None
        )
    
    def _generate_jwt(self, method: str, path: str) -> str:
        """Generate JWT for API authentication"""
        uri = f"{method} api.coinbase.com{path}"
        now = int(time.time())
        payload = {
            "sub": self.api_key_name,
            "iss": "cdp",
            "nbf": now,
            "exp": now + 120,
            "uris": [uri]
        }
        headers = {
            "alg": "ES256",
            "kid": self.api_key_name,
            "nonce": str(int(time.time() * 1000000)),
            "typ": "JWT"
        }
        return jwt.encode(payload, self.private_key, algorithm="ES256", headers=headers)
    
    def _request(self, method: str, path: str, body: dict = None) -> dict:
        """Make authenticated API request"""
        token = self._generate_jwt(method, path)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.BASE_URL}{path}"
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=body, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code >= 400:
            raise Exception(f"API Error {response.status_code}: {response.text}")
        
        return response.json() if response.text else {}
    
    def get_accounts(self) -> list:
        """Get all accounts with balances"""
        result = self._request("GET", "/api/v3/brokerage/accounts")
        return result.get("accounts", [])
    
    def get_balance(self, currency: str) -> float:
        """Get balance for specific currency"""
        accounts = self.get_accounts()
        for acc in accounts:
            if acc.get("currency") == currency:
                return float(acc.get("available_balance", {}).get("value", 0))
        return 0.0
    
    def get_product(self, product_id: str) -> dict:
        """Get product details including current price"""
        return self._request("GET", f"/api/v3/brokerage/products/{product_id}")
    
    def get_price(self, product_id: str) -> float:
        """Get current price for a trading pair"""
        product = self.get_product(product_id)
        return float(product.get("price", 0))
    
    def get_candles(self, product_id: str, granularity: int = 3600, limit: int = 100) -> list:
        """Get historical candles"""
        path = f"/api/v3/brokerage/products/{product_id}/candles?granularity={granularity}&limit={limit}"
        result = self._request("GET", path)
        return result.get("candles", [])
    
    def create_order(
        self,
        product_id: str,
        side: str,  # "BUY" or "SELL"
        size: Optional[str] = None,
        quote_size: Optional[str] = None,
        client_order_id: Optional[str] = None
    ) -> dict:
        """Create a market order"""
        import uuid
        
        order = {
            "client_order_id": client_order_id or str(uuid.uuid4()),
            "product_id": product_id,
            "side": side,
            "order_configuration": {
                "market_market_ioc": {}
            }
        }
        
        if quote_size:  # Buy with USD amount
            order["order_configuration"]["market_market_ioc"]["quote_size"] = quote_size
        elif size:  # Buy/sell specific amount
            order["order_configuration"]["market_market_ioc"]["base_size"] = size
        
        return self._request("POST", "/api/v3/brokerage/orders", order)
    
    def buy(self, product_id: str, usd_amount: float) -> dict:
        """Buy crypto with USD amount"""
        return self.create_order(
            product_id=product_id,
            side="BUY",
            quote_size=str(usd_amount)
        )
    
    def sell(self, product_id: str, crypto_amount: float) -> dict:
        """Sell crypto amount"""
        return self.create_order(
            product_id=product_id,
            side="SELL",
            size=str(crypto_amount)
        )
    
    def get_orders(self, product_id: str = None, status: str = None) -> list:
        """Get orders"""
        path = "/api/v3/brokerage/orders/historical/batch"
        if product_id:
            path += f"?product_id={product_id}"
        result = self._request("GET", path)
        return result.get("orders", [])
