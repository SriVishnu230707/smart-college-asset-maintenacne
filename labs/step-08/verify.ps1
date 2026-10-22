[CmdletBinding()]
param([switch]$WriteEvidence)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$composeFile = Join-Path $projectRoot 'compose.yaml'
$labRunId = [guid]::NewGuid().ToString('D')
do { $differentRunId = [guid]::NewGuid().ToString('D') } while ($differentRunId -eq $labRunId)

function Invoke-CrudExercise([string]$SqlFile, [string]$RunId = $labRunId, [int]$ExpectedExitCode = 0) {
    $result = @(& docker compose --file $composeFile exec -T postgres sh /labs/step-02/psql.sh "--set=lab_run_id=$RunId" --file $SqlFile 2>&1)
    if ($LASTEXITCODE -ne $ExpectedExitCode) {
        $result | ForEach-Object { Write-Host "$_" }
        throw "Step 8 CRUD/transaction exercise failed: $SqlFile"
    }
    return ($result | ForEach-Object { "$($_)".TrimEnd() })
}

$proofCompleted = $false
try {
    $exerciseOutput = @(Invoke-CrudExercise '/labs/step-08/query.sql')
    $guardOutput = @(Invoke-CrudExercise '/labs/step-08/cleanup.sql' $differentRunId 3)
    $guardTranscript = $guardOutput -join "`n"
    if ($guardTranscript -notmatch 'REFUSED: STEP08_RUN_ID_MISMATCH' -or $guardTranscript -notmatch 'ERROR:\s+22023\b') {
        throw 'Cleanup did not report the exact expected run-ID refusal.'
    }
    $guardOutput += 'PASS: Cleanup refuses a different run ID before removing any study object.'
    $observerOutput = @(Invoke-CrudExercise '/labs/step-08/reconnect.sql')
    $proofCompleted = $true
}
finally {
    # The baseline was committed for a real independent-connection proof.
    # Cleanup is attempted even after a failure and requires this exact run ID.
    $cleanupOutput = @(Invoke-CrudExercise '/labs/step-08/cleanup.sql')
    $cleanupCheckOutput = @(Invoke-CrudExercise '/labs/step-08/cleanup-check.sql')
    if (-not $proofCompleted) {
        $cleanupOutput | ForEach-Object { Write-Host "$_" }
        $cleanupCheckOutput | ForEach-Object { Write-Host "$_" }
    }
}

$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 8: SQL CRUD and transaction verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    "Lab run ID (synthetic cleanup marker, not a credential): $labRunId",
    "Different run ID used for the cleanup refusal proof: $differentRunId",
    'Two deliberate statement errors (23505, 25P02) and one cleanup refusal (22023) are asserted below.',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<run-id> --file /labs/step-08/query.sql',
    ($exerciseOutput -join "`n"),
    '',
    'Command (expected exit 3, SQLSTATE 22023): docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<different-run-id> --file /labs/step-08/cleanup.sql',
    ($guardOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<run-id> --file /labs/step-08/reconnect.sql',
    ($observerOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<run-id> --file /labs/step-08/cleanup.sql',
    ($cleanupOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=lab_run_id=<run-id> --file /labs/step-08/cleanup-check.sql',
    ($cleanupCheckOutput -join "`n")
) -join "`n"
Write-Output $transcript

if ($WriteEvidence) {
    $evidenceFile = Join-Path $PSScriptRoot 'evidence.txt'
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($evidenceFile, $transcript + "`n", $utf8)
    Write-Output "Evidence saved: $evidenceFile"
}
