[CmdletBinding()]
param([switch]$WriteEvidence)

. (Join-Path $PSScriptRoot '../shared/verify.ps1')
Invoke-CommittedLab -Step '08' -Title 'SQL CRUD and transaction' -SqlOnly `
    -ExpectedBehavior 'Two deliberate statement errors (23505, 25P02) and one cleanup refusal (22023) are asserted below.' `
    -WriteEvidence:$WriteEvidence
