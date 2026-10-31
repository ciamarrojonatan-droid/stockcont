"""Background task runner for pipeline phase execution.

Delegates work to main.py via subprocess so the dashboard
server never blocks and never modifies data files directly.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sys
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MAIN_PY = BASE_DIR / "main.py"
PYTHON = sys.executable

_running_tasks: Dict[str, asyncio.subprocess.Process] = {}
_task_records: Dict[str, Dict[str, Any]] = {}


async def _stream_pipe(
    stream: asyncio.StreamReader,
    task_key: str,
    is_stderr: bool = False,
) -> None:
    """Read a stream line by line, log it, and append to the task's recent logs."""
    while True:
        try:
            line_bytes = await stream.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace").rstrip("\r\n")
            if "\r" in line:
                line = line.split("\r")[-1]
            line = line.strip()
            if not line:
                continue
            if is_stderr:
                logger.warning("[%s] %s", task_key, line)
            else:
                logger.info("[%s] %s", task_key, line)

            record = _task_records.get(task_key)
            if record:
                record["logs"].append(line)
                record["last_log"] = line
        except Exception as e:
            logger.error("Error reading stream pipe for '%s': %s", task_key, e)
            break


async def _monitor_task(task_key: str, process: asyncio.subprocess.Process) -> None:
    """Stream stdout and stderr line-by-line and update task record."""
    try:
        tasks = []
        if process.stdout is not None:
            tasks.append(asyncio.create_task(_stream_pipe(process.stdout, task_key, is_stderr=False)))
        if process.stderr is not None:
            tasks.append(asyncio.create_task(_stream_pipe(process.stderr, task_key, is_stderr=True)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        rc = await process.wait()

        record = _task_records.get(task_key)
        if record:
            record["returncode"] = rc
            record["completed_at"] = datetime.now(timezone.utc).isoformat()
            if rc == 0:
                record["status"] = "completed"
                logger.info("Task '%s' completed successfully.", task_key)
            else:
                record["status"] = "failed"
                logger.error("Task '%s' failed (rc=%s).", task_key, rc)
                if not record.get("last_log") or record["last_log"].startswith("Starting"):
                    record["last_log"] = f"Task failed with exit code {rc}"
    except Exception as e:
        logger.error("Error monitoring task '%s': %s", task_key, e)
        record = _task_records.get(task_key)
        if record:
            record["status"] = "failed"
            record["completed_at"] = datetime.now(timezone.utc).isoformat()
            record["logs"].append(f"Monitor error: {e}")
            record["last_log"] = f"Monitor error: {e}"
    finally:
        _running_tasks.pop(task_key, None)


async def run_phase(phase: int, extra_args: Optional[List[str]] = None) -> Dict[str, Any]:
    """Start a pipeline phase in a background subprocess."""
    task_key = f"phase-{phase}"

    if task_key in _running_tasks and _running_tasks[task_key].returncode is None:
        return {"success": False, "message": f"Phase {phase} is already running", "task_id": task_key}

    cmd = [PYTHON, "-u", str(MAIN_PY), "--phase", str(phase)]
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Starting Phase %d: %s", phase, " ".join(cmd))

    _task_records[task_key] = {
        "task_id": task_key,
        "phase": phase,
        "status": "running",
        "returncode": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "logs": deque(maxlen=100),
        "last_log": f"Starting Phase {phase}...",
    }

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
            env=env,
        )
        _running_tasks[task_key] = process
        asyncio.create_task(_monitor_task(task_key, process))
        return {"success": True, "message": f"Phase {phase} started", "task_id": task_key}
    except Exception as e:
        logger.error("Failed to start Phase %d: %s", phase, e)
        if task_key in _task_records:
            _task_records[task_key]["status"] = "failed"
            _task_records[task_key]["completed_at"] = datetime.now(timezone.utc).isoformat()
            _task_records[task_key]["last_log"] = f"Failed to start: {e}"
        return {"success": False, "message": str(e), "task_id": None}


async def run_conta2(mode: str = "window", batch_size: int = 10) -> Dict[str, Any]:
    """Launch Conta 2 (SeedVR 8K Upscaler).

    If mode == 'window' on Windows: opens run_conta2.bat in a separate console window.
    If mode == 'background': runs Phase 3 with --account 2 --batch-size {batch_size}.
    """
    bat_file = BASE_DIR / "run_conta2.bat"
    if mode == "window" and sys.platform.startswith("win") and bat_file.exists():
        import subprocess

        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "StockCont Conta 2 - SeedVR 8K", str(bat_file)],
                cwd=str(BASE_DIR),
                shell=False,
            )
            return {
                "success": True,
                "message": "run_conta2.bat disparado em uma nova janela de terminal!",
                "mode": "window",
                "task_id": None,
            }
        except Exception as e:
            logger.warning("Falha ao abrir janela para run_conta2.bat: %s, usando background", e)

    extra_args = ["--account", "2", "--batch-size", str(batch_size)]
    return await run_phase(3, extra_args=extra_args)


async def run_backup(dry_run: bool = False, force: bool = False) -> Dict[str, Any]:
    """Start a Google Drive backup in background."""
    task_key = "backup"

    if task_key in _running_tasks and _running_tasks[task_key].returncode is None:
        return {"success": False, "message": "Backup is already running", "task_id": task_key}

    cmd = [PYTHON, "-u", str(MAIN_PY), "--backup"]
    if dry_run:
        cmd.append("--dry-run")
    if force:
        cmd.append("--force")

    logger.info("Starting backup: %s", " ".join(cmd))

    _task_records[task_key] = {
        "task_id": task_key,
        "phase": None,
        "status": "running",
        "returncode": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "logs": deque(maxlen=100),
        "last_log": "Starting backup...",
    }

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
            env=env,
        )
        _running_tasks[task_key] = process
        asyncio.create_task(_monitor_task(task_key, process))
        return {"success": True, "message": "Backup started", "task_id": task_key}
    except Exception as e:
        logger.error("Failed to start backup: %s", e)
        if task_key in _task_records:
            _task_records[task_key]["status"] = "failed"
            _task_records[task_key]["completed_at"] = datetime.now(timezone.utc).isoformat()
            _task_records[task_key]["last_log"] = f"Failed to start: {e}"
        return {"success": False, "message": str(e), "task_id": None}


def get_running_tasks() -> Dict[str, Any]:
    """Return status of all tracked background tasks."""
    result: Dict[str, Any] = {}
    for key, record in list(_task_records.items()):
        result[key] = {
            "task_id": record["task_id"],
            "phase": record.get("phase"),
            "status": record["status"],
            "returncode": record["returncode"],
            "started_at": record["started_at"],
            "completed_at": record["completed_at"],
            "last_log": record.get("last_log", ""),
            "logs": list(record["logs"]),
        }
    return result


def get_task(task_key: str) -> Optional[Dict[str, Any]]:
    """Return details of a specific task."""
    record = _task_records.get(task_key)
    if not record:
        return None
    return {
        "task_id": record["task_id"],
        "phase": record.get("phase"),
        "status": record["status"],
        "returncode": record["returncode"],
        "started_at": record["started_at"],
        "completed_at": record["completed_at"],
        "last_log": record.get("last_log", ""),
        "logs": list(record["logs"]),
    }


def terminate_task(task_key: str) -> bool:
    """Terminate a running background task and child processes."""
    proc = _running_tasks.get(task_key)
    if proc and proc.returncode is None:
        try:
            if sys.platform.startswith("win"):
                import subprocess
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
            else:
                proc.terminate()
            logger.info("Terminated task '%s' (PID %s)", task_key, proc.pid)
            record = _task_records.get(task_key)
            if record:
                record["status"] = "failed"
                record["completed_at"] = datetime.now(timezone.utc).isoformat()
                record["last_log"] = "Process terminated by user"
                record["logs"].append("Process terminated by user")
            return True
        except Exception as e:
            logger.error("Failed to terminate task '%s': %s", task_key, e)
            try:
                proc.kill()
            except Exception:
                pass
    return False


def cleanup_orphan_processes() -> int:
    """Find and terminate orphan python processes running main.py."""
    count = 0
    my_pid = os.getpid()
    tracked_pids = {p.pid for p in _running_tasks.values() if p and getattr(p, "pid", None)}

    if sys.platform.startswith("win"):
        try:
            import subprocess
            # Filter specifically by Python process names so PowerShell itself doesn't match
            ps_cmd = (
                "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
                "Where-Object { ($_.CommandLine -like '*main.py*--phase*' -or $_.CommandLine -like '*main.py*--backup*') -and ($_.CommandLine -notlike '*--dashboard*') } | "
                "Select-Object -ExpandProperty ProcessId"
            )
            cmd = ["powershell", "-NoProfile", "-Command", ps_cmd]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            pids = [int(p.strip()) for p in res.stdout.strip().splitlines() if p.strip().isdigit()]
            for pid in pids:
                if pid == my_pid or pid in tracked_pids:
                    continue
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=5)
                    logger.warning("Terminated orphan main.py process PID %d", pid)
                    count += 1
                except Exception as e:
                    logger.error("Failed to kill orphan PID %d: %s", pid, e)
        except Exception as e:
            logger.warning("Error checking for orphan processes: %s", e)
    else:
        try:
            import subprocess
            cmd = ["pgrep", "-f", "python.*main\\.py"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            pids = [int(p.strip()) for p in res.stdout.strip().splitlines() if p.strip().isdigit()]
            for pid in pids:
                if pid == my_pid or pid in tracked_pids:
                    continue
                try:
                    os.kill(pid, 9)
                    logger.warning("Terminated orphan main.py process PID %d", pid)
                    count += 1
                except Exception as e:
                    logger.error("Failed to kill orphan PID %d: %s", pid, e)
        except Exception as e:
            logger.warning("Error checking for orphan processes (unix): %s", e)

    return count



async def run_daemon_task(mode: str = "background", interval: int = 300, min_buffer: int = 50) -> Dict[str, Any]:
    """Launch 24/7 Production Daemon."""
    task_key = "daemon"
    if task_key in _running_tasks and _running_tasks[task_key].returncode is None:
        return {"success": False, "message": "Daemon 24/7 já está em execução", "task_id": task_key}

    bat_file = BASE_DIR / "run_24_7.bat"
    if mode == "window" and sys.platform.startswith("win") and bat_file.exists():
        import subprocess
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "StockCont Daemon 24/7", str(bat_file)],
                cwd=str(BASE_DIR),
                shell=False,
            )
            return {
                "success": True,
                "message": "Daemon 24/7 iniciado em janela de terminal dedicada (run_24_7.bat).",
                "task_id": "daemon_window",
            }
        except Exception as e:
            return {"success": False, "message": f"Falha ao iniciar run_24_7.bat: {e}", "task_id": None}

    cmd = [PYTHON, "-u", str(MAIN_PY), "--daemon", "--daemon-interval", str(interval), "--min-buffer", str(min_buffer)]
    logger.info("Iniciando Daemon 24/7 em background: %s", " ".join(cmd))

    _task_records[task_key] = {
        "task_id": task_key,
        "phase": "daemon",
        "status": "running",
        "returncode": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "logs": deque(maxlen=100),
        "last_log": "Iniciando Daemon 24/7...",
    }

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
            env=env,
        )
        _running_tasks[task_key] = process
        asyncio.create_task(_monitor_task(task_key, process))
        return {"success": True, "message": "Daemon 24/7 iniciado em background com sucesso", "task_id": task_key}
    except Exception as e:
        logger.error("Falha ao iniciar Daemon 24/7: %s", e)
        if task_key in _task_records:
            _task_records[task_key]["status"] = "failed"
            _task_records[task_key]["completed_at"] = datetime.now(timezone.utc).isoformat()
            _task_records[task_key]["last_log"] = f"Failed to start: {e}"
        return {"success": False, "message": str(e), "task_id": None}


async def run_video_phase(phase: int, extra_args: Optional[List[str]] = None) -> Dict[str, Any]:
    """Start a video pipeline phase in a background subprocess."""
    task_key = f"video-phase-{phase}"

    if task_key in _running_tasks and _running_tasks[task_key].returncode is None:
        return {"success": False, "message": f"Video Phase {phase} is already running", "task_id": task_key}

    cmd = [PYTHON, "-u", str(MAIN_PY), "--phase", str(phase), "--video"]
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Starting Video Phase %d: %s", phase, " ".join(cmd))

    _task_records[task_key] = {
        "task_id": task_key,
        "phase": f"video-{phase}",
        "status": "running",
        "returncode": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "logs": deque(maxlen=100),
        "last_log": f"Starting Video Phase {phase}...",
    }

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
            env=env,
        )
        _running_tasks[task_key] = process
        asyncio.create_task(_monitor_task(task_key, process))
        return {"success": True, "message": f"Video Phase {phase} started", "task_id": task_key}
    except Exception as e:
        logger.error("Failed to start Video Phase %d: %s", phase, e)
        if task_key in _task_records:
            _task_records[task_key]["status"] = "failed"
            _task_records[task_key]["completed_at"] = datetime.now(timezone.utc).isoformat()
            _task_records[task_key]["last_log"] = f"Failed to start: {e}"
        return {"success": False, "message": str(e), "task_id": None}


async def run_video_i2v_synthesis(image_stem: str) -> Dict[str, Any]:
    """Synthesize 4D video prompts for a specific 8K image via Gemini Vision."""
    clean_stem = Path(image_stem).stem
    task_key = f"i2v-{clean_stem[:12]}"
    if task_key in _running_tasks and _running_tasks[task_key].returncode is None:
        return {"success": False, "message": f"I2V synthesis already running for {clean_stem}", "task_id": task_key}

    script = (
        "import os, sys, json, time; from pathlib import Path; "
        "from dotenv import load_dotenv; from src.analyzer.video_director import generate_video_prompts_from_reference, BASE_DIR, PROCESSED_VIDEO_PROMPTS_FILE, FINAL_IMAGES_DIR; "
        "load_dotenv(BASE_DIR / '.env', override=True); "
        "api_key = os.getenv('GEMINI_API_KEY'); "
        f"stem = '{clean_stem}'; "
        "cand = FINAL_IMAGES_DIR / f'{stem}.jpg'; "
        "if not cand.exists(): cand = FINAL_IMAGES_DIR / f'{stem}.png'; "
        "if not cand.exists(): print(f'Image not found: {stem}'); sys.exit(1); "
        "print(f'Synthesizing 4D video prompts from {cand.name}...'); "
        "res = generate_video_prompts_from_reference(cand, stem.replace('_', ' ').title(), stem, api_key); "
        "if not res: print('Failed to generate prompts via Gemini'); sys.exit(2); "
        "existing = []; "
        "if PROCESSED_VIDEO_PROMPTS_FILE.exists(): "
        "    try: existing = json.loads(PROCESSED_VIDEO_PROMPTS_FILE.read_text(encoding='utf-8')) "
        "    except: existing = []; "
        "existing = [x for x in existing if str(x.get('source_id')) != stem]; "
        "existing.append(res); "
        "tmp = PROCESSED_VIDEO_PROMPTS_FILE.with_suffix(f'.tmp.{os.getpid()}'); "
        "tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding='utf-8'); "
        "tmp.replace(PROCESSED_VIDEO_PROMPTS_FILE); "
        "print(f'Successfully generated 4 commercial video prompts for {stem}!');"
    )

    cmd = [PYTHON, "-u", "-c", script]

    _task_records[task_key] = {
        "task_id": task_key,
        "phase": "i2v-synthesis",
        "status": "running",
        "returncode": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "logs": deque(maxlen=100),
        "last_log": f"Synthesizing 4D video prompts for {clean_stem}...",
    }

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR),
            env=env,
        )
        _running_tasks[task_key] = process
        asyncio.create_task(_monitor_task(task_key, process))
        return {"success": True, "message": f"I2V synthesis started for {clean_stem}", "task_id": task_key}
    except Exception as e:
        logger.error("Failed to start I2V synthesis: %s", e)
        if task_key in _task_records:
            _task_records[task_key]["status"] = "failed"
            _task_records[task_key]["completed_at"] = datetime.now(timezone.utc).isoformat()
            _task_records[task_key]["last_log"] = f"Failed to start: {e}"
        return {"success": False, "message": str(e), "task_id": None}
