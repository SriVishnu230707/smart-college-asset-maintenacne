[CmdletBinding()]
param([switch]$WriteEvidence,[string]$PythonExecutable)
. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '27' -Title 'Safe populated-data evolution' `
    -ExpectedBehavior 'Relationship paths and exact-run cleanup refusal (22023) are asserted.' `
    -PythonExecutable $PythonExecutable -WriteEvidence:$WriteEvidence
