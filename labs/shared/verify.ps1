# Shared by the lab entry points; compatible with PowerShell 5.1 and 7.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$composeFile = Join-Path $projectRoot 'compose.yaml'

function Invoke-LabProcess {
    param([string]$FilePath, [string[]]$Arguments = @(),
          [int]$ExpectedExitCode = 0, [string]$InputText)

    $executable = (Get-Command $FilePath -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $previousPreference = $ErrorActionPreference
    try {
        # Windows PowerShell wraps native stderr in ErrorRecords. Capture it
        # without terminating early, then check the actual process exit code.
        $ErrorActionPreference = 'Continue'
        $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        if ($PSBoundParameters.ContainsKey('InputText')) {
            $result = @($InputText | & $executable @Arguments 2>&1)
        } else {
            $result = @(& $executable @Arguments 2>&1)
        }
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    $lines = @($result | ForEach-Object { "$($_)".TrimEnd() })
    if ($exitCode -ne $ExpectedExitCode) {
        throw "$FilePath exited $exitCode (expected $ExpectedExitCode).`n$($lines -join "`n")"
    }
    return $lines
}

function Invoke-LabSql {
    param([string]$SqlFile, [string[]]$PsqlArguments = @(), [int]$ExpectedExitCode = 0)
    Invoke-LabProcess -FilePath docker -ExpectedExitCode $ExpectedExitCode -Arguments (
        @('compose', '--file', $composeFile, 'exec', '-T', 'postgres', 'sh', '/labs/step-02/psql.sh') +
        $PsqlArguments + @('--file', $SqlFile))
}

function Resolve-LabPython {
    param([string]$Executable, [string]$Probe, [string]$Requirements)
    if ($Executable) {
        $candidates = @($Executable)
    } else {
        $candidates = @(
            (Join-Path $projectRoot '.venv/Scripts/python.exe'),
            (Join-Path $projectRoot '.venv/bin/python')
        ) + @(Get-Command python3, python -CommandType Application -ErrorAction SilentlyContinue |
            Where-Object { $_.Source -notmatch '[\\/]WindowsApps[\\/]' } | ForEach-Object { $_.Source }) + @(
            (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe')
        )
    }
    foreach ($candidate in $candidates | Select-Object -Unique) {
        try {
            Invoke-LabProcess $candidate @('-c', $Probe) | Out-Null
            return $candidate
        } catch {
            # An explicit interpreter is the only candidate; do not replace it.
        }
    }
    throw "No usable Python 3.10+ matching $Requirements was found. Supply -PythonExecutable and install $Requirements."
}

function Write-LabEvidence {
    param([string]$Transcript, [string]$Path, [switch]$Save)
    Write-Output $Transcript
    if ($Save) {
        [IO.File]::WriteAllText($Path, $Transcript + "`n", (New-Object System.Text.UTF8Encoding($false)))
        Write-Output "Evidence saved: $Path"
    }
}
