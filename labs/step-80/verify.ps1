[CmdletBinding()]
param([switch]$WriteEvidence,[string]$PythonExecutable)
. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '80' -Title 'Independent feature and reference audit' `
    -ExpectedBehavior 'Real PostgreSQL assertions, independent observation, and exact-run cleanup are required.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
