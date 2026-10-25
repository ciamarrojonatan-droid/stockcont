<#
.SYNOPSIS
    StockCont - PowerShell Automated Pipeline Runner
.DESCRIPTION
    Script resiliente com suporte a encoding UTF-8, checagem de integridade,
    execucao parametrizada e saida colorida para a esteira StockCont.
.EXAMPLE
    .\scripts\run_pipeline.ps1 -Status
    .\scripts\run_pipeline.ps1 -Phase 2
    .\scripts\run_pipeline.ps1 -All -Query "biotech lab"
#>

[CmdletBinding()]
param (
    [switch]$Status,
    [int]$Phase,
    [string]$Query,
    [switch]$Seasonal,
    [switch]$Backup,
    [switch]$All,
    [switch]$Dashboard,
    [int]$Batches = 1,
    [switch]$AllBatches,
    [string]$Platform = "all",
    [switch]$DryRun
)

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      StockCont Industrial Pipeline Runner (PowerShell)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$PythonPath = Join-Path $RootDir "venv\Scripts\python.exe"

if (-not (Test-Path $PythonPath)) {
    Write-Host "[ERRO] Python virtualenv nao localizado em $PythonPath" -ForegroundColor Red
    exit 1
}

$Arguments = @()

if ($Status) {
    $Arguments += "--status"
} elseif ($Seasonal) {
    $Arguments += "--seasonal"
} elseif ($Backup) {
    $Arguments += "--backup"
} elseif ($Dashboard) {
    $Arguments += "--dashboard"
} elseif ($All) {
    $Arguments += "--all"
    if ($Query) { $Arguments += @("-q", $Query) }
    if ($AllBatches) { $Arguments += "--all-batches" }
} elseif ($Phase -gt 0) {
    $Arguments += @("--phase", $Phase)
    if ($Query) { $Arguments += @("-q", $Query) }
    if ($Phase -eq 3) {
        if ($AllBatches) {
            $Arguments += "--all-batches"
        } elseif ($Batches -gt 1) {
            $Arguments += @("--batches", $Batches)
        }
    }
    if ($Phase -eq 5) {
        if ($Platform) { $Arguments += @("--platform", $Platform) }
        if ($DryRun) { $Arguments += "--dry-run" }
    }
} else {
    $Arguments += "--status"
}

$ArgsStr = $Arguments -join " "
Write-Host "[EXEC] $PythonPath main.py $ArgsStr" -ForegroundColor Yellow

& $PythonPath main.py @Arguments

$ExitCode = $LASTEXITCODE
if ($ExitCode -eq 0) {
    Write-Host "`n[OK] Execucao concluida com sucesso." -ForegroundColor Green
} else {
    Write-Host "`n[ERRO] O comando falhou com codigo de saida $ExitCode." -ForegroundColor Red
}

exit $ExitCode
