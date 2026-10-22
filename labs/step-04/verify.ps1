[CmdletBinding()]
param([switch]$WriteEvidence)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$composeFile = Join-Path $projectRoot 'compose.yaml'
$applicationUuid = [guid]::NewGuid().ToString('D')

function Invoke-TypeExercise([string]$SqlFile, [string[]]$PsqlArguments = @()) {
    $result = @(& docker compose --file $composeFile exec -T postgres sh /labs/step-02/psql.sh @PsqlArguments --file $SqlFile 2>&1)
    if ($LASTEXITCODE -ne 0) {
        $result | ForEach-Object { Write-Host "$_" }
        throw "Step 4 identifier/type exercise failed: $SqlFile"
    }
    return ($result | ForEach-Object { "$($_)".TrimEnd() })
}

$exerciseOutput = @(Invoke-TypeExercise '/labs/step-04/query.sql' @("--set=application_uuid=$applicationUuid"))
$reconnectOutput = @(Invoke-TypeExercise '/labs/step-04/reconnect.sql')
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
Write-Output $transcript

if ($WriteEvidence) {
    $evidenceFile = Join-Path $PSScriptRoot 'evidence.txt'
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($evidenceFile, $transcript + "`n", $utf8)
    Write-Output "Evidence saved: $evidenceFile"
}
