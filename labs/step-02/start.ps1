# Run from PowerShell: .\labs\step-02\start.ps1
[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot '../shared/verify.ps1')
$secretDirectory = Join-Path $projectRoot '.local'

try {
    Invoke-LabProcess docker @('info', '--format', '{{.ServerVersion}}')
} catch {
    throw "Docker is not ready. Run docker desktop start, then retry. $($_.Exception.Message)"
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

Invoke-LabProcess docker @('compose', '--file', $composeFile, 'config', '--quiet')
Invoke-LabProcess docker @('compose', '--file', $composeFile, 'up', '--detach', '--wait', '--wait-timeout', '60', 'postgres')

Write-Output 'Learning database is ready: college_learning; role: college_learner.'
Write-Output 'Connect: docker compose exec postgres sh /labs/step-02/psql.sh'
Write-Output 'Inspect and verify: .\labs\step-02\verify.ps1 -WriteEvidence'
