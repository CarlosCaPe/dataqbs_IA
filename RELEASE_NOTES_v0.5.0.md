# v0.5.0 — killer

- Swapper: amount_in now reflects actual wallet free balance for first hop.
- Removed internal min-amount/min-cost checks; let the exchange enforce limits and errors.
- Live orders avoid derived prices. For Binance inverted buys, send quoteOrderQty equal to wallet spend and amount=None.
- Post-order amount_out based on refreshed wallet balance (more truthful than local estimates).
- Minor fixes: import os in swapper, safer error reporting and fills list.

How to update:
- In `projects/arbitraje`, run `poetry install` if environment changed.
- Use `swapper` as before. Dry-run still estimates with ticker; live paths now depend solely on wallet and exchange.
