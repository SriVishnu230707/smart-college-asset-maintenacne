[CmdletBinding()]
param([switch]$WriteEvidence, [string]$PythonExecutable)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '14' -Title 'Core connections, bound values, and transaction' `
    -ExpectedBehavior 'The duplicate-code error (23505) and cleanup refusal (22023) are deliberate and asserted.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
