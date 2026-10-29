#Requires -Version 5.1
[CmdletBinding()]
param([switch]$WriteEvidence)
. (Join-Path $PSScriptRoot '../labs/shared/verify.ps1')
$report = @(
    "Dashboard async regression: PowerShell $($PSVersionTable.PSVersion)",
    "Captured (UTC): $([DateTimeOffset]::UtcNow.ToString('u'))"
)
$report += Invoke-LabProcess node @('--version')
$report += Invoke-LabProcess node @('--test', (Join-Path $PSScriptRoot 'dashboard-async.test.cjs'))
$suffix = if ($PSVersionTable.PSVersion.Major -ge 7) { '7' } else { '5' }
Write-LabEvidence -Transcript ($report -join "`n") -Path (Join-Path $PSScriptRoot "dashboard-async-evidence-powershell$suffix.txt") -Save:$WriteEvidence
