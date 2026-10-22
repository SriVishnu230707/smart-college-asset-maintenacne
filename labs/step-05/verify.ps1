[CmdletBinding()]
param([switch]$WriteEvidence, [string]$PythonExecutable)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$composeFile = Join-Path $projectRoot 'compose.yaml'

if (-not $PythonExecutable) {
    $installedPython = Get-Command python3, python -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Source -notmatch '[\\/]WindowsApps[\\/]' } | Select-Object -First 1
    if ($installedPython) {
        $PythonExecutable = $installedPython.Source
    } else {
        $profileDirectory = [Environment]::GetFolderPath('UserProfile')
        $bundledPython = Join-Path $profileDirectory '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
        if (Test-Path -LiteralPath $bundledPython) { $PythonExecutable = $bundledPython }
    }
}
if (-not $PythonExecutable) {
    throw 'Python 3.10+ is required. Supply -PythonExecutable and install labs/step-05/requirements.txt.'
}

function Invoke-MoneyTimeExercise([string]$SqlFile) {
    $result = @(& docker compose --file $composeFile exec -T postgres sh /labs/step-02/psql.sh --file $SqlFile 2>&1)
    if ($LASTEXITCODE -ne 0) {
        $result | ForEach-Object { Write-Host "$_" }
        throw "Step 5 money/time exercise failed: $SqlFile"
    }
    return ($result | ForEach-Object { "$($_)".TrimEnd() })
}

$sqlOutput = @(Invoke-MoneyTimeExercise '/labs/step-05/query.sql')
$reconnectOutput = @(Invoke-MoneyTimeExercise '/labs/step-05/reconnect.sql')
$fixtureLines = @($sqlOutput | Where-Object { $_.StartsWith('PYTHON_FIXTURE=') })
if ($fixtureLines.Count -ne 1) { throw 'Expected one PostgreSQL result payload for the Python exercise.' }
$payload = $fixtureLines[0].Substring('PYTHON_FIXTURE='.Length)
$pythonScript = Join-Path $PSScriptRoot 'python_lab.py'
$pythonOutput = @($payload | & $PythonExecutable -B $pythonScript 2>&1)
if ($LASTEXITCODE -ne 0) {
    $pythonOutput | ForEach-Object { Write-Host "$_" }
    throw 'Python Decimal/datetime verification failed. Check Python 3.10+ and the lab requirements.'
}
$capturedAt = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330)).ToString('yyyy-MM-dd HH:mm:ss zzz')
$transcript = @(
    'Step 5: money and time verification evidence',
    "Captured (Asia/Kolkata): $capturedAt",
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-05/query.sql',
    ($sqlOutput -join "`n"),
    '',
    'Command: docker compose exec -T postgres sh /labs/step-02/psql.sh --file /labs/step-05/reconnect.sql',
    ($reconnectOutput -join "`n"),
    '',
    'Command: python -B labs/step-05/python_lab.py (PostgreSQL JSON fixture on stdin)',
    (($pythonOutput | ForEach-Object { "$($_)".TrimEnd() }) -join "`n")
) -join "`n"
Write-Output $transcript
if ($WriteEvidence) {
    $evidenceFile = Join-Path $PSScriptRoot 'evidence.txt'
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($evidenceFile, $transcript + "`n", $utf8)
    Write-Output "Evidence saved: $evidenceFile"
}
