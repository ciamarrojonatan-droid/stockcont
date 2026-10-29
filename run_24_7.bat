@echo off
title StockCont - Producao Autonoma 24/7 (Supervisor Daemon)
cd /d "%~dp0"

echo ========================================================
echo   StockCont - Supervisor de Producao Autonoma 24/7
echo   Pipeline E2E Contínuo com Gestao de Cotas e Cofre
echo ========================================================

if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_BIN=%~dp0venv\Scripts\python.exe"
) else if exist "C:\Program Files\Python311\python.exe" (
    set "PY_BIN=C:\Program Files\Python311\python.exe"
) else (
    set "PY_BIN=python"
)

:DAEMON_LOOP
echo.
echo [%DATE% %TIME%] Iniciando Daemon 24/7 do StockCont...
echo Pressione Ctrl+C para encerrar manualmente.
echo.

"%PY_BIN%" main.py --daemon --daemon-interval 300 --min-buffer 50

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo ========================================================
echo [SUPERVISOR] O processo do Daemon encerrou com codigo %EXIT_CODE%.
echo [%DATE% %TIME%] Auto-recuperacao ativada. Reiniciando em 30 segundos...
echo ========================================================
timeout /t 30 /nobreak
goto DAEMON_LOOP
