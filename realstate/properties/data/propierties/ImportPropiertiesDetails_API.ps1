# -------------------- TOP OF FILE --------------------
param(
  [string]$BasePath = $(Get-Location).Path,
  [switch]$ForceDownload
)

# --- EasyBroker: Property Detail endpoint (only) ---
# Docs: https://dev.easybroker.com/reference/get_properties-property-id
$ApiBase = 'https://api.easybroker.com/v1/properties'
$Headers = @{
  'X-Authorization' = '9zyhdg6zdm4lmllmeombg095ftiga1'
  'accept'          = 'application/json'
}

# Ensure TLS 1.2 on older hosts
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

# --------- Validate & normalize BasePath ----------
if ([string]::IsNullOrWhiteSpace($BasePath)) {
  throw "BasePath is empty. Pass -BasePath 'C:\path\to\base'."
}

# (Optional) auto-fix common typos seen earlier
$BasePath = $BasePath `
  -replace '\\lisitng(\\|$)', '\listing$1' `
 

# Resolve to a concrete path (throws if not found)
try {
  $BasePath = (Resolve-Path -LiteralPath $BasePath -ErrorAction Stop).Path
}
catch {
  throw "BasePath not found: $BasePath"
}

# --------- Folders ----------
$IdsFolder = Join-Path -Path $BasePath -ChildPath 'properties_by_id'
$OutFolder = Join-Path -Path $BasePath -ChildPath 'details'

if (-not (Test-Path -LiteralPath $IdsFolder)) {
  throw "IDs folder not found: $IdsFolder"
}
if (-not (Test-Path -LiteralPath $OutFolder)) {
  New-Item -ItemType Directory -Path $OutFolder | Out-Null
}

Write-Host "BasePath : $BasePath"
Write-Host "IDs from : $IdsFolder"
Write-Host "Output to: $OutFolder"

# --------- Helper: resilient REST with retry/backoff ----------
function Invoke-WithRetry {
  param(
    [Parameter(Mandatory=$true)][string]$Method,
    [Parameter(Mandatory=$true)][string]$Uri,
    [hashtable]$Headers,
    [int]$MaxAttempts = 5,
    [int]$InitialDelayMs = 400
  )
  $attempt = 0
  $delay = $InitialDelayMs
  while ($true) {
    $attempt++
    try {
      return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -TimeoutSec 60 -ErrorAction Stop
    }
    catch {
      $status = $_.Exception.Response.StatusCode.value__
      $retryable = ($status -ge 500) -or ($status -eq 429)
      if ($attempt -lt $MaxAttempts -and $retryable) {
        Write-Warning "[$status] Attempt $attempt failed for $Uri. Retrying in $delay ms..."
        Start-Sleep -Milliseconds $delay
        $delay = [Math]::Min($delay * 2, 8000)  # cap at 8s
        continue
      }
      throw
    }
  }
}

# --------- Extract IDs from your saved list/header JSONs ----------
# Supports BOTH shapes:
#  A) One property per file: { "public_id": "EB-XXXX" , ... }
#  B) Page/list per file:    { "content": [ { "public_id": "EB-XXXX" }, ... ], ... }
$propertyIds = @()

Get-ChildItem -LiteralPath $IdsFolder -File -Filter *.json -ErrorAction Stop | ForEach-Object {
  try {
    $obj = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json

    if ($null -ne $obj.public_id) {
      # Single property file
      $propertyIds += [string]$obj.public_id
    }
    elseif ($null -ne $obj.content) {
      # Page/list file
      $idsFromPage = $obj.content | ForEach-Object { $_.public_id } | Where-Object { $_ }
      $propertyIds += $idsFromPage
    }
    else {
      # As a last resort, if filename IS the id (e.g., EB-XXXX.json)
      $fallback = [IO.Path]::GetFileNameWithoutExtension($_.Name)
      if ($fallback -and $fallback -ne '') { $propertyIds += $fallback }
      Write-Warning "No 'public_id' or 'content' in $($_.Name). Using filename as fallback: $fallback"
    }
  }
  catch {
    Write-Warning "Could not parse JSON in $($_.Name): $($_.Exception.Message)"
  }
}

$propertyIds = $propertyIds | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Sort-Object -Unique

if (-not $propertyIds -or $propertyIds.Count -eq 0) {
  throw "No property IDs could be extracted from: $IdsFolder"
}

Write-Host "Collected $($propertyIds.Count) unique property IDs."

# --------- Download DETAILS for each ID (only /v1/properties/{id}) ----------
$failures = New-Object System.Collections.Generic.List[object]
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
    $response = Invoke-WithRetry -Method 'GET' -Uri $url -Headers $Headers
    $json = $response | ConvertTo-Json -Depth 100

    # atomic write
    $tmpFile = "$outFile.tmp"
    $json | Set-Content -LiteralPath $tmpFile -Encoding UTF8
    Move-Item -LiteralPath $tmpFile -Destination $outFile -Force
  }
  catch {
    $msg = $_.Exception.Message
    Write-Warning "Failed for '$id': $msg"
    $failures.Add([PSCustomObject]@{ id = $id; error = $msg })

    # Persist an error payload so downstream steps can detect failures
    $errPayload = "{""id"":""$($id.Replace('"','\"'))"",""error"":""$($msg.Replace('"','\"'))""}"
    $errPayload | Set-Content -LiteralPath $outFile -Encoding UTF8
  }

  # Gentle throttle
  Start-Sleep -Milliseconds 250
}

Write-Host "`nDone. Saved detail JSON files to: $OutFolder"

if ($failures.Count -gt 0) {
  Write-Warning "There were $($failures.Count) failures:"
  $failures | Format-Table -AutoSize
}
# --------------------- END OF FILE ---------------------
