"""Background task runner for pipeline phase execution.

Delegates work to main.py via subprocess so the dashboard
server never blocks and never modifies data files directly.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MAIN_PY = BASE_DIR / "main.py"
PYTHON = sys.executable

_running_tasks: Dict[str, asyncio.subprocess.Process] = {}


async def run_phase(phase: int, extra_args: Optional[List[str]] = None) -> Dict[str, str]:
    """Start a pipeline phase in a background subprocess."""
    task_key = f"phase-{phase}"

    if task_key in _running_tasks and _running_tasks[task_key].returncode is None:
        return {"success": False, "message": f"Phase {phase} is already running", "task_id": task_key}

    cmd = [PYTHON, str(MAIN_PY), "--phase", str(phase)]
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Starting Phase %d: %s", phase, " ".join(cmd))

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
        )
        _running_tasks[task_key] = process
        asyncio.create_task(_monitor_task(task_key, process))
        return {"success": True, "message": f"Phase {phase} started", "task_id": task_key}
    except Exception as e:
        logger.error("Failed to start Phase %d: %s", phase, e)
        return {"success": False, "message": str(e), "task_id": None}


async def run_backup(dry_run: bool = False, force: bool = False) -> Dict[str, str]:
    """Start a Google Drive backup in background."""
    task_key = "backup"
    cmd = [PYTHON, str(MAIN_PY), "--backup"]
    if dry_run:
        cmd.append("--dry-run")
    if force:
        cmd.append("--force")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
        )
        _running_tasks[task_key] = process
        asyncio.create_task(_monitor_task(task_key, process))
        return {"success": True, "message": "Backup started", "task_id": task_key}
    except Exception as e:
        return {"success": False, "message": str(e), "task_id": None}


async def _monitor_task(task_key: str, process: asyncio.subprocess.Process) -> None:
    """Wait for a subprocess to finish and log the result."""
    try:
        stdout, stderr = await process.communicate()
        rc = process.returncode
        if rc == 0:
            logger.info("Task '%s' completed successfully.", task_key)
        else:
            err = stderr.decode("utf-8", errors="replace") if stderr else ""
            logger.error("Task '%s' failed (rc=%s): %s", task_key, rc, err[:500])
    except Exception as e:
        logger.error("Error monitoring task '%s': %s", task_key, e)
    finally:
        _running_tasks.pop(task_key, None)


def get_running_tasks() -> Dict[str, str]:
    """Return status of all tracked background tasks."""
    result: Dict[str, str] = {}
    for key, proc in list(_running_tasks.items()):
        if proc.returncode is None:
            result[key] = "running"
        else:
            result[key] = f"finished (rc={proc.returncode})"
    return result
