clear

# === Config ===
$url = "https://api.easybroker.com/v1/listing_statuses?page=1&limit=1000"
$headers = @{
    "X-Authorization" = "9zyhdg6zdm4lmllmeombg095ftiga1"
    "accept"          = "application/json"
}

# Carpeta del script y archivo de salida
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputFile = Join-Path $scriptDir "listing_statuses.json"

# === Llamada ===
$response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get

# Guardar JSON con buen formato
$response | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputFile -Encoding utf8

Write-Host "JSON saved to $outputFile"
