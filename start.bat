@echo off
setlocal
title StockCont Dashboard Server

echo ============================================================
echo        StockCont - AI Stock Asset Automation Pipeline
echo                 Iniciando Dashboard Web SPA
echo ============================================================
echo.

cd /d "%~dp0"

if not exist "%~dp0venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual 'venv' nao encontrado em:
    echo        %~dp0venv
    echo.
    echo Por favor, crie o ambiente virtual primeiro com:
    echo   python -m venv venv
    echo   .\venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [INFO] Inicializando servidor Uvicorn em http://localhost:8501...
echo [INFO] O navegador abrira automaticamente em alguns segundos.
echo [INFO] Para encerrar o Dashboard, pressione Ctrl+C nesta janela.
echo.

"%~dp0venv\Scripts\python.exe" main.py --dashboard

if errorlevel 1 (
    echo.
    echo [AVISO] O servidor foi encerrado ou encontrou um erro.
    pause
)
