---
name: stockcont-deploy
description: >-
  Pre-flight validation and startup of the local FastAPI Web SPA Dashboard
  with health checks, test gates, and process management. Use when running /deploy.
---

# StockCont Deploy & Launch Orchestrator (`/deploy`)

Workflow para validação de integridade pré-deploy e inicialização do servidor Web SPA do StockCont.

## 🧭 Etapas do Procedimento

### Passo 1: Gate de Testes Automatizados
Antes de subir qualquer processo, a esteira executa os testes para garantir estabilidade:
```powershell
.\venv\Scripts\python.exe -m pytest
```
Se algum teste falhar, o deploy é abortado imediatamente com diagnóstico do erro.

### Passo 2: Verificação de Ambiente (.env)
- Checa a presença do arquivo `.env`.
- Valida se `GEMINI_API_KEY` está preenchida.
- Verifica se a porta `8501` está livre para bind.

### Passo 3: Inicialização do Servidor FastAPI
O servidor é iniciado em background:
```powershell
.\venv\Scripts\python.exe main.py --dashboard --no-browser --port 8501
```

### Passo 4: Health-Check HTTP
O assistente realiza uma requisição de health check no endpoint local:
```powershell
Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 5
```
Se retornar `StatusCode: 200`, o serviço é considerado operacional.

### Passo 5: Confirmação Operacional
Apresenta o painel com:
- URL de acesso: `http://localhost:8501`
- Status dos KPIs em tempo real
- Link para a Matriz de Distribuição e Galeria IPTC/EXIF
