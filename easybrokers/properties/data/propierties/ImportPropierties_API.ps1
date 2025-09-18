# -------------------- TOP OF FILE --------------------
param(
  [string]$BasePath,
  [switch]$ForceDownload
)

# --- Config ---
$ApiBase = 'https://api.easybroker.com/v1/properties'
$Headers = @{
  'X-Authorization' = '9zyhdg6zdm4lmllmeombg095ftiga1'
  'accept'          = 'application/json'
}

# Ensure TLS 1.2 on older hosts
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

# Validate BasePath
if (-not (Test-Path -LiteralPath $BasePath)) {
  throw "BasePath not found: $BasePath"
}

# Folders
$IdsFolder = Join-Path $BasePath 'properties_by_id'
$OutFolder = Join-Path $BasePath 'details'

if (-not (Test-Path -LiteralPath $IdsFolder)) {
  throw "IDs folder not found: $IdsFolder"
}
if (-not (Test-Path -LiteralPath $OutFolder)) {
  New-Item -ItemType Directory -Path $OutFolder | Out-Null
}

Write-Host "BasePath : $BasePath"
Write-Host "IDs from : $IdsFolder"
Write-Host "Output to: $OutFolder"

# Build ID array from JSON filenames
$propertyIds = Get-ChildItem -LiteralPath $IdsFolder -File -Filter *.json -ErrorAction Stop |
  ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_.Name) } |
  Where-Object { $_ -and $_.Trim().Length -gt 0 } |
  Sort-Object -Unique

Write-Host "Found $($propertyIds.Count) IDs."

# Download loop
$failures = @()
$idx = 0
foreach ($id in $propertyIds) {
  $idx++
  $url     = "$ApiBase/$id"
  $outFile = Join-Path $OutFolder "$id.json"

  if ((-not $ForceDownload) -and (Test-Path -LiteralPath $outFile)) {
    Write-Host "[$idx/$($propertyIds.Count)] Skip $id (exists)."
    continue
  }

  Write-Host "[$idx/$($propertyIds.Count)] GET $url"
  try {
    $response = Invoke-RestMethod -Method GET -Uri $url -Headers $Headers -TimeoutSec 60
    $json = $response | ConvertTo-Json -Depth 100
    $json | Set-Content -LiteralPath $outFile -Encoding UTF8
  }
  catch {
    $msg = $_.Exception.Message
    Write-Warning "Failed for '$id': $msg"
    $failures += [PSCustomObject]@{ id = $id; error = $msg }
    "{""id"":""$id"",""error"":""$($msg.Replace('"','\"'))""}" | Set-Content -LiteralPath $outFile -Encoding UTF8
  }

  Start-Sleep -Milliseconds 250
}

Write-Host "`nDone. Saved JSON files to: $OutFolder"
if ($failures.Count -gt 0) {
  Write-Warning "There were $($failures.Count) failures."
  $failures | Format-Table -AutoSize
}
