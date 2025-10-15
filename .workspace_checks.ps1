param($root)

Set-Location $root
$dirs = Get-ChildItem -Recurse -Filter pyproject.toml | Select-Object -ExpandProperty DirectoryName -Unique
foreach ($d in $dirs) {
    Write-Output "== Package: $d =="
    try {
        Set-Location $d
        if (Test-Path pyproject.toml) {
            Write-Output 'Running: poetry install --no-interaction --no-ansi'
            poetry install --no-interaction --no-ansi
        }
        else {
            Write-Output 'No pyproject.toml'
        }

        if (Test-Path src) {
            Write-Output 'Running: poetry run ruff check src (if available)'
            try {
                # Try to run ruff via poetry; if not available, warn but continue
                poetry run ruff --version > $null 2>&1
                poetry run ruff check src || Write-Output 'ruff reported issues'
            }
            catch {
                Write-Output 'ruff not available in this environment; skipping ruff for this package'
            }
        }
        else {
            Write-Output 'no src dir, skipping ruff'
        }

        if (Test-Path tests) {
            Write-Output 'Running: poetry run pytest -q --rootdir . tests'
            poetry run pytest -q --rootdir . tests
        }
        else {
            Write-Output 'no tests dir, skipping pytest'
        }
    }
    catch {
        Write-Output "ERROR in ${d}: ${_}"
    }
    finally {
        Set-Location $root
    }
}
