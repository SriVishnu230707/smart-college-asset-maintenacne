[CmdletBinding()]
param([switch]$WriteEvidence,[string]$PythonExecutable)
. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '49' -Title 'Aggregate reports before child joins' `
    -ExpectedBehavior 'Assertions, independent observation, and exact-run cleanup are required.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
