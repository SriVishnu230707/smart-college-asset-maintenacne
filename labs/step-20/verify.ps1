[CmdletBinding()]
param([switch]$WriteEvidence, [string]$PythonExecutable)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '20' -Title 'Flush visibility, autoflush, and Session recovery' `
    -ExpectedBehavior 'CHECK rejection (23514), PendingRollbackError, and cleanup refusal (22023) are deliberate and asserted.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
