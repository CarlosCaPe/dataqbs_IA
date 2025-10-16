$vars = @('BINANCE_API_KEY','BINANCE_API_SECRET','BYBIT_API_KEY','BYBIT_API_SECRET','OKX_API_KEY','OKX_API_SECRET','KUCOIN_API_KEY','KUCOIN_API_SECRET','MEXC_API_KEY','MEXC_API_SECRET','GATEIO_API_KEY','GATEIO_API_SECRET','COINBASE_API_KEY','COINBASE_API_SECRET','BITGET_API_KEY','BITGET_API_SECRET')
$found = @()
foreach ($v in $vars) {
    if (Get-ChildItem Env:$v -ErrorAction SilentlyContinue) { $found += $v }
}
if ($found.Count -gt 0) {
    Write-Output 'FOUND:'
    $found | ForEach-Object { Write-Output " - $_" }
} else {
    Write-Output 'NO_EXCHANGE_CREDS_FOUND'
}
