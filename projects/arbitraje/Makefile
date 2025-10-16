PY=poetry run python

.PHONY: diag collect-logs

diag:
	cd projects/arbitraje && poetry install && poetry run python scripts/diagnose_ticker_fetch.py --no-sim

collect-logs:
	# Collect arbitraje logs into artifacts/arbitraje/logs (non-destructive copy)
	python projects/arbitraje/scripts/collect_logs.py

canonicalize:
	# Create canonical copies of logs and tests for CI/docs
	cd projects/arbitraje && poetry run python scripts/create_canonical_copies.py

diag-canonical:
	# Create canonical copies (if any) and run the canonical test + diagnostics
	cd projects/arbitraje && set -e; \
		poetry install --no-interaction --no-ansi; \
		poetry run python scripts/create_canonical_copies.py; \
		if [ -f canonical/tests/test_connector_fetch.py ]; then \
			poetry run python canonical/tests/test_connector_fetch.py; \
		else \
			echo "ERROR: canonical/tests/test_connector_fetch.py missing. Run 'make canonicalize' or ensure canonical files are present."; \
			exit 1; \
		fi; \
		poetry run python scripts/diagnose_ticker_fetch.py --no-sim
