[CmdletBinding()]
param([switch]$WriteEvidence)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$composeFile = Join-Path $projectRoot 'compose.yaml'

function Invoke-AggregateExercise([string]$SqlFile) {
    $result = @(& docker compose --file $composeFile exec -T postgres sh /labs/step-02/psql.sh --file $SqlFile 2>&1)
    if ($LASTEXITCODE -ne 0) {
        $result | ForEach-Object { Write-Host "$_" }
        throw "Step 11 aggregate exercise failed: $SqlFile"
    }
    return ($result | ForEach-Object { "$($_)".TrimEnd() })
}

$exerciseOutput = @(Invoke-AggregateExercise '/labs/step-11/query.sql')
$reconnectOutput = @(Invoke-AggregateExercise '/labs/step-11/reconnect.sql')
$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 11: aggregate verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-11/query.sql',
    ($exerciseOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-11/reconnect.sql',
    ($reconnectOutput -join "`n")
) -join "`n"
Write-Output $transcript

if ($WriteEvidence) {
    $evidenceFile = Join-Path $PSScriptRoot 'evidence.txt'
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($evidenceFile, $transcript + "`n", $utf8)
    Write-Output "Evidence saved: $evidenceFile"
}
