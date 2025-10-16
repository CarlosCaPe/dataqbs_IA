PY=poetry run python

.PHONY: diag collect-logs

diag:
	cd projects/arbitraje && poetry install && poetry run python scripts/diagnose_ticker_fetch.py --no-sim

collect-logs:
	# Collect arbitraje logs into artifacts/arbitraje/logs (non-destructive copy)
	python projects/arbitraje/scripts/collect_logs.py
