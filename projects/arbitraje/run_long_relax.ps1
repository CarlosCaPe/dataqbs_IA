# Wrapper script to start a long relax run (repeat=1000)
# Place this file in projects/arbitraje and run with pwsh -NoProfile -File .\run_long_relax.ps1

Set-StrictMode -Version Latest

# Ensure script runs from its directory
Set-Location -Path $PSScriptRoot

# Clear common exchange API env vars to avoid blocking network balance calls
Remove-Item -ErrorAction SilentlyContinue Env:BINANCE_API_KEY,Env:BINANCE_API_SECRET,Env:OKX_API_KEY,Env:OKX_SECRET,Env:BITGET_API_KEY,Env:BITGET_SECRET,Env:MEXC_API_KEY,Env:MEXC_SECRET

# Set desired log level
$env:ARBITRAJE_LOG_LEVEL = 'INFO'

Write-Output "Starting long relax run (repeat=1000) in $PWD"
Write-Output "ARBITRAJE_LOG_LEVEL=$env:ARBITRAJE_LOG_LEVEL"

# Run the Python runner via poetry
poetry run python -m arbitraje.arbitrage_report_ccxt --config .\arbitraje.relax_diag.yaml --repeat 1000 --repeat_sleep 0 --no_console_clear
