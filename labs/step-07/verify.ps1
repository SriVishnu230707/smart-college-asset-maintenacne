[CmdletBinding()]
param([switch]$WriteEvidence)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')

$exerciseOutput = @(Invoke-LabSql '/labs/step-07/query.sql')
$reconnectOutput = @(Invoke-LabSql '/labs/step-07/reconnect.sql')
$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 7: referential-integrity verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-07/query.sql',
    ($exerciseOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-07/reconnect.sql',
    ($reconnectOutput -join "`n")
) -join "`n"
Write-LabEvidence -Transcript $transcript -Path (Join-Path $PSScriptRoot 'evidence.txt') -Save:$WriteEvidence
