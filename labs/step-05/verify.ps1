[CmdletBinding()]
param([switch]$WriteEvidence, [string]$PythonExecutable)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')

$probe = "import sys; from importlib.metadata import version; from zoneinfo import ZoneInfo; version('tzdata'); ZoneInfo('Asia/Kolkata'); sys.exit(0 if sys.version_info >= (3, 10) else 1)"
$PythonExecutable = Resolve-LabPython -Executable $PythonExecutable -Probe $probe -Requirements 'labs/step-05/requirements.txt'

$sqlOutput = @(Invoke-LabSql '/labs/step-05/query.sql')
$reconnectOutput = @(Invoke-LabSql '/labs/step-05/reconnect.sql')
$fixtureLines = @($sqlOutput | Where-Object { $_.StartsWith('PYTHON_FIXTURE=') })
if ($fixtureLines.Count -ne 1) { throw 'Expected one PostgreSQL result payload for the Python exercise.' }
$payload = $fixtureLines[0].Substring('PYTHON_FIXTURE='.Length)
$pythonScript = Join-Path $PSScriptRoot 'python_lab.py'
$pythonOutput = @(Invoke-LabProcess $PythonExecutable @('-X', 'utf8', '-B', $pythonScript) -InputText $payload)
$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 5: money and time verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-05/query.sql',
    ($sqlOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-05/reconnect.sql',
    ($reconnectOutput -join "`n"),
    '',
    'Command: python -X utf8 -B labs/step-05/python_lab.py (PostgreSQL JSON fixture on stdin)',
    (($pythonOutput | ForEach-Object { "$($_)".TrimEnd() }) -join "`n")
) -join "`n"
Write-LabEvidence -Transcript $transcript -Path (Join-Path $PSScriptRoot 'evidence.txt') -Save:$WriteEvidence
