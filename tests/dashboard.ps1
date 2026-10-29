#Requires -Version 5.1
[CmdletBinding()]
param([switch]$WriteEvidence)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$python = Join-Path $project '.venv/Scripts/python.exe'
Push-Location $project
try {
    # unittest writes progress to stderr even on success. Read both streams
    # directly so Windows PowerShell does not turn it into NativeCommandError.
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $python
    $start.Arguments = '-X utf8 -m unittest tests.dashboard_cases -v'
    $start.WorkingDirectory = $project
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        $output = @(($stdout.Result + $stderr.Result).TrimEnd([char[]]"`r`n") -split '\r?\n')
        $code = $process.ExitCode
    } finally { $process.Dispose() }
    $report = @("Dashboard verification: PowerShell $($PSVersionTable.PSVersion)", "Captured (UTC): $([DateTimeOffset]::UtcNow.ToString('u'))") + $output
    $report | Write-Output
    if ($WriteEvidence) {
        $suffix = if ($PSVersionTable.PSVersion.Major -ge 7) { '7' } else { '5' }
        $path = Join-Path $PSScriptRoot "dashboard-evidence-powershell$suffix.txt"
        [IO.File]::WriteAllLines($path, $report, (New-Object Text.UTF8Encoding($false)))
    }
    if ($code -ne 0) { throw "Dashboard verification failed ($code)." }
} finally { Pop-Location }
