@echo off
:: ============================================================================
:: StockCont - Automated Pipeline Runner (Windows Batch)
:: Garante UTF-8, valida venv e executa fases do pipeline
:: ============================================================================

chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%"

echo ============================================================================
echo   [StockCont] Disparando Pipeline de Automacao Industrial
echo ============================================================================

:: 1. Validar ambiente virtual Python
if not exist "venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual venv nao encontrado!
    echo Execute: python -m venv venv ^&^& .\venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

:: 2. Executar com argumentos passados ou status padrao
if "%~1"=="" (
    echo [INFO] Nenhum argumento informado. Exibindo status da esteira:
    venv\Scripts\python.exe main.py --status
) else (
    echo [INFO] Executando comando: python main.py %*
    venv\Scripts\python.exe main.py %*
)

set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% equ 0 (
    echo [SUCESSO] Operacao finalizada com codigo 0.
) else (
    echo [FALHA] Processo terminou com erro: %EXIT_CODE%
)

exit /b %EXIT_CODE%
