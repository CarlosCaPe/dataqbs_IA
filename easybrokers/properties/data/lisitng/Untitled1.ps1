<#
.SYNOPSIS
  Prueba conexión IMAP a Outlook/Hotmail usando LOGIN (app password) con fallback de host.

.USAGE
  pwsh -File .\scripts\Test-HotmailImap.ps1                # Lee HOTMAIL_USER / HOTMAIL_PASS de .env
  pwsh -File .\scripts\Test-HotmailImap.ps1 -Verbose       # Verbose
  pwsh -File .\scripts\Test-HotmailImap.ps1 -User u@outlook.com -Password 'app_pass'

.NOTES
  No imprime la contraseña. Usa únicamente para diagnóstico rápido.
  Si devuelve a1 OK LOGIN completed => autenticación básica IMAP habilitada y app password válido.
  Si devuelve a1 NO LOGIN failed => credenciales, propagación o bloqueo de basic auth.
#>

[CmdletBinding()]
param(
    [string]$User,
    [string]$Password,
    [string]$PrimaryHost = 'outlook.office365.com',
    [string]$FallbackHost = 'imap-mail.outlook.com',
    [int]$Port = 993,
    [switch]$NoFallback
)

function Get-DotEnvValue {
    param([string]$Name, [string]$Path = '.env')
    if (-not (Test-Path $Path)) { return $null }
    $line = Get-Content -Path $Path | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
    if (-not $line) { return $null }
    return ($line -split '=', 2)[1].Trim().Trim('"')
}

if (-not $User) { $User = Get-DotEnvValue -Name 'HOTMAIL_USER' }
if (-not $Password) { $Password = Get-DotEnvValue -Name 'HOTMAIL_PASS' }

if (-not $User -or -not $Password) {
    Write-Error 'Faltan HOTMAIL_USER u HOTMAIL_PASS (pase -User/-Password o rellene .env).'
    exit 2
}

Write-Verbose "Usuario: $User"

Add-Type -AssemblyName System.Net.Security
Add-Type -AssemblyName System.Net.Primitives
Add-Type -AssemblyName System.IO
Add-Type -AssemblyName System.Net.Sockets

function Invoke-ImapLogin {
    param(
        [string]$ImapHost,
        [int]$Port,
        [string]$User,
        [string]$Password  # Plain for quick diagnostic only
    )
    $tcp = New-Object System.Net.Sockets.TcpClient
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $tcp.Connect($ImapHost, $Port)
    $sslStream = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, { param($s, $c, $ch, $e) return $true })
    $sslStream.AuthenticateAsClient($ImapHost)
    $reader = New-Object System.IO.StreamReader($sslStream)
    $writer = New-Object System.IO.StreamWriter($sslStream)
    $writer.NewLine = "`r`n"
    $writer.AutoFlush = $true
    # Greeting
    $greet = $reader.ReadLine()
    [PSCustomObject]@{ Stage = 'Greeting'; Host = $ImapHost; Line = $greet }
    # LOGIN
    $loginCmd = "a1 LOGIN $User $Password"
    $writer.WriteLine($loginCmd)
    $resp = @()
    while ($true) {
        if ($sslStream.CanRead -and $tcp.Connected) {
            if ($reader.Peek() -ge 0) {
                $line = $reader.ReadLine()
                $resp += $line
                if ($line -match '^a1 ') { break }
            }
            else { Start-Sleep -Milliseconds 50 }
        }
        else { break }
        if ($sw.Elapsed.TotalSeconds -gt 10) { break }
    }
    foreach ($l in $resp) { [PSCustomObject]@{ Stage = 'Response'; Host = $ImapHost; Line = $l } }
    # LOGOUT
    $writer.WriteLine('a2 LOGOUT') | Out-Null
    $tcp.Close()
}

$results = @()
try {
    Write-Host ("Probando IMAP en {0}:{1} ..." -f $PrimaryHost, $Port) -ForegroundColor Cyan
    $results += Invoke-ImapLogin -ImapHost $PrimaryHost -Port $Port -User $User -Password $Password
    $loginLine = ($results | Where-Object { $_.Line -match '^a1 ' } | Select-Object -Last 1).Line
    if ($loginLine -match 'OK') {
        Write-Host ("LOGIN OK en host primario ({0})" -f $PrimaryHost) -ForegroundColor Green
    }
    elseif (-not $NoFallback) {
        Write-Host ("LOGIN falló en primario; intentando fallback {0} ..." -f $FallbackHost) -ForegroundColor Yellow
        $results += Invoke-ImapLogin -ImapHost $FallbackHost -Port $Port -User $User -Password $Password
        $fbLine = ($results | Where-Object { $_.Host -eq $FallbackHost -and $_.Line -match '^a1 ' } | Select-Object -Last 1).Line
        if ($fbLine -match 'OK') { Write-Host "LOGIN OK en fallback." -ForegroundColor Green } else { Write-Host "LOGIN falló también en fallback." -ForegroundColor Red }
    }
    else {
        Write-Host "LOGIN falló (sin fallback)." -ForegroundColor Red
    }
}
catch {
    Write-Error $_
}

Write-Host "Resumen bruto:" -ForegroundColor Cyan
$results | Format-Table -AutoSize

<# Interpretación rápida:
  a1 OK LOGIN completed   => Exito (basic auth + app password activo)
  a1 NO LOGIN failed.     => Credencial / app password / bloqueo basic auth
  * BYE Authentication failed. => Servidor cerró sesión (posible bloqueo)
  Si ambos hosts fallan y app password es nuevo => probablemente OAuth necesario.
#>
