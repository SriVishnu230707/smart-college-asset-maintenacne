# Run from PowerShell: .\labs\step-02\start.ps1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$composeFile = Join-Path $projectRoot 'compose.yaml'
$secretDirectory = Join-Path $projectRoot '.local'

& docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) {
    throw 'Docker is not ready. Run docker desktop start, wait for the engine, then run this script again.'
}

[System.IO.Directory]::CreateDirectory($secretDirectory) | Out-Null
foreach ($name in @('postgres-admin-password', 'college-learner-password')) {
    $secretFile = Join-Path $secretDirectory $name
    if (-not (Test-Path -LiteralPath $secretFile)) {
        $secretBytes = New-Object byte[] 32
        $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $generator.GetBytes($secretBytes) } finally { $generator.Dispose() }
        $secretValue = [System.BitConverter]::ToString($secretBytes).Replace('-', '').ToLowerInvariant()
        $utf8 = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($secretFile, $secretValue + "`n", $utf8)
    }
}

& docker compose --file $composeFile config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose configuration is invalid.' }

& docker compose --file $composeFile up --detach --wait --wait-timeout 60 postgres
if ($LASTEXITCODE -ne 0) { throw 'The learning database did not become ready. Inspect docker compose logs postgres.' }

Write-Output 'Learning database is ready: college_learning; role: college_learner.'
Write-Output 'Connect: docker compose exec postgres sh /labs/step-02/psql.sh'
Write-Output 'Inspect and verify: .\labs\step-02\verify.ps1 -WriteEvidence'
