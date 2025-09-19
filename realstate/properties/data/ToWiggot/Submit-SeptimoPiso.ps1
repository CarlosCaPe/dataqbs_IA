<# 
.SYNOPSIS
  Build a sitemap, verify it’s reachable, and notify search engines (Google ping, GSC API, IndexNow).

.NOTES
  - Google "ping" only works if the sitemap URL is publicly reachable.
  - Bing ping endpoint is deprecated (410). Prefer IndexNow (requires hosting a key file).
  - Best path: Verify property in Google Search Console and submit sitemap/page there.
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [string]$SiteUrl,                 # e.g., https://septimopiso.wiggot.com/

  [Parameter(Mandatory=$true)]
  [string]$SitemapLocalPath,        # e.g., C:\temp\sitemap.xml

  [Parameter(Mandatory=$true)]
  [string]$SitemapWebUrl,           # e.g., https://septimopiso.wiggot.com/sitemap.xml

  [Parameter(Mandatory=$false)]
  [string]$GoogleAccessToken,       # OAuth token for Search Console (webmasters scope), optional

  [Parameter(Mandatory=$false)]
  [string]$GSCPropertyUrl = 'https://septimopiso.wiggot.com/', # must match verified property exactly

  # IndexNow (optional): only use if you can host a key file on the same host
  [Parameter(Mandatory=$false)]
  [switch]$UseIndexNow,             # enable IndexNow call
  [Parameter(Mandatory=$false)]
  [string]$IndexNowHost,            # e.g., septimopiso.wiggot.com
  [Parameter(Mandatory=$false)]
  [string]$IndexNowKey,             # your IndexNow key (filename/content)
  [Parameter(Mandatory=$false)]
  [string[]]$IndexNowUrls           # URLs to notify (e.g., $SiteUrl, $SitemapWebUrl)
)

function Invoke-HttpGet {
  param([string]$Url, [int]$TimeoutSec = 30)
  try {
    return Invoke-WebRequest -Uri $Url -UseBasicParsing -Method GET -TimeoutSec $TimeoutSec
  } catch {
    return $null
  }
}

function Test-UrlReachable {
  param([string]$Url)
  $resp = Invoke-HttpGet -Url $Url
  if ($resp -and ($resp.StatusCode -ge 200) -and ($resp.StatusCode -lt 400)) { return $true }
  return $false
}

function New-SitemapXml {
  param(
    [string]$Url,
    [string]$OutFile
  )
  Write-Host "Building sitemap at $OutFile ..."
  $now = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  $content = @"
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>$Url</loc>
    <lastmod>$now</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
"@
  New-Item -ItemType Directory -Force -Path (Split-Path -LiteralPath $OutFile) | Out-Null
  $content | Set-Content -LiteralPath $OutFile -Encoding UTF8
  Write-Host "Sitemap.xml written."
}

function Ping-GoogleSitemap {
  param([Parameter(Mandatory=$true)][string]$SitemapUrl)
  # Only attempt if the sitemap is reachable
  if (-not (Test-UrlReachable -Url $SitemapUrl)) {
    Write-Warning "Sitemap not reachable at $SitemapUrl — skipping Google ping."
    return
  }
  $encoded = [uri]::EscapeDataString($SitemapUrl)
  try {
    Invoke-WebRequest -Uri "https://www.google.com/ping?sitemap=$encoded" -UseBasicParsing -Method GET -TimeoutSec 30 | Out-Null
    Write-Host "Google ping call sent (Google may ignore pings unless the property is verified)."
  } catch {
    Write-Warning "Google ping failed: $($_.Exception.Message)"
  }
}

function Submit-SitemapToGoogleSearchConsole {
  param(
    [string]$PropertyUrl,       # exact verified property
    [string]$SitemapUrl,
    [string]$AccessToken
  )
  if (-not $AccessToken) {
    Write-Warning "No GoogleAccessToken provided. Skipping Search Console submission."
    return
  }
  if (-not (Test-UrlReachable -Url $SitemapUrl)) {
    Write-Warning "Sitemap not reachable at $SitemapUrl — Search Console may reject it."
  }
  Write-Host "Submitting sitemap to Google Search Console API..."
  try {
    $endpoint = "https://www.googleapis.com/webmasters/v3/sites/$([uri]::EscapeDataString($PropertyUrl))/sitemaps/$([uri]::EscapeDataString($SitemapUrl))"
    $headers  = @{ Authorization = "Bearer $AccessToken" }
    Invoke-WebRequest -Uri $endpoint -Method PUT -Headers $headers -UseBasicParsing -TimeoutSec 30 | Out-Null
    Write-Host "Sitemap submitted to Search Console."
  } catch {
    Write-Warning "Search Console submission failed: $($_.Exception.Message)"
  }
}

function Invoke-IndexNow {
  param(
    [string]$Host,
    [string]$Key,
    [string[]]$Urls
  )
  if (-not $Host -or -not $Key -or -not $Urls -or $Urls.Count -eq 0) {
    Write-Warning "IndexNow parameters incomplete — skipping."
    return
  }

  <#
    IMPORTANT:
    - You must host the key file (filename: $Key.txt) at:
        https://$Host/$Key.txt
      or
        https://$Host/.well-known/$Key
    - If you cannot place a file at that host, IndexNow will not verify and will be ineffective.
  #>

  $endpoint = "https://api.indexnow.org/indexnow"
  $body = @{
    host   = $Host
    key    = $Key
    urlList = $Urls
  } | ConvertTo-Json -Depth 3

  Write-Host "Calling IndexNow..."
  try {
    Invoke-WebRequest -Uri $endpoint -Method POST -UseBasicParsing -ContentType 'application/json' -Body $body -TimeoutSec 30 | Out-Null
    Write-Host "IndexNow POST sent."
  } catch {
    Write-Warning "IndexNow request failed: $($_.Exception.Message)"
  }
}

# --- 0) Hit the target page (optional warm-up) ---
$resp = Invoke-HttpGet -Url $SiteUrl
if ($resp) { Write-Host "Site GET: $($resp.StatusCode) $($resp.StatusDescription)" }
else { Write-Warning "Site GET failed (continuing)..." }

# --- 1) Build sitemap locally ---
New-SitemapXml -Url $SiteUrl -OutFile $SitemapLocalPath
Write-Host "`nUpload $SitemapLocalPath to:"
Write-Host "  $SitemapWebUrl"

# --- 2) Ping Google (ONLY if sitemap is reachable) ---
Ping-GoogleSitemap -SitemapUrl $SitemapWebUrl

# --- 3) (Optional) Submit to Google Search Console (requires token + verified property) ---
if ($GoogleAccessToken) {
  Submit-SitemapToGoogleSearchConsole -PropertyUrl $GSCPropertyUrl -SitemapUrl $SitemapWebUrl -AccessToken $GoogleAccessToken
} else {
  Write-Host "`nNo GoogleAccessToken provided. You can still submit in the Search Console UI."
}

# --- 4) (Optional) IndexNow for Bing/Yandex (requires hosting key file on the same host) ---
if ($UseIndexNow) {
  # Build the URL list safely without inline ternary
  $urls = @()
  if ($IndexNowUrls -and $IndexNowUrls.Count -gt 0) {
    $urls = $IndexNowUrls
  } else {
    $urls = @($SiteUrl)
  }

  Invoke-IndexNow -Host $IndexNowHost -Key $IndexNowKey -Urls $urls
} else {
  Write-Host "`n(Bing ping is deprecated and returns 410. Use Bing Webmaster Tools or IndexNow when hosting is possible.)"
}

Write-Host "`nDone."
