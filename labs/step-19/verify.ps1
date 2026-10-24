[CmdletBinding()]
param([switch]$WriteEvidence, [string]$PythonExecutable)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '19' -Title 'ORM object lifecycle and unit-of-work' `
    -ExpectedBehavior 'Lifecycle and rollback transitions are asserted; cleanup refusal (22023) is deliberate and asserted.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
