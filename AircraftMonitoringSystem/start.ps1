$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Get-RunningPythonScriptProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath
    )

    $resolvedScriptPath = (Resolve-Path $ScriptPath).Path

    return Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -in @('python.exe', 'py.exe', 'pythonw.exe') -and
            $_.CommandLine -and
            $_.CommandLine -like "*$resolvedScriptPath*"
        } |
        Select-Object -First 1
}

function Start-PythonScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,

        [Parameter(Mandatory = $true)]
        [string]$DisplayName,

        [string[]]$Arguments = @()
    )

    $existingProcess = Get-RunningPythonScriptProcess -ScriptPath $ScriptPath
    if ($existingProcess) {
        Write-Host "$DisplayName is already running (PID $($existingProcess.ProcessId))."
        return
    }

    $resolvedScriptPath = (Resolve-Path $ScriptPath).Path
    $argumentList = @($Arguments + @($resolvedScriptPath))
    $startedProcess = Start-Process -FilePath $python.Source -ArgumentList $argumentList -WorkingDirectory $root -PassThru

    Write-Host "Started $DisplayName (PID $($startedProcess.Id))."
}

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

Write-Host 'Starting application processes...'
Start-PythonScript -ScriptPath 'server/server.py' -DisplayName 'Flask server'
Start-PythonScript -ScriptPath 'applications/events_simulator.py' -DisplayName 'Events simulator'
Write-Host 'Waiting 8 seconds before starting Monitor poller...'
Start-Sleep -Seconds 8
Start-PythonScript -ScriptPath 'applications/monitor.py' -DisplayName 'Monitor poller'
