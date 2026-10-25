[CmdletBinding()]
param([switch]$WriteEvidence,[string]$PythonExecutable)
. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '31' -Title 'Measure lazy relationship queries' `
    -ExpectedBehavior 'Assertions, independent observation, and exact-run cleanup are required.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
