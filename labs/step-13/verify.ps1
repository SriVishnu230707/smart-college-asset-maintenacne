[CmdletBinding()]
param([switch]$WriteEvidence, [string]$PythonExecutable)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')
$probe = "import sys, sqlalchemy, psycopg; from importlib.metadata import version; sys.exit(0 if sys.version_info >= (3, 10) and version('SQLAlchemy') == '2.1.6' and version('psycopg') == '3.3.6' and version('psycopg-binary') == '3.3.6' else 1)"
$PythonExecutable = Resolve-LabPython -Executable $PythonExecutable -Probe $probe -Requirements 'requirements.txt'
$pythonOutput = @(Invoke-LabProcess $PythonExecutable @('-X', 'utf8', '-B', (Join-Path $PSScriptRoot 'python_lab.py')))
$backendMatch = [regex]::Match(($pythonOutput -join "`n"), '(?m)^engine_backend_pid=(\d+)\s*$')
if (-not $backendMatch.Success) { throw 'The Python probe did not report its PostgreSQL backend PID.' }
$engineBackend = $backendMatch.Groups[1].Value
$reconnectOutput = @(Invoke-LabSql '/labs/step-13/reconnect.sql' -PsqlArguments @("--set=engine_backend_pid=$engineBackend"))
$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 13: Python database-layer verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    'Command: python -X utf8 -B labs/step-13/python_lab.py',
    ($pythonOutput -join "`n"),
    '',
    "Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=engine_backend_pid=$engineBackend --file /labs/step-13/reconnect.sql",
    ($reconnectOutput -join "`n")
) -join "`n"
Write-LabEvidence -Transcript $transcript -Path (Join-Path $PSScriptRoot 'evidence.txt') -Save:$WriteEvidence
