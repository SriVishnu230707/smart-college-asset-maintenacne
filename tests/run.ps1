#Requires -Version 5.1
[CmdletBinding()]
param([switch]$WriteEvidence, [string]$PythonExecutable)

. (Join-Path $PSScriptRoot '../labs/shared/verify.ps1')
$shellExecutable = (Get-Process -Id $PID).Path
$shellVersion = $PSVersionTable.PSVersion.ToString()
$logDirectory = Join-Path $projectRoot ".local/test-results/powershell-$shellVersion"
[IO.Directory]::CreateDirectory($logDirectory) | Out-Null
$report = @("Regression suite: PowerShell $shellVersion", "Captured (UTC): $([DateTimeOffset]::UtcNow.ToString('u'))")
$result = 'FAILED'
$expectedCounts = [ordered]@{ '02'=5; '03'=11; '04'=19; '05'=34; '06'=48; '07'=43; '08'=23; '09'=37; '10'=26; '11'=25; '12'=31; '13'=23; '14'=32; '15'=31; '16'=40; '17'=48; '18'=32; '19'=39; '20'=35; '21'=22; '22'=19; '23'=17; '24'=20 }

function Assert-Suite([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
    $script:report += "PASS: $Message"
    Write-Output "PASS: $Message"
}

# Verify that entry points resolve files using their own location, including
# the project path containing spaces and '&', rather than the caller's cwd.
Push-Location ([IO.Path]::GetTempPath())
try {
    & (Join-Path $projectRoot 'labs/step-02/start.ps1') | Out-Null
    Assert-Suite $true 'Database startup and Compose readiness succeed.'

    $sqlFiles = @(Get-ChildItem (Join-Path $projectRoot 'labs') -Recurse -Filter *.sql)
    foreach ($file in $sqlFiles) {
        $sql = [IO.File]::ReadAllText($file.FullName)
        if ($sql -match '(?m)^\s*\\quit\s+\d') { throw "Invalid numeric quit in $($file.Name)" }
        foreach ($include in [regex]::Matches($sql, '(?m)^\s*\\ir\s+([^\r\n]+)')) {
            $target = Join-Path $file.DirectoryName $include.Groups[1].Value.Trim()
            if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Missing SQL include: $target" }
        }
    }
    foreach ($file in Get-ChildItem $projectRoot -Recurse -Filter *.ps1 | Where-Object { $_.FullName -notmatch '[\\/]\.local[\\/]' }) {
        $tokens = $null
        $parseErrors = $null
        [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
        if ($parseErrors.Count) { throw "PowerShell syntax errors: $($file.FullName)" }
    }
    Assert-Suite $true 'PowerShell syntax, SQL include paths, and assertion-exit guards are valid.'

    foreach ($step in $expectedCounts.Keys) {
        $verifier = Join-Path $projectRoot "labs/step-$step/verify.ps1"
        $arguments = @('-NoProfile', '-NonInteractive', '-File', $verifier)
        if (($step -eq '05' -or [int]$step -ge 13) -and $PythonExecutable) { $arguments += @('-PythonExecutable', $PythonExecutable) }
        $output = @(Invoke-LabProcess $shellExecutable $arguments -LogPath (Join-Path $logDirectory "step-$step.txt"))
        $text = $output -join "`n"
        $passCount = [regex]::Matches($text, '(?m)^PASS:').Count
        Assert-Suite ($passCount -eq $expectedCounts[$step] -and $text -notmatch '(?m)FAIL:|WARNING:') "Step ${step}: $($expectedCounts[$step]) checks pass from an unrelated working directory."
    }

    $guard = @(Invoke-LabSql '/labs/step-04/query.sql' -PsqlArguments @('--set=VERBOSITY=sqlstate') -ExpectedExitCode 3) -join "`n"
    Assert-Suite ($guard -match 'FAIL: Supply a client-generated UUID' -and $guard -match 'ERROR:\s+P0001\b') 'Missing required UUID fails with psql exit 3 and SQLSTATE P0001.'

    $propagated = $false
    try { Invoke-LabSql '/labs/step-04/query.sql' | Out-Null } catch {
        if ($_.Exception.Message -notmatch 'exited 3 \(expected 0\)') { throw }
        $propagated = $true
    }
    Assert-Suite $propagated 'The shared runner propagates an unexpected nonzero SQL exit.'

    $stderr = @(Invoke-LabProcess $shellExecutable @('-NoProfile', '-NonInteractive', '-Command', "[Console]::Error.WriteLine('EXPECTED_STDERR'); exit 0")) -join "`n"
    Assert-Suite ($stderr -match 'EXPECTED_STDERR') 'Native stderr is captured without mistaking a successful process for a failure.'

    $missingPython = @(Invoke-LabProcess $shellExecutable @('-NoProfile', '-NonInteractive', '-File',
        (Join-Path $projectRoot 'labs/step-05/verify.ps1'), '-PythonExecutable',
        (Join-Path $logDirectory 'missing-python.exe')) -ExpectedExitCode 1) -join "`n"
    Assert-Suite ($missingPython -match 'No usable Python' -and $missingPython -notmatch 'Command: docker') 'An unavailable explicit Python produces a clear preflight failure before SQL runs.'

    foreach ($proof in @(& (Join-Path $PSScriptRoot 'runner-regressions.ps1'))) {
        $report += $proof
        Write-Output $proof
    }

    $remaining = @(Invoke-LabProcess docker @('compose', '--file', $composeFile, 'exec', '-T', 'postgres', 'sh',
        '/labs/step-02/psql.sh', '--tuples-only', '--no-align', '--command',
        "SELECT count(*) FROM pg_namespace WHERE nspname ~ '^college_step(0[2-9]|[12][0-9]|30)$'")) -join ''
    Assert-Suite ($remaining.Trim() -eq '0') 'A fresh connection confirms no implemented study schema remains.'
    $labCheckCount = ($expectedCounts.Values | Measure-Object -Sum).Sum
    $runnerCheckCount = @($report | Where-Object { $_ -like 'PASS:*' }).Count - $expectedCounts.Count
    $report += "Result: PASSED; $($expectedCounts.Count) lab suites, $labCheckCount lab checks, and $runnerCheckCount runner regression checks."
    $result = 'PASSED'
} finally {
    Pop-Location
    if ($result -ne 'PASSED') { $report += 'Result: FAILED; see the process error and local logs.' }
    $report += "Command: $shellExecutable -NoProfile -File tests/run.ps1 -WriteEvidence"
    $evidencePath = Join-Path $PSScriptRoot "evidence-powershell$($PSVersionTable.PSVersion.Major).txt"
    Write-LabEvidence -Transcript ($report -join "`n") -Path $evidencePath -Save:$WriteEvidence
}
