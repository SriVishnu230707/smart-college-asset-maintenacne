[CmdletBinding()]
param([switch]$WriteEvidence,[string]$PythonExecutable)
. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '39' -Title 'Manage drafts and protect repair history' `
    -ExpectedBehavior 'Assertions, independent observation, and exact-run cleanup are required.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
