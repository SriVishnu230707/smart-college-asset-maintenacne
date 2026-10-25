[CmdletBinding()]
param([switch]$WriteEvidence,[string]$PythonExecutable)
. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '21' -Title 'Identity and freshness' `
    -ExpectedBehavior 'A merge race deliberately raises 23505; exact-run cleanup refusal raises 22023.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
