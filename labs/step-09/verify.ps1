[CmdletBinding()]
param([switch]$WriteEvidence)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$composeFile = Join-Path $projectRoot 'compose.yaml'

function Invoke-FilterExercise([string]$SqlFile) {
    $result = @(& docker compose --file $composeFile exec -T postgres sh /labs/step-02/psql.sh --file $SqlFile 2>&1)
    if ($LASTEXITCODE -ne 0) {
        $result | ForEach-Object { Write-Host "$_" }
        throw "Step 9 filtering/ordering exercise failed: $SqlFile"
    }
    return ($result | ForEach-Object { "$($_)".TrimEnd() })
}

$exerciseOutput = @(Invoke-FilterExercise '/labs/step-09/query.sql')
$reconnectOutput = @(Invoke-FilterExercise '/labs/step-09/reconnect.sql')
$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 9: filtering and ordering verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-09/query.sql',
    ($exerciseOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-09/reconnect.sql',
    ($reconnectOutput -join "`n")
) -join "`n"
Write-Output $transcript

if ($WriteEvidence) {
    $evidenceFile = Join-Path $PSScriptRoot 'evidence.txt'
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($evidenceFile, $transcript + "`n", $utf8)
    Write-Output "Evidence saved: $evidenceFile"
}
