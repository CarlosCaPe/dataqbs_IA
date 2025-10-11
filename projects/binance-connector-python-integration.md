# Binance Connector (Python) – Integration Notes

This repository was cloned into `projects/binance-connector-python`.

What it is:
- A collection of auto‑generated Python SDKs for Binance product families (Spot, Wallet, Convert, Staking, Sub‑accounts, Futures, etc.).
- Each product is a separate Poetry package under `clients/<product>` with its own `pyproject.toml`.
- A shared core `binance-common` package under `common/` used across clients.

How to use (quick start):
- For Spot (REST):
  - Install the SDK (either using `pip` or `poetry`):
    - `pip install binance-sdk-spot`
    - or add to Poetry: `poetry add binance-sdk-spot`
  - Example snippet:
    ```python
    import logging
    from binance_common.configuration import ConfigurationRestAPI
    from binance_common.constants import SPOT_REST_API_PROD_URL
    from binance_sdk_spot.spot import Spot

    logging.basicConfig(level=logging.INFO)
    cfg = ConfigurationRestAPI(api_key="<API_KEY>", api_secret="<API_SECRET>", base_path=SPOT_REST_API_PROD_URL)
    client = Spot(config_rest_api=cfg)
    resp = client.rest_api.exchange_info(symbol="BNBUSDT")
    print(resp.data())
    ```

- For Convert (list pairs):
  ```python
  import os, logging
  from binance_sdk_convert.convert import Convert, ConfigurationRestAPI, CONVERT_REST_API_PROD_URL
  logging.basicConfig(level=logging.INFO)
  cfg = ConfigurationRestAPI(api_key=os.getenv("API_KEY", ""), api_secret=os.getenv("API_SECRET", ""), base_path=CONVERT_REST_API_PROD_URL)
  client = Convert(config_rest_api=cfg)
  print(client.rest_api.list_all_convert_pairs().data())
  ```

Notes for this repo (dataqbs_IA):
- The arbitraje project already includes a native Binance REST client for a few endpoints. You can optionally switch to this official SDK for stronger typing and more endpoints.
- If you prefer to vendor only a subset, you can install just the packages you need (e.g., `binance-sdk-spot`, `binance-sdk-wallet`, `binance-sdk-convert`). No need to install the whole monorepo.

Where to look:
- Top‑level README: `projects/binance-connector-python/README.md`
- Spot client docs and examples: `projects/binance-connector-python/clients/spot/README.md` and `examples/`
- Convert examples (REST): `projects/binance-connector-python/clients/convert/examples/rest_api/`
- Common utilities (configuration, constants, signing): `projects/binance-connector-python/common/src/binance_common/`

Compatibility tips with arbitraje:
- You can replace ccxt calls with Spot client endpoints for market data where helpful. Beware of rate limits; use the SDK’s retry/backoff options.
- For balances, the Wallet client and Spot REST (/api/v3/account) are available; configure API keys and consider recvWindow/clock skew.
- For WebSocket market streams, use `clients/spot` WebSocket Streams module.

Troubleshooting on Windows:
- If you see "Filename too long" during clone, we already enabled `git config core.longpaths true` in this repo.
- Python version constraint is ">=3.9,<3.14" for most clients.
