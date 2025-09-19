clear
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# === Config ===
$baseUrl  = "https://api.easybroker.com/v1/properties".Trim()
$headers  = @{
    "X-Authorization" = "9zyhdg6zdm4lmllmeombg095ftiga1"
    "accept"          = "application/json"
}

$limit    = 50
$page     = 1

# === Salidas (junto al script)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outJson   = Join-Path $scriptDir "properties.json"
$outNdjson = Join-Path $scriptDir "properties.ndjson"
$byIdDir   = Join-Path $scriptDir "properties_by_id"

# Limpieza previa
if (Test-Path $outJson)   { Remove-Item $outJson  -Force }
if (Test-Path $outNdjson) { Remove-Item $outNdjson -Force }
if (Test-Path $byIdDir)   { Remove-Item $byIdDir -Recurse -Force }
New-Item -ItemType Directory -Path $byIdDir | Out-Null

# Acumulador
$all = New-Object System.Collections.Generic.List[object]
$seq = 0

Write-Host "Descargando propiedades de EasyBroker…" -ForegroundColor Cyan
Write-Host "Base URL: >$baseUrl< (len=$($baseUrl.Length))"

while ($true) {
    # URL simple (sin HttpUtility)
    $url = "$baseUrl?page=$page&limit=$limit"

    try {
        $resp = Invoke-RestMethod -Uri $url -Headers $headers -Method Get -ErrorAction Stop
    }
    catch {
        Write-Host "Error en la solicitud (página $page): $($_.Exception.Message)" -ForegroundColor Red
        break
    }

    # EasyBroker suele responder con 'content' y 'pagination'
    $items = $null
    if ($resp -and $resp.PSObject.Properties.Name -contains 'content') {
        $items = $resp.content
    }
    elseif ($resp -and $resp.PSObject.Properties.Name -contains 'data') {
        $items = $resp.data
    }
    elseif ($resp -is [System.Collections.IEnumerable]) {
        $items = $resp
    }
    else {
        $items = @($resp)
    }

    if (-not $items -or $items.Count -eq 0) {
        Write-Host "No hay más resultados. Fin de la paginación." -ForegroundColor Yellow
        break
    }

    foreach ($it in $items) {
        $all.Add($it); $seq++

        # ID: public_id > id > consecutivo
        $propId =
            if ($it.PSObject.Properties.Name -contains 'public_id' -and $it.public_id) { [string]$it.public_id }
            elseif ($it.PSObject.Properties.Name -contains 'id' -and $it.id)           { [string]$it.id }
            else                                                                       { "item_{0:000000}" -f $seq }

        $safeId   = ($propId -replace '[^\w\.-]+','_')
        $fileById = Join-Path $byIdDir ($safeId + ".json")

        # Archivo por ID (formato legible)
        $it | ConvertTo-Json -Depth 20 | Out-File -FilePath $fileById -Encoding utf8

        # NDJSON (una línea por objeto)
        ($it | ConvertTo-Json -Depth 20 -Compress) | Out-File -FilePath $outNdjson -Encoding utf8 -Append
    }

    Write-Host ("Página {0} descargada ({1} propiedades)" -f $page, $items.Count)

    # ¿Más páginas?
    $hasMore = $true
    if ($resp -and $resp.PSObject.Properties.Name -contains 'pagination') {
        $pg = $resp.pagination
        if     ($pg -and $pg.PSObject.Properties.Name -contains 'total_pages') { $hasMore = ($page -lt [int]$pg.total_pages) }
        elseif ($pg -and $pg.PSObject.Properties.Name -contains 'next_page')   { $hasMore = [bool]$pg.next_page }
    }
    else {
        if ($items.Count -lt $limit) { $hasMore = $false }
    }

    if (-not $hasMore) { break }
    $page++
    Start-Sleep -Milliseconds 200
}

# Guardar combinado
$all | ConvertTo-Json -Depth 20 | Out-File -FilePath $outJson -Encoding utf8

Write-Host ""
Write-Host "Propiedades totales: $($all.Count)" -ForegroundColor Green
Write-Host "Archivo combinado:   $outJson"
Write-Host "Archivo NDJSON:      $outNdjson"
Write-Host "Carpeta por ID:      $byIdDir"
