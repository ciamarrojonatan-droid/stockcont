@echo off
title StockCont - Conta 1 (Raw Producer)
cd /d "%~dp0"
echo ========================================================
echo  StockCont - Iniciando Conta 1 (Raw Producer)
echo  Workflow: 2113606426114670593 (Entrada 42 Nos PromptList / Saida #121)
echo  Capacidade: ate 210 prompts por execucao (janela de 40 min)
echo ========================================================

if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_BIN=%~dp0venv\Scripts\python.exe"
) else if exist "C:\Program Files\Python311\python.exe" (
    set "PY_BIN=C:\Program Files\Python311\python.exe"
) else (
    set "PY_BIN=python"
)

"%PY_BIN%" main.py --phase 3 --account 1 --batch-size 210
pause
