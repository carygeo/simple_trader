#!/usr/bin/env python3
"""
Kraken Bot - Leveraged + Short Trading

Run with: python run.py [--live]
"""

import os
import sys
import json
import yaml
import time
import logging
from datetime import datetime
from pathlib import Path

# Add parent to path for shared modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from trader.kraken import KrakenClient
from trader.kraken_strategy import KrakenSMAStrategy

# Load config
CONFIG_PATH = Path(__file__).parent / "config.yaml"
STATE_PATH = Path(__file__).parent / "state.json"
LOG_DIR = Path(__file__).parent / "logs"

LOG_DIR.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "trader.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH) as f:
            return json.load(f)
    return {
        "position": "NONE",  # LONG, SHORT, NONE
        "entry_price": 0,
        "quantity": 0,
        "leverage": 1,
        "last_signal": None,
        "unrealized_pnl": 0,
        "trades": []
    }


def save_state(state):
    state["updated_at"] = datetime.utcnow().isoformat()
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def main():
    config = load_config()
    state = load_state()
    
    logger.info("=" * 60)
    logger.info(f"🤖 {config['name']} Starting")
    logger.info(f"   Exchange: {config['exchange']}")
    logger.info(f"   Mode: {config['mode']}")
    logger.info(f"   Strategy: {config['strategy']['name']}")
    logger.info(f"   Leverage: {config['trading']['leverage']}x")
    logger.info(f"   Pairs: {config['trading']['pairs']}")
    logger.info(f"   Dry Run: {config['dry_run']}")
    logger.info("=" * 60)
    
    # Initialize client
    api_key = os.getenv("KRAKEN_API_KEY")
    api_secret = os.getenv("KRAKEN_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("Missing KRAKEN_API_KEY or KRAKEN_API_SECRET")
        sys.exit(1)
    
    client = KrakenClient()
    strategy = KrakenSMAStrategy(
        leverage=config['trading']['leverage'],
        allow_short=config['trading']['allow_short']
    )
    
    # Main loop
    while True:
        try:
            for pair in config['trading']['pairs']:
                # Get current price and data
                # ... trading logic here
                pass
            
            save_state(state)
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            save_state(state)
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    main()
