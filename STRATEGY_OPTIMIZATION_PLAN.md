# Trading Strategy Optimization Plan
**Created:** 2026-02-01  
**Owner:** Abel (autonomous optimization)  
**Goal:** Find the most profitable and reliable trading strategy

---

## 🎯 Primary Objectives (Priority Order)

### 1. PROFITABILITY (Most Important)
- **Target:** Maximize annual returns with realistic fee modeling
- **Minimum viable:** >100% annual return after fees
- **Stretch goal:** 500%+ annual return after fees
- **Dream goal:** 1000%+ annual return after fees

### 2. RELIABILITY (Critical)
- **Consistency:** Strategy should work across multiple time periods
- **Drawdown limit:** Max drawdown <60% preferred, <80% acceptable
- **Win rate:** Track win/loss ratio for confidence
- **Robustness:** Should work on at least 2-3 assets, not just one

### 3. LOW TRADE FREQUENCY (Important)
- **Fewer trades = better** (reduces fee drag, slippage, stress)
- **Target:** <50 trades per year ideal
- **Acceptable:** <100 trades per year
- **Avoid:** >200 trades per year (fee death spiral)

---

## 📊 Evaluation Criteria

Every strategy MUST be evaluated with:

| Metric | Weight | Notes |
|--------|--------|-------|
| **Net Return (after fees)** | 40% | Use 0.2% round-trip fee assumption |
| **Max Drawdown** | 25% | Lower is better; >80% is disqualifying |
| **Trade Count** | 15% | Fewer is better |
| **Sharpe Ratio** | 10% | Risk-adjusted returns |
| **Multi-Asset Validity** | 10% | Works on >1 asset |

### Fee Assumptions
- **Trading fee:** 0.1% per trade (entry or exit)
- **Slippage:** 0.1% per trade
- **Total round-trip:** 0.4% (0.2% in + 0.2% out)
- **Always include fees in reported returns**

---

## 🚫 Constraints & Rules

### Hard Rules (Never Break)
1. **Always include fees** - No theoretical-only returns
2. **Test on 1-year minimum** - No cherry-picked periods
3. **Report max drawdown** - No hiding the pain
4. **Log all findings** - Even failures teach us

### Soft Rules (Prefer but flexible)
1. Prefer simple strategies over complex ones
2. Prefer strategies that work on multiple assets
3. Prefer strategies with clear entry/exit rules
4. Avoid over-optimization (curve fitting)

---

## 🔬 Testing Protocol

### For Each Strategy Variant:

```python
# Standard test parameters
ASSETS = ['ETH', 'BTC', 'SOL', 'XRP', 'DOGE']  # Test on top 5
PERIOD = '1y'  # 1 year minimum
FEE_PCT = 0.002  # 0.2% per trade
LEVERAGE_OPTIONS = [1, 2, 3]  # Test multiple leverage levels
```

### Required Output:
```
Strategy: [NAME]
Asset: [ASSET]
Period: [START] to [END]
Leverage: [Xx]

Results (WITH FEES):
- Return: +XX.X%
- Max Drawdown: -XX.X%
- Total Trades: XX
- Sharpe Ratio: X.XX

Verdict: [PASS/FAIL/PROMISING]
```

---

## 📈 Current Leaderboard

| Rank | Strategy | Asset | Leverage | Return | Drawdown | Trades |
|------|----------|-------|----------|--------|----------|--------|
| 1 | 30-day Breakout | ETH | 3x | +133% | -58% | 6 |
| 2 | 30-day Breakout | ETH | 2x | +104% | -44% | 6 |
| 3 | 30-day Breakout | ETH | 1x | +56% | -27% | 6 |

*Updated: 2026-02-01 07:00*

---

## 🔄 Optimization Areas to Explore

### Phase 1: Breakout Variations (Current)
- [ ] Test 20-day, 40-day, 50-day channels
- [ ] Test on other assets (BTC, SOL)
- [ ] Add trailing stop to lock gains
- [ ] Test ATR-based channel width

### Phase 2: Trend Following
- [ ] Moving average variations (EMA vs SMA)
- [ ] Longer-period crossovers (50/200)
- [ ] ADX trend strength filter
- [ ] Momentum confirmation

### Phase 3: Hybrid Strategies
- [ ] Breakout + trend confirmation
- [ ] Multi-timeframe analysis
- [ ] Volatility-adjusted position sizing
- [ ] Asset rotation based on momentum

### Phase 4: Advanced
- [ ] Machine learning signal generation
- [ ] Sentiment analysis integration
- [ ] On-chain metrics (if available)
- [ ] Correlation-based hedging

---

## 📝 Logging Requirements

Every optimization session must log to `memory/activity.log`:

```
[YYYY-MM-DD HH:MM] STRATEGY | [brief finding]
```

Examples:
- `[2026-02-01 09:00] STRATEGY | Tested 20-day breakout on ETH - +98% (worse than 30-day)`
- `[2026-02-01 10:00] STRATEGY | Found: 40-day breakout @ 3x = +156% - NEW LEADER!`

---

## 🚨 Alert Conditions

**Immediately notify Cary via Telegram if:**
- Strategy found with >200% return after fees
- Strategy works on 3+ assets with >100% each
- Major insight about market behavior
- Strategy failure that invalidates current approach

---

## 📊 Dashboard Integration (REQUIRED)

### Mission Control Backtesting Page
**URL:** https://mission-control-board.fly.dev/trade (Backtest tab)

All optimization results MUST be synced to the dashboard:

1. **Backtest Charts** - Generate PNG plots for each strategy tested
   - Save to `backtest_results/[timeframe]/[ASSET]_[STRATEGY]_backtest.png`
   - Include: price chart, signals, equity curve, key metrics

2. **Summary CSV** - Update CSV with all backtest results
   - `backtest_results/[timeframe]/backtest_summary_[timeframe].csv`
   - Columns: asset, strategy, return_pct, hold_pct, trades, max_dd, sharpe

3. **Sync to Dashboard** - Push data to Mission Control API
   - Run: `python sync_to_mission_control.py`
   - Endpoint: POST /api/trader with backtest data
   - Include timeframe data (1mo, 6mo, 1yr)

4. **Leaderboard Update** - Keep Top 5 strategies visible
   - Dashboard shows best performers per timeframe
   - Auto-updates when new results synced

### Dashboard Data Requirements
```json
{
  "backtests": {
    "1mo": [...results...],
    "6mo": [...results...],
    "1yr": [...results...]
  },
  "leaderboard": {
    "1mo": [top 5],
    "6mo": [top 5],
    "1yr": [top 5]
  },
  "charts": {
    "available": ["ETH_SMA", "ETH_MACD", ...]
  }
}
```

### After Each Optimization Session:
- [ ] Generate backtest plots for new strategies
- [ ] Update summary CSVs
- [ ] Run sync script to push to dashboard
- [ ] Verify data appears on Mission Control

---

## 📚 Reference Files

- `OPTIMIZATION_RESULTS.md` - Detailed technical findings
- `MORNING_BRIEFING.md` - Summary for Cary
- `trader/strategies.py` - Implemented strategies
- `strategy_optimizer.py` - Optimization scripts
- `sync_to_mission_control.py` - Dashboard sync script

---

*This document guides all autonomous optimization work. Update leaderboard when new leaders found. Keep dashboard current!*
