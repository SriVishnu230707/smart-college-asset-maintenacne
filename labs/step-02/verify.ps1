[CmdletBinding()]
param([switch]$WriteEvidence)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')

$first = @(Invoke-LabSql '/labs/step-02/query.sql')
$second = @(Invoke-LabSql '/labs/step-02/reconnect.sql')
$firstText = $first -join "`n"
$secondText = $second -join "`n"
$firstPid = [regex]::Match($firstText, '(?m)^connection_backend_pid=(\d+)\s*$')
$secondPid = [regex]::Match($secondText, '(?m)^connection_backend_pid=(\d+)\s*$')
if (-not $firstPid.Success -or -not $secondPid.Success) { throw 'Connection identifiers are missing from the inspection output.' }
if ($firstPid.Groups[1].Value -eq $secondPid.Groups[1].Value) { throw 'Expected distinct PostgreSQL backend identifiers for separate connections.' }

$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 2: PostgreSQL inspection evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-02/query.sql',
    $firstText,
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-02/reconnect.sql',
    $secondText,
    '',
    'PASS: The two psql invocations used different PostgreSQL backend identifiers.'
) -join "`n"
Write-LabEvidence -Transcript $transcript -Path (Join-Path $PSScriptRoot 'evidence.txt') -Save:$WriteEvidence
