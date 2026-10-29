<#
.SYNOPSIS
    Configura o StockCont Daemon 24/7 no Agendador de Tarefas do Windows (Task Scheduler).
.DESCRIPTION
    Cria uma tarefa agendada no Windows para iniciar automaticamente o run_24_7.bat
    sempre que o usuário fizer logon no computador, mantendo a fábrica operando continuamente.
.PARAMETER Action
    "install" para criar a tarefa ou "uninstall" para removê-la.
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("install", "uninstall", "status")]
    [string]$Action = "install"
)

$TaskName = "StockCont_Production_24_7"
$ScriptDir = Split-Path -Parent $PSScriptRoot
$BatPath = Join-Path $ScriptDir "run_24_7.bat"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  StockCont — Windows Task Scheduler Automation (24/7)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

if ($Action -eq "status") {
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "✓ Tarefa '$TaskName' ESTÁ instalada e ativa no Windows." -ForegroundColor Green
        Write-Host "  Estado: $($existingTask.State)"
    } else {
        Write-Host "✗ Tarefa '$TaskName' NÃO está instalada." -ForegroundColor Yellow
    }
    exit 0
}

if ($Action -eq "uninstall") {
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "✓ Tarefa '$TaskName' removida com sucesso do Agendador de Tarefas." -ForegroundColor Green
    } else {
        Write-Host "ℹ️ Tarefa '$TaskName' não foi encontrada para remoção." -ForegroundColor Gray
    }
    exit 0
}

# Install Task
if (-not (Test-Path $BatPath)) {
    Write-Error "Arquivo '$BatPath' não encontrado!"
    exit 1
}

$ActionObj = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatPath`"" -WorkingDirectory $ScriptDir
$TriggerObj = New-ScheduledTaskTrigger -AtLogOn
$SettingsObj = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

try {
    # Remove previous task if exists
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

    Register-ScheduledTask -TaskName $TaskName -Action $ActionObj -Trigger $TriggerObj -Settings $SettingsObj -Description "Inicia o StockCont Daemon 24/7 na inicialização do Windows"
    Write-Host "✓ Tarefa '$TaskName' registrada com sucesso!" -ForegroundColor Green
    Write-Host "  • Gatilho: No logon do usuário" -ForegroundColor Gray
    Write-Host "  • Script: $BatPath" -ForegroundColor Gray
    Write-Host "  • Auto-restart em falhas: Ativo" -ForegroundColor Gray
    Write-Host "Para remover no futuro, execute: .\scripts\setup_windows_task.ps1 uninstall" -ForegroundColor Cyan
} catch {
    Write-Error "Falha ao registrar a tarefa no Agendador do Windows: $_"
}
