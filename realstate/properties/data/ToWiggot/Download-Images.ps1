# -------------------- Download images from bajar.csv --------------------
#Requires -Version 5.1

param(
  [string]$CsvPath = ".\bajar.csv",
  [string]$OutputRoot = ".\images",
  [int]$MaxRetries = 3,
  [int]$TimeoutSec = 120
)

# TLS 1.2 (older hosts)
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch {}

# Basic validation
if (-not (Test-Path -LiteralPath $CsvPath)) {
  throw "CSV not found: $CsvPath"
}
if (-not (Test-Path -LiteralPath $OutputRoot)) {
  New-Item -ItemType Directory -Path $OutputRoot | Out-Null
}

# Detect delimiter (tab or comma) -> PS5 style (no inline-if expression)
$firstLine = Get-Content -LiteralPath $CsvPath -TotalCount 1 -ErrorAction Stop
$delimiter = ","
if ($firstLine -match "`t") { $delimiter = "`t" }

# Import CSV (header expected: public_id,image_index,url)
$rows = Import-Csv -LiteralPath $CsvPath -Delimiter $delimiter -ErrorAction Stop

if (-not $rows -or $rows.Count -eq 0) {
  throw "CSV appears to be empty: $CsvPath"
}

# Optional sanity check for headers (don’t index $rows[0] if empty)
$expected = @('public_id','image_index','url')
$actualCols = $rows[0].psobject.Properties.Name
$missing = $expected | Where-Object { $_ -notin $actualCols }
if ($missing.Count -gt 0) {
  throw "CSV missing expected column(s): $($missing -join ', ')"
}

function Get-UrlExtension {
  param([string]$Url)
  try {
    $u    = [Uri]$Url
    $leaf = [System.IO.Path]::GetFileName($u.AbsolutePath)
    $ext  = [System.IO.Path]::GetExtension($leaf)
    if ([string]::IsNullOrWhiteSpace($ext)) { return ".jpg" }
    return $ext
  } catch { return ".jpg" }
}

function Sanitize-Name {
  param([string]$Name)
  $invalid = [System.IO.Path]::GetInvalidFileNameChars() -join ''
  $regex = "[{0}]" -f [RegEx]::Escape($invalid)
  return ($Name -replace $regex, "_")
}

function Download-File {
  param(
    [string]$Url,
    [string]$OutFile,
    [int]$MaxRetries = 3,
    [int]$TimeoutSec = 120
  )
  for ($i = 1; $i -le $MaxRetries; $i++) {
    try {
      if (Test-Path -LiteralPath $OutFile) { return $true }
      Invoke-WebRequest -Uri $Url -OutFile $OutFile -Headers @{ 'User-Agent'='Mozilla/5.0' } -TimeoutSec $TimeoutSec -UseBasicParsing
      return $true
    } catch {
      if ($i -eq $MaxRetries) {
        Write-Warning "Failed ($i/$MaxRetries): $Url -> $OutFile : $($_.Exception.Message)"
        return $false
      }
      Start-Sleep -Seconds ([Math]::Min(2 * $i, 10))
    }
  }
}

$counter = 0
foreach ($row in $rows) {
  $counter++

  $publicId   = "$($row.public_id)".Trim()
  $imageIndex = "$($row.image_index)".Trim()
  $url        = "$($row.url)".Trim()

  if ([string]::IsNullOrWhiteSpace($publicId) -or
      [string]::IsNullOrWhiteSpace($imageIndex) -or
      [string]::IsNullOrWhiteSpace($url)) {
    Write-Warning "Skipping row $counter due to missing data."
    continue
  }

  $safePublicId = Sanitize-Name $publicId
  $targetDir = Join-Path $OutputRoot $safePublicId
  if (-not (Test-Path -LiteralPath $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
  }

  $ext = Get-UrlExtension $url

  # Zero-pad indexes (handles non-numeric gracefully)
  $num = 0
  if ([int]::TryParse($imageIndex, [ref]$num)) {
    $fileName = ('{0:D3}{1}' -f $num, $ext)
  } else {
    $fileName = ($imageIndex + $ext)
  }

  $outFile = Join-Path $targetDir $fileName

  if (Download-File -Url $url -OutFile $outFile -MaxRetries $MaxRetries -TimeoutSec $TimeoutSec) {
    Write-Host ("[{0}] {1} -> {2}" -f $publicId, $imageIndex, $outFile)
  }
}

Write-Host "Done. Images saved under: $OutputRoot"
# ------------------------------------------------------------------------
