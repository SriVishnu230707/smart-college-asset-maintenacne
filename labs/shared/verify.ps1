# Shared by the lab entry points; compatible with PowerShell 5.1 and 7.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$composeFile = Join-Path $projectRoot 'compose.yaml'

function Invoke-LabProcess {
    param([string]$FilePath, [string[]]$Arguments = @(),
          [int]$ExpectedExitCode = 0, [string]$InputText, [string]$LogPath)

    if ($LogPath) {
        $logEncoding = New-Object System.Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($LogPath, '', $logEncoding)
    }
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
    if ($LogPath) { [IO.File]::WriteAllText($LogPath, ($lines -join "`n") + "`n", $logEncoding) }
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

function Invoke-CommittedLab {
    param([string]$Step, [string]$Title, [string]$ExpectedBehavior,
          [string]$PythonExecutable, [switch]$WriteEvidence, [switch]$SqlOnly)

    if (-not $SqlOnly) {
        $probe = "import sys, sqlalchemy, psycopg; from importlib.metadata import version; sys.exit(0 if sys.version_info >= (3, 10) and version('SQLAlchemy') == '2.1.6' and version('psycopg') == '3.3.6' and version('psycopg-binary') == '3.3.6' else 1)"
        if ([int]$Step -ge 26) { $probe = "import alembic; from importlib.metadata import version; assert version('alembic') == '1.20.1'; " + $probe }
        $PythonExecutable = Resolve-LabPython -Executable $PythonExecutable -Probe $probe -Requirements 'requirements.txt'
    }
    $labDirectory = Join-Path $projectRoot "labs/step-$Step"
    $labRunId = [guid]::NewGuid().ToString('D')
    $differentRunId = [guid]::Empty.ToString('D')
    $sqlRoot = "/labs/step-$Step"
    $outputs = @{}
    $labFailure = $null
    $cleanupErrors = New-Object 'System.Collections.Generic.List[string]'
    try {
        if ($SqlOnly) {
            $outputs.exercise = @(Invoke-LabSql "$sqlRoot/query.sql" -PsqlArguments @("--set=lab_run_id=$labRunId"))
        } else {
            $outputs.exercise = @(Invoke-LabProcess $PythonExecutable @('-X', 'utf8', '-B',
                (Join-Path $labDirectory 'python_lab.py'), '--run-id', $labRunId))
        }
        $outputs.guard = @(Invoke-LabSql "$sqlRoot/cleanup.sql" -PsqlArguments @("--set=lab_run_id=$differentRunId") -ExpectedExitCode 3)
        $guardTranscript = $outputs.guard -join "`n"
        if ($guardTranscript -notmatch "REFUSED: STEP${Step}_RUN_ID_MISMATCH" -or $guardTranscript -notmatch 'ERROR:\s+22023\b') {
            throw 'Cleanup did not report the exact expected run-ID refusal.'
        }
        $outputs.guard += 'PASS: Cleanup refuses a different run ID before removing any study object.'
        $outputs.observer = @(Invoke-LabSql "$sqlRoot/reconnect.sql" -PsqlArguments @("--set=lab_run_id=$labRunId"))
    } catch {
        $labFailure = $_
    } finally {
        # Attempt both checks, and never replace the original failure with a
        # secondary cleanup error. No evidence is saved when either fails.
        foreach ($file in @('cleanup.sql', 'cleanup-check.sql')) {
            try {
                $outputs[$file] = @(Invoke-LabSql "$sqlRoot/$file" -PsqlArguments @("--set=lab_run_id=$labRunId"))
            } catch {
                $cleanupErrors.Add("${file}: $($_.Exception.Message)")
            }
        }
    }
    if ($cleanupErrors.Count) {
        $original = if ($labFailure) { $labFailure.Exception.Message } else { 'The lab completed but cleanup failed.' }
        throw "$original`nCleanup errors:`n$($cleanupErrors -join "`n")"
    }
    if ($labFailure) { throw $labFailure }

    $capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
    $exerciseCommand = if ($SqlOnly) {
        "Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<run-id> --file $sqlRoot/query.sql"
    } else { "Command: python -X utf8 -B labs/step-$Step/python_lab.py --run-id <run-id>" }
    $transcript = @(
        "Step ${Step}: $Title verification evidence", "Captured (Asia/Kolkata): $capturedAt",
        "Lab run ID (synthetic cleanup marker, not a credential): $labRunId",
        "Different run ID used for the cleanup refusal proof: $differentRunId", $ExpectedBehavior,
        $exerciseCommand, ($outputs.exercise -join "`n"), '',
        "Command (expected exit 3, SQLSTATE 22023): docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<different-run-id> --file $sqlRoot/cleanup.sql",
        ($outputs.guard -join "`n"), ''
        foreach ($section in @(@('reconnect.sql', 'observer'), @('cleanup.sql', 'cleanup.sql'), @('cleanup-check.sql', 'cleanup-check.sql'))) {
            "Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<run-id> --file $sqlRoot/$($section[0])"
            $outputs[$section[1]] -join "`n"
            ''
        }
    ) -join "`n"
    Write-LabEvidence -Transcript $transcript.TrimEnd() -Path (Join-Path $labDirectory 'evidence.txt') -Save:$WriteEvidence
}
