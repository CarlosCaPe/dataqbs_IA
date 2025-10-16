<#
Validate environment for the `projects/arbitraje` project.
Exits with code 0 on success. Non-zero on failure.
Checks:
 - Poetry env exists
 - `poetry run ruff --version` works (ruff installed in env)
 - `poetry lock --check` supported and passes (optional)
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "[validate_env] Start validation at $(Get-Date -Format o)"

# Resolve project root (script executed from project folder by tasks)
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "[validate_env] Project root: $projectRoot"

Push-Location $projectRoot
try {
    # 1) Check poetry exists
    try {
        $poetry = Get-Command poetry -ErrorAction Stop
        Write-Host "[validate_env] Found poetry: $($poetry.Path)"
    } catch {
        Write-Error "[validate_env] poetry not found in PATH. Install poetry or ensure it's on PATH."
        exit 2
    }

    # 2) Check poetry env info
    try {
        $venv = poetry env info -p 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "[validate_env] poetry env info failed; attempting to proceed anyway. Output: $venv"
        } else {
            Write-Host "[validate_env] Poetry venv: $venv"
        }
    } catch {
        Write-Warning "[validate_env] Could not run 'poetry env info -p' (continuing)"
    }

    # 3) Check ruff availability within poetry env
    try {
        $ruffVer = poetry run ruff --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "[validate_env] 'poetry run ruff --version' failed. ruff is not installed in the poetry environment."
            exit 3
        }
        Write-Host "[validate_env] ruff available: $ruffVer"
    } catch {
        Write-Error "[validate_env] Exception when running 'poetry run ruff --version': $_"
        exit 3
    }

    # 4) Optional: check poetry lock validity if supported
    try {
        $lockCheck = poetry lock --check 2>&1
        $code = $LASTEXITCODE
        if ($code -eq 0) {
            Write-Host "[validate_env] poetry lock --check passed"
        } elseif ($code -eq 2) {
            # poetry prints exit code 2 for out-of-sync on some versions
            Write-Warning "[validate_env] poetry lock --check reported mismatch. Consider running 'poetry lock'"
        } else {
            Write-Warning "[validate_env] poetry lock --check returned code $code; output: $lockCheck"
        }
    } catch {
        Write-Warning "[validate_env] 'poetry lock --check' not supported or failed; falling back to suggestion."
    }

    Write-Host "[validate_env] All quick checks passed."
    exit 0
} finally {
    Pop-Location
}
