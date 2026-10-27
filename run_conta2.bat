@echo off
title StockCont - Conta 2 (SeedVR 8K Upscaler)
cd /d "%~dp0"
echo ========================================================
echo  StockCont - Iniciando Conta 2 (SeedVR 8K Upscaler)
echo  Workflow: 2114903521153097729 (Entrada #5 / Saida #55)
echo  Limite Anti-OOM: Ate 10 imagens por lote de 40 min
echo ========================================================
python main.py --phase 3 --account 2 --batch-size 10
pause
