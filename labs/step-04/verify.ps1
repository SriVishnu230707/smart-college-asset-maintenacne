[CmdletBinding()]
param([switch]$WriteEvidence)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')
$applicationUuid = [guid]::NewGuid().ToString('D')

$exerciseOutput = @(Invoke-LabSql '/labs/step-04/query.sql' @("--set=application_uuid=$applicationUuid"))
$reconnectOutput = @(Invoke-LabSql '/labs/step-04/reconnect.sql')
$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 4: identifier and ordinary-type verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    "Client-generated UUID ([guid]::NewGuid): $applicationUuid",
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --set=application_uuid=<client-generated-uuid> --file /labs/step-04/query.sql',
    ($exerciseOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-04/reconnect.sql',
    ($reconnectOutput -join "`n")
) -join "`n"
Write-LabEvidence -Transcript $transcript -Path (Join-Path $PSScriptRoot 'evidence.txt') -Save:$WriteEvidence
