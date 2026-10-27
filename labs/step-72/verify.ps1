[CmdletBinding()]
param([switch]$WriteEvidence,[string]$PythonExecutable)
. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '72' -Title 'Custom types and attribute validation' `
    -ExpectedBehavior 'Real PostgreSQL assertions, independent observation, and exact-run cleanup are required.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
