#Requires -Version 5.1
# Fault injection keeps cleanup-error tests independent of the database.
. (Join-Path $PSScriptRoot '../labs/shared/verify.ps1')
$runnerShell = (Get-Process -Id $PID).Path
$runnerLogDirectory = Join-Path $projectRoot '.local/test-results/runner-regressions'
[IO.Directory]::CreateDirectory($runnerLogDirectory) | Out-Null
$runnerLog = Join-Path $runnerLogDirectory "child-failure-$PID.txt"

function Assert-Runner([bool]$Condition, [string]$Message, [string]$Details) {
    if (-not $Condition) { throw "$Message $Details".TrimEnd() }
    Write-Output "PASS: $Message"
}

[IO.File]::WriteAllText($runnerLog, 'STALE_PASSED_LOG')
$processFailure = ''
try {
    Invoke-LabProcess $runnerShell @('-NoProfile', '-NonInteractive', '-Command',
        "[Console]::WriteLine('CURRENT_STDOUT'); [Console]::Error.WriteLine('CURRENT_STDERR'); exit 4") -LogPath $runnerLog | Out-Null
} catch { $processFailure = $_.Exception.Message }
$failedLog = [IO.File]::ReadAllText($runnerLog)
Assert-Runner ($processFailure -match 'exited 4 \(expected 0\)' -and $failedLog -match 'CURRENT_STDOUT' `
    -and $failedLog -match 'CURRENT_STDERR' -and $failedLog -notmatch 'STALE_PASSED_LOG') `
    'A failed child replaces stale logs with its current stdout/stderr before its exit is propagated.'

[IO.File]::WriteAllText($runnerLog, 'STALE_PASSED_LOG')
$launchFailed = $false
$launchError = ''
try {
    Invoke-LabProcess (Join-Path $runnerLogDirectory 'missing-process.exe') -LogPath $runnerLog | Out-Null
} catch { $launchFailed = $true; $launchError = $_.Exception.Message }
Assert-Runner ($launchFailed -and [IO.File]::ReadAllText($runnerLog) -eq '') `
    'An executable lookup failure clears an older log before attempting to launch.' $launchError

function Invoke-FakeCommittedLab([string]$Failure, [switch]$SqlOnly) {
    # These scoped replacements never invoke Docker or change tracked evidence.
    $calls = New-Object 'System.Collections.Generic.List[string]'
    $runIds = New-Object 'System.Collections.Generic.List[string]'
    $state = @{ run = ''; saved = $false }
    $stepCode = if ($SqlOnly) { '08' } else { '20' }
    function Resolve-LabPython {
        if ($SqlOnly) { throw 'SQL-only lab unexpectedly requested Python' }
        return 'synthetic-python'
    }
    function Invoke-LabProcess {
        param([string]$FilePath, [string[]]$Arguments)
        $state.run = $Arguments[-1]
        if ($Failure -eq 'Primary') { throw 'PRIMARY_LAB_FAILURE' }
        return 'PASS: Synthetic Python completed.'
    }
    function Invoke-LabSql {
        param([string]$SqlFile, [string[]]$PsqlArguments, [int]$ExpectedExitCode = 0)
        $calls.Add((Split-Path $SqlFile -Leaf))
        $runIds.Add($PsqlArguments[0].Substring('--set=lab_run_id='.Length))
        if ($SqlFile.EndsWith('/query.sql')) { $state.run = $runIds[-1] }
        if ($ExpectedExitCode -eq 3) { return "REFUSED: STEP${stepCode}_RUN_ID_MISMATCH", 'ERROR: 22023' }
        if ($SqlFile.EndsWith('/reconnect.sql') -and $Failure -eq 'Observer') { throw 'OBSERVER_FAILURE' }
        if ($SqlFile.EndsWith('/cleanup.sql') -and $Failure -in @('Primary', 'Cleanup')) { throw 'CLEANUP_FAILURE' }
        if ($SqlFile.EndsWith('/cleanup-check.sql') -and $Failure -eq 'Primary') { throw 'CLEANUP_CHECK_FAILURE' }
        return 'PASS: Synthetic SQL completed.'
    }
    function Write-LabEvidence {
        param([string]$Transcript, [string]$Path, [switch]$Save)
        $state.saved = $true
        return $Transcript
    }
    $message = ''
    $transcript = ''
    try {
        $transcript = @(Invoke-CommittedLab -Step $stepCode -Title 'Synthetic fault injection' -ExpectedBehavior 'Synthetic errors are asserted.' -WriteEvidence -SqlOnly:$SqlOnly) -join "`n"
    } catch { $message = $_.Exception.Message }
    return [pscustomobject]@{ Message = $message; Transcript = $transcript; Calls = $calls; RunIds = $runIds; State = $state }
}

$primary = Invoke-FakeCommittedLab 'Primary'
Assert-Runner ($primary.Message.StartsWith('PRIMARY_LAB_FAILURE') -and $primary.Message -match 'cleanup.sql: CLEANUP_FAILURE' `
    -and $primary.Message -match 'cleanup-check.sql: CLEANUP_CHECK_FAILURE' `
    -and ($primary.Calls -join ',') -eq 'cleanup.sql,cleanup-check.sql' `
    -and @($primary.RunIds | Where-Object { $_ -ne $primary.State.run }).Count -eq 0 -and -not $primary.State.saved) `
    'The original lab error and both cleanup errors survive, with both exact-run cleanup checks attempted and no success evidence.'

$observerFailure = Invoke-FakeCommittedLab 'Observer'
Assert-Runner ($observerFailure.Message -eq 'OBSERVER_FAILURE' `
    -and ($observerFailure.Calls -join ',') -eq 'cleanup.sql,reconnect.sql,cleanup.sql,cleanup-check.sql' `
    -and -not $observerFailure.State.saved) `
    'An observer failure is preserved while both cleanup checks still run.'

$cleanupFailure = Invoke-FakeCommittedLab 'Cleanup'
Assert-Runner ($cleanupFailure.Message -match 'The lab completed but cleanup failed.' `
    -and $cleanupFailure.Message -match 'cleanup.sql: CLEANUP_FAILURE' `
    -and $cleanupFailure.Calls[-1] -eq 'cleanup-check.sql' -and -not $cleanupFailure.State.saved) `
    'Cleanup failure after successful proofs still fails the run, attempts the independent check, and saves no success evidence.'

$success = Invoke-FakeCommittedLab 'Success'
Assert-Runner ($success.Message -eq '' -and $success.State.saved `
    -and ($success.Calls -join ',') -eq 'cleanup.sql,reconnect.sql,cleanup.sql,cleanup-check.sql' `
    -and $success.RunIds[0] -ne $success.State.run `
    -and @($success.RunIds | Select-Object -Skip 1 | Where-Object { $_ -ne $success.State.run }).Count -eq 0 `
    -and $success.Transcript -match 'PASS: Cleanup refuses a different run ID' `
    -and $success.Transcript -match 'cleanup-check.sql') `
    'The shared success path preserves the mismatched guard, exact-run observer/cleanup, and complete evidence transcript.'

$sqlOnly = Invoke-FakeCommittedLab 'Success' -SqlOnly
Assert-Runner ($sqlOnly.Message -eq '' -and $sqlOnly.State.saved `
    -and ($sqlOnly.Calls -join ',') -eq 'query.sql,cleanup.sql,reconnect.sql,cleanup.sql,cleanup-check.sql' `
    -and $sqlOnly.RunIds[1] -ne $sqlOnly.State.run `
    -and @($sqlOnly.RunIds | Select-Object -Skip 2 | Where-Object { $_ -ne $sqlOnly.State.run }).Count -eq 0 `
    -and $sqlOnly.Transcript -match '/labs/step-08/query.sql') `
    'The SQL-only lab keeps its guarded flow and evidence without resolving or launching Python.'
