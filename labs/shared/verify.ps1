# Shared by the lab entry points; compatible with PowerShell 5.1 and 7.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$composeFile = Join-Path $projectRoot 'compose.yaml'

function Invoke-LabProcess {
    param([string]$FilePath, [string[]]$Arguments = @(),
          [int]$ExpectedExitCode = 0, [string]$InputText)

    $executable = (Get-Command $FilePath -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $previousPreference = $ErrorActionPreference
    try {
        # Windows PowerShell wraps native stderr in ErrorRecords. Capture it
        # without terminating early, then check the actual process exit code.
        $ErrorActionPreference = 'Continue'
        $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        if ($PSBoundParameters.ContainsKey('InputText')) {
            $result = @($InputText | & $executable @Arguments 2>&1)
        } else {
            $result = @(& $executable @Arguments 2>&1)
        }
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    $lines = @($result | ForEach-Object { "$($_)".TrimEnd() })
    if ($exitCode -ne $ExpectedExitCode) {
        throw "$FilePath exited $exitCode (expected $ExpectedExitCode).`n$($lines -join "`n")"
    }
    return $lines
}

function Invoke-LabSql {
    param([string]$SqlFile, [string[]]$PsqlArguments = @(), [int]$ExpectedExitCode = 0)
    Invoke-LabProcess -FilePath docker -ExpectedExitCode $ExpectedExitCode -Arguments (
        @('compose', '--file', $composeFile, 'exec', '-T', 'postgres', 'sh', '/labs/step-02/psql.sh') +
        $PsqlArguments + @('--file', $SqlFile))
}

function Write-LabEvidence {
    param([string]$Transcript, [string]$Path, [switch]$Save)
    Write-Output $Transcript
    if ($Save) {
        [IO.File]::WriteAllText($Path, $Transcript + "`n", (New-Object System.Text.UTF8Encoding($false)))
        Write-Output "Evidence saved: $Path"
    }
}
