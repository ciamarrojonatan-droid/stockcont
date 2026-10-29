@echo off
title StockCont - Conta 2 (SeedVR 8K Upscaler)
cd /d "%~dp0"
echo ========================================================
echo  StockCont - Iniciando Conta 2 (SeedVR 8K Upscaler)
echo  Workflow: 2115663736840245249 (Entrada #5 / Saida #55)
echo  Limite Anti-OOM: Ate 10 imagens por lote de 40 min
echo ========================================================

if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_BIN=%~dp0venv\Scripts\python.exe"
) else if exist "C:\Program Files\Python311\python.exe" (
    set "PY_BIN=C:\Program Files\Python311\python.exe"
) else (
    set "PY_BIN=python"
)

"%PY_BIN%" main.py --phase 3 --account 2 --batch-size 10
pause
