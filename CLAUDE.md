# StockCont — Claude Code Dual-Mode Operating Instructions

@[Project Architecture & Context](PROJECT_CONTEXT.md)

This repository is configured for dual-mode execution between **Claude Code** and **Antigravity**. Both agents share `PROJECT_CONTEXT.md` as the authoritative Single Source of Truth (SSOT).

---

## ⚡ Quick Start & Primary Commands

### Environment & Setup
- **Activate Python venv (Windows)**: `.\venv\Scripts\Activate.ps1` or `venv\Scripts\activate.bat`
- **Install dependencies**: `pip install -r requirements.txt`
- **Install Playwright browsers**: `playwright install chromium`
- **Run automated test suite**: `pytest` (Expected: 69+ tests passing)

### Pipeline Phase Commands (`main.py`)
```bash
# Dashboard Web Interface (http://localhost:8501)
python main.py --dashboard

# Pipeline Status Overview
python main.py --status

# Predictive Seasonal Demand Radar (D+75 days)
python main.py --seasonal

# Phase 1: Trend & Contributor Insights Scout
python main.py --phase 1 --mode insights --type photo --max-items 20
python main.py --phase 1 --mode search --query "biotech lab" --order nb_downloads

# Phase 2: Art Director (Gemini Vision 700-1000 word prompts)
python main.py --phase 2

# Phase 3: The Factory RPA (RunningHub ComfyUI)
python main.py --phase 3 --node 192
python main.py --phase 3 --batches 5
python main.py --phase 3 --all-batches

# Phase 4: The Cataloger (IPTC/EXIF binary injection + CSV export)
python main.py --phase 4

# Cloud Backup: Google Drive
python main.py --backup

# Phase 5: The Distributor (SFTP/FTP Mass Upload)
python main.py --phase 5 --dry-run
python main.py --phase 5 --platform adobe
python main.py --phase 5 --platform all
```

---

## 🛡️ Coding & Architectural Standards

1. **UTF-8 Console & I/O**: Always ensure scripts configure UTF-8 encoding on Windows to prevent `cp1252` encoding exceptions.
2. **Atomic Writes**: When updating critical JSON files (`prompts.json`, `generation_history.json`, `upload_history.json`), write to `.tmp` first and replace atomically.
3. **SHA-256 Ledger**: Never bypass the prompt queue manager (`src/factory/prompt_queue.py`). Prompts must have canonical SHA-256 hashes to prevent duplicate GPU runs.
4. **Binary Metadata Integrity**: Never corrupt IPTC or EXIF headers in JPG files. Follow the compliance rules in `src/cataloger/adobe_csv_maker.py`.
5. **State Synchronization**: Always keep `state.md` updated with the latest pipeline metrics.
