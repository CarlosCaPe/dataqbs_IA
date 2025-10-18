Set-StrictMode -Version Latest
Set-Location "$PSScriptRoot/.."
Write-Output "Starting relax run (repeat=1000)..."
poetry run python -m arbitraje.arbitrage_report_ccxt --config ./arbitraje.relax_diag.yaml --repeat 1000 --repeat_sleep 0
