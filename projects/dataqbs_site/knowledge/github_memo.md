# memo — Trading & Monitoring Tools

Carlos Carrillo's personal trading tools repository at dataqbs, including grid trading bots, cross-exchange arbitrage radar, and portfolio monitoring.

## Projects

### MEMO-GRID v7.0.0 — Grid Trading ETH/BTC
- Maker-only grid trading bot for ETH/BTC on Binance Spot via ccxt
- Optimized via Optuna HPO with 50,000 trials (TPE sampler)
- Optimal parameters: step_pct=5.5%, levels=1, recenter_threshold=6%
- Backtest engine covering 2017–2026 with real maker fee modeling
- 22 analysis tools including attribution analysis, Monte Carlo projections, volatility analysis
- FIFO inventory tracking with persistent state
- 33 unit tests with full coverage
- Attribution analysis: decomposes returns into alpha (grid strategy) vs beta (market movement)
- Yearly P&L breakdown with per-year cycle counting

Key formula: E[Gain] ≈ Volatility × Cycle Frequency × (Step% - Fees%)
- ETH/BTC annual volatility: 55%
- Binance maker fees: 0.1%
- Result from backtest: +5.11 BTC gained from 0.23 BTC initial

### MEMO-GRID-RADAR — Grid Trading Microservice
- Production-ready grid bot microservice
- Supports multiple exchanges: Binance Spot primary
- Maker-only orders with LIMIT_MAKER when supported
- Adaptive step sizing based on fee pressure
- Volatility spike pause protection
- FIFO PnL reconciliation
- Linux deployment: systemd support, Azure VM compatible
- Consolidation tool for small holdings cleanup

### arbextra — Cross-Exchange Arbitrage Radar
- Scans BTC/USDT across multiple exchanges via ccxt
- Computes gross/net spreads with configurable thresholds
- Auto-triggered mirrored taker orders (dry-run/live modes)
- Portfolio PnL tracker for all assets valued in USDT
- Token baselines tracking: tokens_inicial, tokens_actual, tokens_profit
- Rebalance percentage feature with safety clamping (0–100%)
- CSV reports: spreads, suggestions, outcomes, portfolio summary

## Technologies
- Python, ccxt, pandas, NumPy
- Optuna (HPO), PyYAML, pytest
- Binance API, multiple exchange APIs
- systemd (Linux deployment)
- PyInstaller (standalone executable)

## GitHub Repository
https://github.com/CarlosCaPe/memo
