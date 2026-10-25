[CmdletBinding()]
param([switch]$WriteEvidence,[string]$PythonExecutable)
. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '22' -Title 'Bidirectional relationships' `
    -ExpectedBehavior 'A missing parent deliberately raises 23503; exact-run cleanup refusal raises 22023.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
