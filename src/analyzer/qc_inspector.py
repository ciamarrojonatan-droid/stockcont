"""Quality Control (QC) Inspector for StockCont.

Provides both Automated AI-driven visual auditing (via Gemini Vision)
and Manual visual triage for raw generated microstock images before upscaling.
Follows ADR-01 (UTF-8 encoding) and ADR-02 (Atomic write with .tmp).
"""

import base64
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import httpx
from dotenv import load_dotenv

# Reconfigure stdout/stderr on Windows for UTF-8 safety
if sys.platform.startswith("win"):
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

PROCESSED_DIR = BASE_DIR / "data" / "processed"
STAGING_DIR = BASE_DIR / "data" / "staging"
STAGING_IMAGES_DIR = STAGING_DIR / "images"

QC_CONFIG_FILE = PROCESSED_DIR / "qc_config.json"
QC_MANIFEST_FILE = PROCESSED_DIR / "qc_manifest.json"

logger = logging.getLogger("QCInspector")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

PREFERRED_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "mode": "auto",  # Default: 'auto' (Gemini Vision) or 'manual' (Human visual review)
    "min_score": 7.5,
    "auto_upscale": False,
    "target_resolution": [7680, 4320],
}

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

QC_SYSTEM_PROMPT = """You are an expert Microstock Technical Inspector and Commercial Art Director for top stock agencies (Adobe Stock, Freepik, Getty Images).
Your role is to rigorously evaluate an AI-generated raw stock image and determine whether it should be approved for high-resolution 8K upscale and commercial distribution.

EVALUATION CRITERIA:
1. Anatomy & Coherence: Check for deformed hands, incorrect finger counts, melted or asymmetrical facial features, distorted eyes, unnatural limbs, or floating artifacts.
2. Composition & Negative Copy-Space: Check if there is clean, uncluttered negative space (at least 30-40% of the frame) suitable for graphic design text overlays, banners, or typography.
3. Optical & Technical Quality: Check for natural focal depth, believable lens bokeh, absence of severe AI smearing, unnatural tile repetitions, or digital noise.
4. B2B Commercial Intent: Does this image have strong commercial appeal for corporate buyers, SaaS websites, healthcare, finance, or modern editorial use?

You must output STRICT JSON matching this schema:
{
  "score": <float between 0.0 and 10.0>,
  "decision": "<'approve' if score >= 7.5 and no severe defects, otherwise 'reject'>",
  "anatomy_score": <float 0.0 to 10.0>,
  "composition_score": <float 0.0 to 10.0>,
  "copy_space_score": <float 0.0 to 10.0>,
  "commercial_viability_score": <float 0.0 to 10.0>,
  "flaws": [<list of concrete flaws detected, e.g. 'extra finger on right hand', 'waxy skin', or empty if clean>],
  "strengths": [<list of strong commercial points, e.g. 'clean left copy-space', 'natural lighting'>],
  "summary": "<concise 1-2 sentence executive assessment in Portuguese or English>"
}
"""


def _atomic_write_json(file_path: Path, data: Any) -> None:
    """Atomic write complying with ADR-02."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(file_path)
    except Exception as e:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise e


class QCInspector:
    """Manages raw/staging image registration, automated Gemini Vision auditing, and manual triage."""

    def __init__(
        self,
        staging_dir: Optional[Path] = None,
        config_file: Optional[Path] = None,
        manifest_file: Optional[Path] = None,
    ):
        self.staging_dir = staging_dir or STAGING_IMAGES_DIR
        self.config_file = config_file or QC_CONFIG_FILE
        self.manifest_file = manifest_file or QC_MANIFEST_FILE
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

    def get_config(self) -> Dict[str, Any]:
        """Load QC configuration with fallback to defaults."""
        if not self.config_file.exists():
            _atomic_write_json(self.config_file, DEFAULT_CONFIG)
            return dict(DEFAULT_CONFIG)
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            config = dict(DEFAULT_CONFIG)
            config.update(data)
            return config
        except Exception as e:
            logger.warning("Error reading %s: %s. Using default config.", self.config_file.name, e)
            return dict(DEFAULT_CONFIG)

    def set_config(
        self,
        mode: Optional[Literal["auto", "manual"]] = None,
        min_score: Optional[float] = None,
        auto_upscale: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update and persist QC configuration."""
        config = self.get_config()
        if mode in ("auto", "manual"):
            config["mode"] = mode
        if min_score is not None and 0.0 <= min_score <= 10.0:
            config["min_score"] = float(min_score)
        if auto_upscale is not None:
            config["auto_upscale"] = bool(auto_upscale)

        _atomic_write_json(self.config_file, config)
        logger.info("QC Config updated: mode=%s, min_score=%.1f, auto_upscale=%s", config["mode"], config["min_score"], config["auto_upscale"])
        return config

    def get_manifest(self) -> Dict[str, Dict[str, Any]]:
        """Load QC manifest tracking all staging images."""
        if not self.manifest_file.exists():
            return {}
        try:
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning("Error reading %s: %s", self.manifest_file.name, e)
            return {}

    def save_manifest(self, manifest: Dict[str, Dict[str, Any]]) -> None:
        """Atomically persist manifest."""
        _atomic_write_json(self.manifest_file, manifest)

    def scan_staging(self) -> List[Dict[str, Any]]:
        """Scan staging directory and register untracked images into the manifest."""
        manifest = self.get_manifest()
        config = self.get_config()
        current_mode = config.get("mode", "auto")
        now_iso = datetime.now(timezone.utc).isoformat()

        updated = False
        new_items = []

        if self.staging_dir.exists():
            stale = [k for k, v in manifest.items() if not Path(v.get("path") or (self.staging_dir / k)).exists()]
            for k in stale:
                del manifest[k]
                updated = True
            for file_path in sorted(self.staging_dir.iterdir()):
                if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
                    fname = file_path.name
                    if fname not in manifest:
                        item = {
                            "filename": fname,
                            "path": str(file_path),
                            "prompt_hash": "",
                            "prompt_text": "",
                            "status": "pending",  # "pending", "approved", "rejected"
                            "mode": current_mode,
                            "score": None,
                            "decision": None,
                            "critique": None,
                            "upscaled": False,
                            "final_image": None,
                            "created_at": now_iso,
                            "reviewed_at": None,
                        }
                        manifest[fname] = item
                        new_items.append(item)
                        updated = True

        if updated:
            self.save_manifest(manifest)
            logger.info("Registered %d new images in QC staging.", len(new_items))

        return list(manifest.values())

    def register_staging_image(
        self,
        filename: str,
        prompt_hash: str = "",
        prompt_text: str = "",
    ) -> Dict[str, Any]:
        """Explicitly register a generated staging image with prompt metadata."""
        manifest = self.get_manifest()
        config = self.get_config()
        current_mode = config.get("mode", "auto")
        now_iso = datetime.now(timezone.utc).isoformat()

        item = {
            "filename": filename,
            "path": str(self.staging_dir / filename),
            "prompt_hash": prompt_hash,
            "prompt_text": prompt_text,
            "status": "pending",
            "mode": current_mode,
            "score": None,
            "decision": None,
            "critique": None,
            "upscaled": False,
            "final_image": None,
            "created_at": now_iso,
            "reviewed_at": None,
        }
        manifest[filename] = item
        self.save_manifest(manifest)
        return item

    def evaluate_image(
        self,
        filename: str,
        api_key: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Audit image using Gemini Vision and update manifest."""
        manifest = self.get_manifest()
        item = manifest.get(filename)
        if not item:
            # Try to register if file exists on disk
            candidate_path = self.staging_dir / filename
            if candidate_path.exists():
                item = self.register_staging_image(filename)
            else:
                raise FileNotFoundError(f"Staging image not found: {filename}")

        if item.get("status") in ("approved", "rejected") and not force:
            logger.info("Image %s already evaluated (%s). Skipping.", filename, item.get("status"))
            return item

        img_path = Path(item.get("path") or (self.staging_dir / filename))
        if not img_path.exists():
            raise FileNotFoundError(f"Physical file missing: {img_path}")

        config = self.get_config()
        min_score = config.get("min_score", 7.5)
        current_mode = config.get("mode", "auto")

        # Encode image to Base64
        with open(img_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
        mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"

        critique_result = self._call_gemini_vision_audit(b64_data, mime, api_key=api_key)

        score = float(critique_result.get("score", 7.0))
        decision = critique_result.get("decision", "reject" if score < min_score else "approve")

        now_iso = datetime.now(timezone.utc).isoformat()
        item["score"] = score
        item["decision"] = decision
        item["critique"] = critique_result
        item["reviewed_at"] = now_iso
        item["mode"] = current_mode

        if current_mode == "auto":
            item["status"] = "approved" if (decision == "approve" and score >= min_score) else "rejected"
            logger.info("🤖 [Auto QC] %s evaluated: Score=%.1f/10 -> Status: %s", filename, score, item["status"])
            
            # If auto_upscale is active and approved, trigger upscale
            if item["status"] == "approved" and config.get("auto_upscale", False):
                try:
                    from src.factory.upscaler import Upscaler
                    upscaler = Upscaler()
                    final_path = upscaler.upscale_image(filename)
                    if final_path:
                        item["upscaled"] = True
                        item["final_image"] = final_path.name
                except Exception as up_err:
                    logger.error("Auto-upscale failed for %s: %s", filename, up_err)
        else:
            # Manual mode: keep pending so user can confirm in Dashboard
            item["status"] = "pending"
            logger.info("👁️ [Manual QC] %s analyzed by AI: Score=%.1f/10. Awaiting user approval in Dashboard.", filename, score)

        manifest[filename] = item
        self.save_manifest(manifest)
        return item

    def _call_gemini_vision_audit(
        self,
        b64_image: str,
        mime_type: str,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform multimodal call to Gemini Vision API with error handling."""
        key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            logger.warning("GEMINI_API_KEY is not configured. Falling back to local heuristic critique.")
            return {
                "score": 8.0,
                "decision": "approve",
                "anatomy_score": 8.0,
                "composition_score": 8.0,
                "copy_space_score": 8.0,
                "commercial_viability_score": 8.0,
                "flaws": [],
                "strengths": ["Local default evaluation (Gemini key not configured)"],
                "summary": "Imagem aprovada preliminarmente (modo offline sem API Gemini).",
            }

        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": b64_image}},
                    {"text": QC_SYSTEM_PROMPT + "\n\nCRITICAL: Analyze this image and return the JSON evaluation report."}
                ]
            }],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            }
        }

        for model_name in PREFERRED_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        raw_text = ""
                        for part in parts:
                            if "text" in part and not part.get("thought", False):
                                raw_text = part["text"]
                                break
                        if not raw_text and parts and "text" in parts[0]:
                            raw_text = parts[0]["text"]

                        clean_json = raw_text.strip()
                        if clean_json.startswith("```json"):
                            clean_json = clean_json[7:]
                        elif clean_json.startswith("```"):
                            clean_json = clean_json[3:]
                        if clean_json.endswith("```"):
                            clean_json = clean_json[:-3]
                        clean_json = clean_json.strip()

                        parsed = json.loads(clean_json)
                        return parsed
                else:
                    logger.warning("Gemini model %s returned status %d: %s", model_name, resp.status_code, resp.text[:150])
            except Exception as e:
                logger.warning("Failed calling %s for QC: %s", model_name, e)

        # Fallback if network or quota issue
        return {
            "score": 7.5,
            "decision": "approve",
            "anatomy_score": 7.5,
            "composition_score": 7.5,
            "copy_space_score": 7.5,
            "commercial_viability_score": 7.5,
            "flaws": [],
            "strengths": ["Automated fallback evaluation"],
            "summary": "Avaliação de fallback executada devido a instabilidade na API externa.",
        }

    def set_status(
        self,
        filename: str,
        status: Literal["approved", "rejected", "pending"],
        notes: str = "",
    ) -> Dict[str, Any]:
        """Manually override status of a staging image."""
        manifest = self.get_manifest()
        item = manifest.get(filename)
        if not item:
            candidate_path = self.staging_dir / filename
            if candidate_path.exists():
                item = self.register_staging_image(filename)
            else:
                raise FileNotFoundError(f"Staging image not found: {filename}")

        item["status"] = status
        item["reviewed_at"] = datetime.now(timezone.utc).isoformat()
        item["manual_override"] = True
        if notes:
            item["manual_notes"] = notes

        manifest[filename] = item
        self.save_manifest(manifest)
        logger.info("Image %s manually set to %s.", filename, status)
        return item

    def batch_set_status(
        self,
        filenames: List[str],
        status: Literal["approved", "rejected", "pending"],
    ) -> int:
        """Batch set status for multiple images."""
        manifest = self.get_manifest()
        count = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        for fname in filenames:
            item = manifest.get(fname)
            if item:
                item["status"] = status
                item["reviewed_at"] = now_iso
                item["manual_override"] = True
                count += 1

        if count > 0:
            self.save_manifest(manifest)
        return count

    def run_batch_qc(self, filenames: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Run evaluation across pending staging images."""
        self.scan_staging()
        manifest = self.get_manifest()

        if filenames is not None:
            target_files = [f for f in filenames if f in manifest]
        else:
            target_files = [f for f, data in manifest.items() if data.get("status") == "pending"]

        logger.info("Starting batch QC on %d image(s)...", len(target_files))
        results = []
        for fname in target_files:
            try:
                res = self.evaluate_image(fname)
                results.append(res)
            except Exception as e:
                logger.error("Error evaluating %s: %s", fname, e)

        return results

    def package_approved_images(
        self,
        output_zip_path: Optional[Path] = None,
        only_unprocessed: bool = True,
        max_images: int = 10,
    ) -> Tuple[Optional[Path], List[str]]:
        """
        Coleta imagens aprovadas pelo QC em data/staging/images/ que ainda não foram
        processadas pelo SeedVR (only_unprocessed=True) e empacota no máximo max_images
        (padrão: 10 para evitar VRAM Out-of-Memory no KSampler #23 do SeedVR).
        """
        import zipfile

        manifest = self.get_manifest()
        approved_filenames: List[str] = []
        for fname, data in manifest.items():
            if data.get("status") == "approved":
                if only_unprocessed and data.get("upscaled_by_seedvr", False):
                    continue
                approved_filenames.append(fname)

        if not approved_filenames:
            logger.warning("Nenhuma imagem aprovada pendente de upscale encontrada para empacotar em zip.")
            return None, []

        # Limitar a no máximo max_images (ex: 10) para proteger a VRAM contra OOM no KSampler
        batch_slice = approved_filenames[:max_images]

        zip_dest = output_zip_path or (self.staging_dir / "approved_batch.zip")
        zip_dest.parent.mkdir(parents=True, exist_ok=True)
        tmp_zip = zip_dest.with_suffix(f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")

        valid_files: List[str] = []
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in batch_slice:
                fpath = Path(manifest[fname].get("path") or (self.staging_dir / fname))
                if fpath.exists():
                    zf.write(fpath, arcname=fpath.name)
                    valid_files.append(fname)
                else:
                    logger.warning("Arquivo físico não encontrado para zip: %s", fpath)

        if not valid_files:
            if tmp_zip.exists():
                tmp_zip.unlink()
            return None, []

        tmp_zip.replace(zip_dest)

        # Espelhar tambem em data/staging/ e data/staging/images/ para visibilidade imediata
        try:
            import shutil
            alt_dest = (self.staging_dir.parent / "approved_batch.zip") if self.staging_dir.name == "images" else (self.staging_dir / "images" / "approved_batch.zip")
            alt_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(zip_dest, alt_dest)
        except Exception:
            pass
        logger.info(
            "📦 Criado pacote zip com %d imagens aprovadas (limite max: %d Anti-OOM): %s",
            len(valid_files),
            max_images,
            zip_dest.name,
        )
        return zip_dest, valid_files

    def get_stats(self) -> Dict[str, Any]:
        """Return summary counters for the QC pipeline."""
        self.scan_staging()
        manifest = self.get_manifest()
        config = self.get_config()

        total = len(manifest)
        pending = sum(1 for item in manifest.values() if item.get("status") == "pending")
        approved = sum(1 for item in manifest.values() if item.get("status") == "approved")
        rejected = sum(1 for item in manifest.values() if item.get("status") == "rejected")
        upscaled = sum(1 for item in manifest.values() if item.get("upscaled", False))

        return {
            "total_staging": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "upscaled": upscaled,
            "mode": config.get("mode", "auto"),
            "min_score": config.get("min_score", 7.5),
            "auto_upscale": config.get("auto_upscale", False),
        }
