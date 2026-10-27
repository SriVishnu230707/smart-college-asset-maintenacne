[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet(51,61,71)][int]$FromStep)
$ErrorActionPreference='Stop'
$through=$FromStep+9
foreach ($shell in @('pwsh','powershell.exe')) {
    & $shell -NoProfile -File (Join-Path $PSScriptRoot 'run.ps1') -FromStep $FromStep -ThroughStep $through -WriteEvidence
    if ($LASTEXITCODE -ne 0) { throw "Debug checkpoint $FromStep-$through failed in $shell" }
}
