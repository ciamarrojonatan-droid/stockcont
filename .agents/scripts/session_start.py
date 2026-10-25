#!/usr/bin/env python3
"""SessionStart hook: show pipeline status and pending tasks at session start.

Reads state.md and key data files to build a welcome summary. Injected as
a systemMessage so it persists in conversation history for the full session.

Contract: SessionStart → input has common fields.
           Output: { "injectSteps": [...] }
"""
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

STATE_FILE = os.path.join(PROJECT_ROOT, "state.md")
TRENDS_FILE = os.path.join(PROJECT_ROOT, "data", "raw", "trends.json")
PROMPTS_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "prompts.json")
HISTORY_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "generation_history.json")
IMAGES_DIR = os.path.join(PROJECT_ROOT, "data", "final", "images")
UPLOAD_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "upload_history.json")


def count_json_items(filepath: str) -> int:
    """Count top-level items in a JSON array file."""
    if not os.path.isfile(filepath):
        return 0
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            return len(data)
        return 0
    except Exception:
        return 0


def count_images() -> int:
    """Count JPG/PNG files in the final images directory."""
    if not os.path.isdir(IMAGES_DIR):
        return 0
    count = 0
    for fname in os.listdir(IMAGES_DIR):
        if fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            count += 1
    return count


def count_prompts_total() -> int:
    """Count total individual prompts across all trend entries."""
    if not os.path.isfile(PROMPTS_FILE):
        return 0
    try:
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        total = 0
        if isinstance(data, list):
            for entry in data:
                prompts = entry.get("generated_prompts", [])
                total += len(prompts)
        return total
    except Exception:
        return 0


def read_state_summary() -> str:
    """Read the first section of state.md for quick context."""
    if not os.path.isfile(STATE_FILE):
        return "No state.md found."
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Return first 20 lines max
        return "".join(lines[:20]).strip()
    except Exception:
        return "Error reading state.md."


def main() -> None:
    try:
        _payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        pass

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    trends = count_json_items(TRENDS_FILE)
    prompts = count_prompts_total()
    generated = count_json_items(HISTORY_FILE)
    images = count_images()
    uploads = count_json_items(UPLOAD_FILE)

    welcome = (
        f"🚀 **StockCont Session Started** — {now}\n\n"
        f"## Pipeline Snapshot\n"
        f"| Metric | Count |\n"
        f"|:---|:---|\n"
        f"| Trends mined | {trends} |\n"
        f"| Prompts ready | {prompts} |\n"
        f"| Generation history | {generated} |\n"
        f"| Final images (4K) | {images} |\n"
        f"| Uploads completed | {uploads} |\n\n"
        f"**Mode**: Autonomous — execute tasks end-to-end, only ask human for "
        f"irrecoverable errors or business decisions.\n\n"
        f"Use `/status` to refresh, `/pipeline` to run phases, `/mine <niche>` "
        f"for one-shot niche exploration."
    )

    result = {
        "injectSteps": [
            {
                "systemMessage": {
                    "systemMessage": welcome
                }
            }
        ]
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
