[CmdletBinding()]
param([switch]$WriteEvidence)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')

$modelOutput = @(Invoke-LabSql '/labs/step-03/query.sql')
$reconnectOutput = @(Invoke-LabSql '/labs/step-03/reconnect.sql')
$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 3: relational-model verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-03/query.sql',
    ($modelOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-03/reconnect.sql',
    ($reconnectOutput -join "`n")
) -join "`n"
Write-LabEvidence -Transcript $transcript -Path (Join-Path $PSScriptRoot 'evidence.txt') -Save:$WriteEvidence
