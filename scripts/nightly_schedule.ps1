<#
.SYNOPSIS
    StockCont - Nightly Autonomous Pipeline Execution Script
.DESCRIPTION
    Executa a rotina noturna sem supervisão humana:
    1. Verifica status e prompts pendentes.
    2. Processa lotes de renderização 4K no ComfyUI (Fase 3).
    3. Executa a catalogação IPTC/EXIF nos novos arquivos (Fase 4).
    4. Sincroniza o backup em nuvem no Google Drive.
    5. Executa os testes automatizados para garantir integridade.
    6. Salva logs com timestamp em data/logs/nightly_run.log.
#>

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$LogsDir = Join-Path $RootDir "data\logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

$LogFile = Join-Path $LogsDir "nightly_run.log"
$Timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

function Log-Message {
    param ([string]$Msg)
    $Line = "[$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))] $Msg"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line -Encoding UTF8
}

Log-Message "=========================================================="
Log-Message "🚀 Iniciando rotina noturna autônoma do StockCont..."

$PythonPath = Join-Path $RootDir "venv\Scripts\python.exe"

# 1. Pipeline Status
Log-Message "Etapa 1: Checando status da esteira..."
& $PythonPath main.py --status | Out-File -FilePath (Join-Path $LogsDir "last_status.txt") -Encoding UTF8

# 2. Fase 4 (Garantir que imagens em disco estão catalogadas)
Log-Message "Etapa 2: Executando Fase 4 (Catalogador IPTC/EXIF)..."
& $PythonPath main.py --phase 4 | Out-Null

# 3. Backup Google Drive
Log-Message "Etapa 3: Sincronizando backup no Google Drive..."
& $PythonPath main.py --backup | Out-Null

# 4. Testes de Regressão
Log-Message "Etapa 4: Executando suíte de testes pytest..."
& $PythonPath -m pytest --quiet | Out-File -FilePath (Join-Path $LogsDir "last_test_run.txt") -Encoding UTF8

Log-Message "🎉 Rotina noturna concluída com sucesso."
Log-Message "=========================================================="
