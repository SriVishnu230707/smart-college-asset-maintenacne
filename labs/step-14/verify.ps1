[CmdletBinding()]
param([switch]$WriteEvidence, [string]$PythonExecutable)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')
$probe = "import sys, sqlalchemy, psycopg; from importlib.metadata import version; sys.exit(0 if sys.version_info >= (3, 10) and version('SQLAlchemy') == '2.1.6' and version('psycopg') == '3.3.6' and version('psycopg-binary') == '3.3.6' else 1)"
$PythonExecutable = Resolve-LabPython -Executable $PythonExecutable -Probe $probe -Requirements 'requirements.txt'
$labRunId = [guid]::NewGuid().ToString('D')
do { $differentRunId = [guid]::NewGuid().ToString('D') } while ($differentRunId -eq $labRunId)

function Invoke-CoreExercise([string]$SqlFile, [string]$RunId = $labRunId, [int]$ExpectedExitCode = 0) {
    Invoke-LabSql $SqlFile -PsqlArguments @("--set=lab_run_id=$RunId") -ExpectedExitCode $ExpectedExitCode
}

$proofCompleted = $false
try {
    $pythonOutput = @(Invoke-LabProcess $PythonExecutable @('-X', 'utf8', '-B',
        (Join-Path $PSScriptRoot 'python_lab.py'), '--run-id', $labRunId))
    $guardOutput = @(Invoke-CoreExercise '/labs/step-14/cleanup.sql' $differentRunId 3)
    $guardTranscript = $guardOutput -join "`n"
    if ($guardTranscript -notmatch 'REFUSED: STEP14_RUN_ID_MISMATCH' -or $guardTranscript -notmatch 'ERROR:\s+22023\b') {
        throw 'Cleanup did not report the exact expected run-ID refusal.'
    }
    $guardOutput += 'PASS: Cleanup refuses a different run ID before removing any study object.'
    $observerOutput = @(Invoke-CoreExercise '/labs/step-14/reconnect.sql')
    $proofCompleted = $true
}
finally {
    # Independent verification needs committed rows. Always attempt exact-run cleanup.
    $cleanupOutput = @(Invoke-CoreExercise '/labs/step-14/cleanup.sql')
    $cleanupCheckOutput = @(Invoke-CoreExercise '/labs/step-14/cleanup-check.sql')
    if (-not $proofCompleted) {
        $cleanupOutput | ForEach-Object { Write-Host "$_" }
        $cleanupCheckOutput | ForEach-Object { Write-Host "$_" }
    }
}

$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 14: Core connections, bound values, and transaction verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    "Lab run ID (synthetic cleanup marker, not a credential): $labRunId",
    "Different run ID used for the cleanup refusal proof: $differentRunId",
    'The duplicate-code error (23505) and cleanup refusal (22023) are deliberate and asserted.',
    'Command: python -X utf8 -B labs/step-14/python_lab.py --run-id <run-id>',
    ($pythonOutput -join "`n"),
    '',
    'Command (expected exit 3, SQLSTATE 22023): docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<different-run-id> --file /labs/step-14/cleanup.sql',
    ($guardOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<run-id> --file /labs/step-14/reconnect.sql',
    ($observerOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<run-id> --file /labs/step-14/cleanup.sql',
    ($cleanupOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<run-id> --file /labs/step-14/cleanup-check.sql',
    ($cleanupCheckOutput -join "`n")
) -join "`n"
Write-LabEvidence -Transcript $transcript -Path (Join-Path $PSScriptRoot 'evidence.txt') -Save:$WriteEvidence
