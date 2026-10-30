# StockCont — Claude Code Dual-Mode Operating Instructions

@[Project Architecture & Context](PROJECT_CONTEXT.md)

This repository is configured for dual-mode execution between **Claude Code** and **Antigravity**. Both agents share `PROJECT_CONTEXT.md` as the authoritative Single Source of Truth (SSOT).

---

## ⚡ Quick Start & Primary Commands

### Environment & Setup
- **Activate Python venv (Windows)**: `.\venv\Scripts\Activate.ps1` or `venv\Scripts\activate.bat`
- **Install dependencies**: `pip install -r requirements.txt`
- **Install Playwright browsers**: `playwright install chromium`
- **Run automated test suite**: `.\venv\Scripts\pytest` (Expected: **131 tests passing 100%**)

### Pipeline Phase Commands (`main.py`)
```bash
# Dashboard Web Interface (Apple iOS 27 Liquid Glass - http://localhost:8501)
python main.py --dashboard

# Pipeline Status Overview & Weekly Quotas
python main.py --status
python main.py --quotas

# Predictive Seasonal Demand Radar (D+75 days)
python main.py --seasonal

# 24/7 Production Daemon & Watchdog
python main.py --daemon
.\run_24_7.bat

# Phase 1: Trend & Contributor Insights Scout
python main.py --phase 1 --mode insights --type photo --max-items 20
python main.py --phase 1 --mode search --query "biotech lab" --order nb_downloads
python main.py --sync-raw

# Phase 2: Art Director (Gemini Vision 700-1000 word prompts)
python main.py --phase 2

# Video Pipeline (4D Temporal Prompts, Mute -an, MP4 Atoms & ProRes)
python main.py --video --phase 2
python main.py --video --phase 4
python main.py --video --phase 4 --prores

# Phase 3: The Factory RPA Dual-Account (RunningHub ComfyUI)
python main.py --phase 3 --account 1 --batch-size 210
.\run_conta1.bat
python main.py --qc --qc-mode auto
python main.py --phase 3 --account 2 --batch-size 10
python main.py --upscale
.\run_conta2.bat

# Phase 4: The Cataloger (IPTC/EXIF 300 DPI binary injection + CSV export)
python main.py --phase 4

# The Vault: Google Drive Backup & Restore
python main.py --backup
python main.py --restore

# Phase 5: The Distributor (SFTP/FTP Mass Upload with Rolling 7D Quotas)
python main.py --phase 5 --dry-run
python main.py --phase 5 --platform all
python main.py --phase 5 --platform adobe
```

---

## 🛡️ Coding & Architectural Standards

1. **UTF-8 Console & I/O (ADR-01)**: Always ensure scripts configure UTF-8 encoding on Windows consoles to prevent `cp1252` encoding exceptions.
2. **Atomic Writes (ADR-02)**: When updating critical JSON files (`prompts.json`, `generation_history.json`, `upload_history.json`, `daemon_state.json`), write to `.tmp` first and replace atomically via `os.replace()`.
3. **SHA-256 Ledger (ADR-03)**: Never bypass the prompt queue manager (`src/factory/prompt_queue.py`). Prompts must have canonical SHA-256 hashes to prevent duplicate GPU runs.
4. **Binary Metadata Integrity (ADR-04)**: Never corrupt IPTC or EXIF headers in JPG files or atoms in MP4 containers. Follow compliance rules in `src/cataloger/adobe_csv_maker.py` and `src/cataloger/platform_compliance.py`.
5. **Strict Anti-Ban Protection (ADR-05)**: Alamy strictly forbids AI content. Never bypass the programatic block in `src/cataloger/platform_compliance.py`.
6. **Dual-Account RPA Topology (ADR-06)**: Maintain strict isolation between Conta 1 (Raw Producer up to 210 prompts) and Conta 2 (SeedVR 8K with curated 10-packs to prevent GPU OOM).
7. **Safe SSD Auto-Purge (ADR-07)**: Local disk space is reclaimed by the 24/7 daemon only after verified upload to all configured agencies AND confirmation in Google Drive.
8. **State Synchronization**: Always keep `state.md` updated with real metrics and test results.
9. **Mandatory Git Protocol**: Every completed sprint or feature cycle must pass tests, sync `state.md`, commit and push to remote (`git push origin master`).
