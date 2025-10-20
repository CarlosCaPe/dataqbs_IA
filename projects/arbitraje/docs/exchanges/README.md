# Exchange API Setup

This folder documents how to configure API credentials per exchange and how our scanner uses them.

- We load environment variables from `.env` files automatically (both at repo root and `projects/arbitraje/.env`).
- For read-only operations (balances, scanning), we only need API keys with restricted permissions (no withdrawals, no trading).
- For future trading automation, trading permissions will be required. Start with IP whitelisting and lowest scopes.

Environment variable names we use:

- Binance: `BINANCE_API_KEY`, `BINANCE_API_SECRET`
- Bybit: `BYBIT_API_KEY`, `BYBIT_API_SECRET`
- Bitget: `BITGET_API_KEY`, `BITGET_API_SECRET`, `BITGET_PASSWORD`
- Coinbase Advanced: `COINBASE_API_KEY`, `COINBASE_API_SECRET`, `COINBASE_API_PASSWORD`

Placeholders for all are included in `projects/arbitraje/.env.example`.

See the per-exchange guides in this folder for details.
