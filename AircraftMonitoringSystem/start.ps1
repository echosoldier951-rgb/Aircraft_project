$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$logFilesToClear = @(
    'MonitorLogs.txt',
    'TriggerNotifications.txt'
)

$stateFilesToRemove = @(
    '.email_trigger_state'
)
# deletes log file data on startup 
foreach ($logFile in $logFilesToClear) {
    $logPath = Join-Path $root $logFile
    if (Test-Path $logPath) {
        Clear-Content -Path $logPath
        Write-Host "Cleared log file: $logFile"
    }
}
#same as the above but for the state file
foreach ($stateFile in $stateFilesToRemove) {
    $statePath = Join-Path $root $stateFile
    if (Test-Path $statePath) {
        Remove-Item -Path $statePath -Force
        Write-Host "Removed state file: $stateFile"
    }
}

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

function Start-PythonScriptInTerminal {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath,

        [Parameter(Mandatory = $true)]
        [string]$DisplayName,

        [string[]]$Arguments = @()
    )

    $resolvedScriptPath = (Resolve-Path $ScriptPath).Path
    $argumentList = @($Arguments + @($resolvedScriptPath))

    Write-Host "Running $DisplayName in current terminal (Ctrl+C to stop)..."
    & $python.Source @argumentList
}

function Start-GreenMailServer {
    $dockerBinPath = 'C:\Program Files\Docker\Docker\resources\bin'
    if ((Test-Path $dockerBinPath) -and (-not ($env:Path -split ';' | Where-Object { $_ -eq $dockerBinPath }))) {
        $env:Path = "$dockerBinPath;$env:Path"
    }

    $docker = Get-Command docker -ErrorAction SilentlyContinue
    $dockerExe = $null

    if ($docker) {
        if ($docker.Source) {
            $dockerExe = $docker.Source
        }
        elseif ($docker.Path) {
            $dockerExe = $docker.Path
        }
    }

    if (-not $dockerExe) {
        $dockerExePath = Join-Path $dockerBinPath 'docker.exe'
        if (Test-Path $dockerExePath) {
            $dockerExe = $dockerExePath
        }
    }

    if (-not $dockerExe) {
        Write-Host 'Docker was not found on PATH. GreenMail cannot start, so SMTP/IMAP will fail.'
        Write-Host 'Install Docker Desktop and run this PDF-aligned command manually:'
        Write-Host 'docker run --rm --name greenmail-imap-lab -p 3025:3025 -p 3110:3110 -p 3143:3143 -p 8080:8080 -e GREENMAIL_OPTS="-Dgreenmail.setup.test.all -Dgreenmail.hostname=0.0.0.0 -Dgreenmail.users=student:password@student.local -Dgreenmail.verbose" greenmail/standalone:2.1.8'
        return
    }

    $containerName = 'greenmail-imap-lab'
    $existingContainerIdRaw = & $dockerExe ps -aq -f "name=^$containerName$"
    $existingContainerId = if ($existingContainerIdRaw) { $existingContainerIdRaw.Trim() } else { '' }

    if ($existingContainerId) {
        & $dockerExe rm -f $containerName | Out-Null
        Write-Host "Removed existing GreenMail container: $containerName"
    }

    $greenmailOpts = '-Dgreenmail.setup.test.all -Dgreenmail.hostname=0.0.0.0 -Dgreenmail.users=student:password@student.local -Dgreenmail.verbose'

    & $dockerExe run -d --rm `
        --name $containerName `
        -p 3025:3025 `
        -p 3110:3110 `
        -p 3143:3143 `
        -p 8080:8080 `
        -e GREENMAIL_OPTS=$greenmailOpts `
        greenmail/standalone:2.1.8 | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Started GreenMail container: $containerName (SMTP 3025, IMAP 3143, POP3 3110, Web/API 8080)"
    }
    else {
        Write-Host 'Failed to start GreenMail container. Continuing without mail server startup.'
    }
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $python) {
    throw 'Python was not found on PATH.'
}

Start-GreenMailServer

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
Write-Host 'Waiting 12 seconds before starting Trigger notifications...'
Start-Sleep -Seconds 12
Start-PythonScript -ScriptPath 'applications/trigger_notifications.py' -DisplayName 'Trigger notifications'

$emailTriggerInTerminal = $true
if ($env:EMAIL_TRIGGER_IN_TERMINAL) {
    $emailTriggerInTerminal = $env:EMAIL_TRIGGER_IN_TERMINAL.Trim().ToLower() -in @('1', 'true', 'yes', 'on')
}

if ($emailTriggerInTerminal) {
    Start-PythonScriptInTerminal -ScriptPath 'applications/email_trigger_from_log.py' -DisplayName 'Email trigger from notification log'
}
else {
    Start-PythonScript -ScriptPath 'applications/email_trigger_from_log.py' -DisplayName 'Email trigger from notification log'
}
