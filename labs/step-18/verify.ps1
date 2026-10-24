[CmdletBinding()]
param([switch]$WriteEvidence, [string]$PythonExecutable)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '18' -Title 'ORM Session persistence and resource cleanup' `
    -ExpectedBehavior 'Application rollback, duplicate code (23505), referenced deletion (23001), and cleanup refusal (22023) are deliberate and asserted.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
