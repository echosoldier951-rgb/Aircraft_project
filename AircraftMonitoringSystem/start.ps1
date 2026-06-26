$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $python) {
    throw 'Python was not found on PATH.'
}

$postgresService = Get-Service -Name 'postgresql*','PostgreSQL*' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($postgresService) {
    if ($postgresService.Status -ne 'Running') {
        Start-Service $postgresService.Name
    }
    Write-Host "PostgreSQL service is running: $($postgresService.Name)"
}
else {
    Write-Host 'No PostgreSQL service was detected. Continuing anyway.'
}

Write-Host 'Initializing the database...'
& $python.Source database/init_db.py

Write-Host 'Starting the Flask server...'
& $python.Source server/server.py
