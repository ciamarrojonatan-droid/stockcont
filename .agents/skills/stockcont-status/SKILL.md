---
name: stockcont-status
description: >-
  Displays real-time pipeline status for StockCont across all 5 phases:
  trends mined, ready prompts, generation progress, cataloged assets,
  and agency upload history. Synchronizes state.md automatically.
---

# StockCont Status Command

This command audits the live status of the 5-phase StockCont pipeline and synchronizes `state.md`.

## Execution Workflow

1. **Query Metrics via CLI**:
   Run the master orchestrator status check:
   ```powershell
   .\venv\Scripts\python.exe main.py --status
   ```

2. **Inspect Underlying Ledgers**:
   - `data/raw/trends.json`: Count scraped trends and raw reference images in `data/raw/images/`.
   - `data/processed/prompts.json`: Count analyzed items and ready 700-1000 word prompts.
   - `data/processed/generation_history.json`: Count SHA-256 registered generations.
   - `data/final/images/`: Count rendered 4K assets.
   - `data/processed/adobe_stock_upload.csv`: Count cataloged assets with IPTC/EXIF.
   - `data/processed/upload_history.json`: Count successfully distributed assets across configured agencies.

3. **Update `state.md`**:
   Reflect the real metrics in the `state.md` table, updating timestamps and recommended next steps.

4. **Output Structured Report**:
   Present the status clearly to the user with a recommended single next action.
