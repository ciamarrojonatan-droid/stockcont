"""Prompt Queue and Generation Ledger Manager for Phase 3.

Manages prompt state persistence, SHA-256 hashing, batch queueing,
and atomic updates to prompts.json and generation_history.json.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
RAW_DIR: Path = BASE_DIR / "data" / "raw"
FINAL_IMAGES_DIR: Path = BASE_DIR / "data" / "final" / "images"
FINAL_VIDEOS_DIR: Path = BASE_DIR / "data" / "final" / "videos"
STAGING_VIDEOS_DIR: Path = BASE_DIR / "data" / "staging" / "videos"

DEFAULT_PROMPTS_FILE: Path = PROCESSED_DIR / "prompts.json"
DEFAULT_HISTORY_FILE: Path = PROCESSED_DIR / "generation_history.json"
DEFAULT_TRENDS_FILE: Path = RAW_DIR / "trends.json"


@dataclass
class PromptItem:
    """Represents a single prompt in the generation queue."""
    prompt_text: str
    prompt_hash: str
    source_id: str = ""
    prompt_id: Any = None
    concept: str = ""
    status: str = "pending"
    generated_at: Optional[str] = None
    image_file: Optional[str] = None
    asset_type: str = "image"
    video_file: Optional[str] = None
    aspect_ratio: str = "16:9"

    def __str__(self) -> str:
        return self.prompt_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_text": self.prompt_text,
            "prompt_hash": self.prompt_hash,
            "source_id": str(self.source_id),
            "prompt_id": self.prompt_id,
            "concept": self.concept,
            "status": self.status,
            "generated_at": self.generated_at,
            "image_file": self.image_file,
            "asset_type": self.asset_type,
            "video_file": self.video_file,
            "aspect_ratio": self.aspect_ratio,
        }


class PromptQueueManager:
    """Orchestrates prompt queueing, deduplication, and generation history ledger."""

    def __init__(
        self,
        prompts_file: Path = DEFAULT_PROMPTS_FILE,
        history_file: Path = DEFAULT_HISTORY_FILE,
        trends_file: Path = DEFAULT_TRENDS_FILE,
        images_dir: Path = FINAL_IMAGES_DIR,
        auto_reconcile: bool = True,
    ) -> None:
        self.prompts_file = Path(prompts_file)
        self.history_file = Path(history_file)
        self.trends_file = Path(trends_file)
        self.images_dir = Path(images_dir)

        self._history: Dict[str, Dict[str, Any]] = self._load_history()

        if auto_reconcile:
            self.reconcile_existing_images()

    @staticmethod
    def compute_hash(prompt_text: str) -> str:
        """Calculate canonical SHA-256 hash of prompt text."""
        normalized = prompt_text.replace("\r\n", " ").replace("\n", " ").strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _load_history(self) -> Dict[str, Dict[str, Any]]:
        """Load history ledger from disk."""
        if not self.history_file.exists():
            return {}
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                elif isinstance(data, list):
                    # Fallback if stored as list of records
                    res: Dict[str, Dict[str, Any]] = {}
                    for item in data:
                        h = item.get("prompt_hash")
                        if h:
                            res[h] = item
                    return res
                return {}
        except Exception as e:
            logger.warning(f"Não foi possível ler {self.history_file.name}: {e}. Inicializando ledger vazio.")
            return {}

    def _save_history(self) -> None:
        """Atomically persist history ledger via temporary file."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self.history_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
            tmp_file.replace(self.history_file)
        except Exception as e:
            logger.error(f"Erro ao salvar histórico de geração ({self.history_file}): {e}")
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass

    def _load_prompts_data(self) -> List[Dict[str, Any]]:
        """Load raw prompts dataset from prompts.json."""
        if not self.prompts_file.exists():
            return []
        try:
            with open(self.prompts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Erro ao ler arquivo de prompts ({self.prompts_file}): {e}")
            return []

    def _save_prompts_data(self, data: List[Dict[str, Any]]) -> None:
        """Atomically persist prompts dataset via temporary file."""
        self.prompts_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self.prompts_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            tmp_file.replace(self.prompts_file)
        except Exception as e:
            logger.error(f"Erro ao salvar prompts.json ({self.prompts_file}): {e}")
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass

    def _get_ordered_raw_items(self) -> List[Dict[str, Any]]:
        """Return prompts dataset ordered with Contributor Insights items first."""
        data = self._load_prompts_data()
        if not data:
            return []

        insights_ids: Set[str] = set()
        if self.trends_file.exists():
            try:
                with open(self.trends_file, "r", encoding="utf-8") as tf:
                    trends = json.load(tf)
                    if isinstance(trends, list):
                        insights_ids = {
                            str(t.get("id"))
                            for t in trends
                            if isinstance(t, dict) and t.get("source") == "contributor_insights"
                        }
            except Exception as e:
                logger.debug(f"Aviso ao ler {self.trends_file.name}: {e}")

        insights_items: List[Dict[str, Any]] = []
        other_items: List[Dict[str, Any]] = []
        for item in data:
            sid = str(item.get("source_id", ""))
            if sid in insights_ids or item.get("source") == "contributor_insights":
                insights_items.append(item)
            else:
                other_items.append(item)

        return insights_items + other_items

    @classmethod
    def extract_prompt_text(cls, prompt_dict: Dict[str, Any]) -> str:
        """Extract clean prompt string from a generated_prompts element."""
        if "prompt_data" in prompt_dict and isinstance(prompt_dict["prompt_data"], dict):
            pdata = prompt_dict["prompt_data"]
            if "final_prompt" in pdata and isinstance(pdata["final_prompt"], str):
                return pdata["final_prompt"].replace("\r\n", " ").replace("\n", " ").strip()
        if "prompt" in prompt_dict and isinstance(prompt_dict["prompt"], str):
            return prompt_dict["prompt"].replace("\r\n", " ").replace("\n", " ").strip()
        if "prompt_data" in prompt_dict:
            return json.dumps(prompt_dict["prompt_data"], ensure_ascii=False)
        return ""

    def get_all_prompts(self) -> List[PromptItem]:
        """Parse all prompts preserving ordering and current generation status."""
        ordered_items = self._get_ordered_raw_items()
        all_items: List[PromptItem] = []

        for item in ordered_items:
            source_id = str(item.get("source_id", ""))
            for p in item.get("generated_prompts", []):
                text = self.extract_prompt_text(p)
                if not text:
                    continue
                p_hash = self.compute_hash(text)
                
                # Check generation status in ledger or item
                history_entry = self._history.get(p_hash)
                is_generated = (p.get("status") == "generated") or (history_entry is not None)
                
                status = "generated" if is_generated else "pending"
                generated_at = None
                image_file = None
                if history_entry:
                    generated_at = history_entry.get("generated_at")
                    image_file = history_entry.get("image_file")
                elif p.get("status") == "generated":
                    generated_at = p.get("generated_at")
                    image_file = p.get("image_file")

                all_items.append(
                    PromptItem(
                        prompt_text=text,
                        prompt_hash=p_hash,
                        source_id=source_id,
                        prompt_id=p.get("id"),
                        concept=p.get("concept", ""),
                        status=status,
                        generated_at=generated_at,
                        image_file=image_file,
                    )
                )

        return all_items

    def get_pending_prompts(self, batch_size: Optional[int] = 10) -> List[PromptItem]:
        """Return pending prompts that have not been generated yet.
        
        Args:
            batch_size: Max number of prompts to return. If None or <= 0, returns all.
        """
        all_items = self.get_all_prompts()
        pending = [p for p in all_items if p.status == "pending"]

        if batch_size is not None and batch_size > 0:
            return pending[:batch_size]
        return pending

    def mark_prompts_generated(
        self,
        prompts: List[Union[PromptItem, str, Dict[str, Any]]],
        saved_images: Optional[List[str]] = None,
    ) -> int:
        """Mark prompts as generated in both history ledger and prompts.json.
        
        If saved_images is provided and its count is less than prompts count,
        only the first len(saved_images) prompts are marked (partial success resilience).
        
        Args:
            prompts: List of PromptItem, strings, or dicts to mark.
            saved_images: List of saved image filenames corresponding to generated prompts.
            
        Returns:
            Number of prompts successfully marked as generated.
        """
        if not prompts:
            return 0

        # Partial failure handling: only mark up to saved_images count if provided
        limit = len(saved_images) if saved_images is not None else len(prompts)
        prompts_to_mark = prompts[:limit]
        if not prompts_to_mark:
            return 0

        now_iso = datetime.now(timezone.utc).isoformat()
        marked_hashes: Dict[str, Dict[str, Any]] = {}

        for idx, item in enumerate(prompts_to_mark):
            img_file = saved_images[idx] if (saved_images and idx < len(saved_images)) else None

            if isinstance(item, PromptItem):
                p_text = item.prompt_text
                p_hash = item.prompt_hash
                source_id = item.source_id
                prompt_id = item.prompt_id
                concept = item.concept
            elif isinstance(item, str):
                p_text = item
                p_hash = self.compute_hash(p_text)
                source_id = ""
                prompt_id = None
                concept = ""
            elif isinstance(item, dict):
                p_text = item.get("prompt_text") or self.extract_prompt_text(item)
                p_hash = item.get("prompt_hash") or self.compute_hash(p_text)
                source_id = str(item.get("source_id", ""))
                prompt_id = item.get("prompt_id") or item.get("id")
                concept = item.get("concept", "")
            else:
                continue

            entry = {
                "prompt_hash": p_hash,
                "prompt_text": p_text,
                "source_id": source_id,
                "prompt_id": prompt_id,
                "concept": concept,
                "generated_at": now_iso,
                "image_file": img_file,
            }
            self._history[p_hash] = entry
            marked_hashes[p_hash] = entry

        # 1. Save history ledger atomically
        self._save_history()

        # 2. Update prompts.json atomically
        raw_data = self._load_prompts_data()
        updated_any = False

        for group in raw_data:
            for p in group.get("generated_prompts", []):
                p_text = self.extract_prompt_text(p)
                p_hash = self.compute_hash(p_text)
                if p_hash in marked_hashes:
                    entry = marked_hashes[p_hash]
                    p["status"] = "generated"
                    p["generated_at"] = entry["generated_at"]
                    if entry["image_file"]:
                        p["image_file"] = entry["image_file"]
                    updated_any = True

        if updated_any:
            self._save_prompts_data(raw_data)

        logger.info(f"✅ {len(marked_hashes)} prompts registrados como gerados no ledger e em prompts.json.")
        return len(marked_hashes)

    def mark_by_hashes(self, hashes: list) -> int:
        """Mark prompts matching specific hashes (full or prefix) as generated."""
        if not hashes:
            return 0
        hash_set = {str(h).strip().lower() for h in hashes if h and str(h).strip()}
        all_items = self.get_all_prompts()
        matching = [
            p for p in all_items
            if (p.prompt_hash.lower() in hash_set or p.prompt_hash[:12].lower() in hash_set)
        ]
        return self.mark_prompts_generated(matching)

    def mark_all_pending_generated(self) -> int:
        """Mark all currently pending prompts in the queue as generated."""
        pending = self.get_pending_prompts(batch_size=None)
        return self.mark_prompts_generated(pending)

    def mark_prompts_pending(
        self,
        prompts: list,
    ) -> int:
        """Mark prompts as pending in both history ledger and prompts.json.
        
        Removes the prompt hash from the generation history ledger and
        reverts its status to 'pending' in prompts.json.
        
        Args:
            prompts: List of PromptItem, strings, or dicts to mark as pending.
            
        Returns:
            Number of prompts successfully reverted to pending.
        """
        if not prompts:
            return 0

        target_hashes = set()
        for item in prompts:
            if hasattr(item, "prompt_hash"):
                target_hashes.add(item.prompt_hash.lower())
            elif isinstance(item, str):
                target_hashes.add(item.lower() if len(item) == 64 else self.compute_hash(item).lower())
            elif isinstance(item, dict):
                p_text = item.get("prompt_text") or self.extract_prompt_text(item)
                p_hash = item.get("full_hash") or item.get("prompt_hash") or (self.compute_hash(p_text) if p_text else None)
                if p_hash:
                    target_hashes.add(str(p_hash).lower())

        if not target_hashes:
            return 0

        # 1. Remove from history ledger
        removed_history = False
        to_del_keys = [k for k in self._history if k.lower() in target_hashes or any(k.lower().startswith(h) for h in target_hashes)]
        for k in to_del_keys:
            del self._history[k]
            removed_history = True

        if removed_history:
            self._save_history()

        # 2. Update prompts.json atomically
        raw_data = self._load_prompts_data()
        updated_any = False

        for group in raw_data:
            for p in group.get("generated_prompts", []):
                p_text = self.extract_prompt_text(p)
                p_hash = self.compute_hash(p_text).lower()
                existing_hash = str(p.get("prompt_hash", "")).lower()
                if (p_hash in target_hashes) or (existing_hash in target_hashes) or any(p_hash.startswith(h) for h in target_hashes):
                    p["status"] = "pending"
                    p.pop("generated_at", None)
                    p.pop("image_file", None)
                    updated_any = True

        if updated_any:
            self._save_prompts_data(raw_data)

        logger.info(f"⏳ {len(target_hashes)} prompts revertidos para status pending.")
        return len(target_hashes)

    def mark_pending_by_hashes(self, hashes: list) -> int:
        """Mark prompts matching specific hashes (full or prefix) as pending."""
        if not hashes:
            return 0
        hash_set = {str(h).strip().lower() for h in hashes if h and str(h).strip()}
        all_items = self.get_all_prompts()
        matching = [
            p for p in all_items
            if (p.prompt_hash.lower() in hash_set or p.prompt_hash[:12].lower() in hash_set)
        ]
        return self.mark_prompts_pending(matching)

    def mark_all_generated_pending(self) -> int:
        """Mark all currently generated prompts in the queue back to pending."""
        all_items = self.get_all_prompts()
        generated = [p for p in all_items if p.status == "generated"]
        return self.mark_prompts_pending(generated)


    def reconcile_existing_images(self) -> int:
        """Bootstrap / sync existing images in data/final/images/ with pending prompts.
        
        If images exist in the final directory that are not yet recorded in the history ledger,
        automatically marks corresponding pending prompts as generated, preventing duplicate
        generation and linking each asset to a distinct prompt.
        """
        if not self.images_dir.exists():
            return 0

        existing_images = sorted(
            [f for f in self.images_dir.iterdir() if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".jpeg"]],
            key=lambda p: p.stat().st_mtime,
        )

        if not existing_images:
            return 0

        recorded_images: Set[str] = {
            entry.get("image_file")
            for entry in self._history.values()
            if isinstance(entry, dict) and entry.get("image_file")
        }

        unrecorded_images = [img for img in existing_images if img.name not in recorded_images]
        if not unrecorded_images:
            return 0

        pending = self.get_pending_prompts(batch_size=len(unrecorded_images))
        if not pending:
            return 0

        images_to_link = [img.name for img in unrecorded_images[:len(pending)]]
        marked = self.mark_prompts_generated(pending, saved_images=images_to_link)
        logger.info(f"🔄 Reconciliação: {marked} prompts sincronizados com imagens existentes em {self.images_dir.name}.")
        return marked

    def get_stats(self) -> Dict[str, Any]:
        """Return total, generated, pending prompts count and percentage."""
        all_items = self.get_all_prompts()
        total = len(all_items)
        generated = sum(1 for p in all_items if p.status == "generated")
        pending = total - generated
        pct = round((generated / total * 100), 1) if total > 0 else 0.0

        videos_count = 0
        if FINAL_VIDEOS_DIR.exists():
            videos_count = len(list(FINAL_VIDEOS_DIR.glob("*.mp4")) + list(FINAL_VIDEOS_DIR.glob("*.mov")))

        return {
            "total": total,
            "generated": generated,
            "pending": pending,
            "progress_percent": pct,
            "final_videos": videos_count,
        }
