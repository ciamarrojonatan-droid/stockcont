"""StockCont — B2B Zero-Trademark Promo Motion Director & Variety Audit (Sprint 11).

Applies architectural patterns from `onetake`, `saas-motion-kit`, and `cursorcam`
to produce silent (-an) pure-code 4K/1080p SaaS & FinTech stock motion assets with:
1. Strict trademark sanitization (blocking commercial brand strings prior to agency upload).
2. Deterministic Tone Matrix variation across camera vectors, chromatic hues & templates.
3. Pairwise pixel + structural Variety & Anti-Sameness auditing to avoid agency spam rejections.
4. ADR-05 active Alamy blocking and Unit Economics royalty estimation.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.analyzer.unit_economics import NICHE_ROYALTY_RATES
from src.cataloger.platform_compliance import PLATFORM_RULES
from src.video.ffmpeg_processor import probe_video
from src.video.hyperframes_engine import HyperFramesMotionEngine

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("stockcont.video.promo_motion_director")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_PROMO_DIR = BASE_DIR / "data" / "final" / "promo_b2b"

PROMO_PRESETS: Tuple[str, ...] = (
    "onetake_bento_launch",
    "cursor_spotlight_demo",
    "kpi_metric_cascade",
)

PROMO_TONE_MATRIX: List[Dict[str, Any]] = [
    {
        "tone": "fintech_cobalt",
        "bg_hex": "#070D19",
        "accent_hex": "#38BDF8",
        "personality": "clinical_fintech",
        "camera_vector": "pan_left",
    },
    {
        "tone": "obsidian_amber",
        "bg_hex": "#161006",
        "accent_hex": "#F59E0B",
        "personality": "high_energy_hook",
        "camera_vector": "diagonal_glide",
    },
    {
        "tone": "emerald_terminal",
        "bg_hex": "#051914",
        "accent_hex": "#10B981",
        "personality": "executive_corporate",
        "camera_vector": "push_in",
    },
    {
        "tone": "crimson_radar",
        "bg_hex": "#19080E",
        "accent_hex": "#FB7185",
        "personality": "cold_war_noir",
        "camera_vector": "zoom_cascade",
    },
]

BANNED_TRADEMARK_TERMS: Tuple[str, ...] = (
    "apple",
    "iphone",
    "macbook",
    "google",
    "youtube",
    "stripe",
    "openai",
    "chatgpt",
    "microsoft",
    "windows",
    "figma",
    "notion",
    "amazon",
    "aws",
    "adobe",
    "meta",
    "instagram",
    "tiktok",
    "nvidia",
    "tesla",
    "slack",
    "salesforce",
)

_TRADEMARK_REGEX = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in BANNED_TRADEMARK_TERMS) + r")(?:'s|s|\d+)?\b",
    flags=re.IGNORECASE,
)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip().lower()).strip("_")[:64] or "promo_asset"


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


@dataclass
class PromoMotionAsset:
    """Single generated B2B SaaS/FinTech silent promo motion clip."""

    index: int
    preset: str
    tone: str
    camera_vector: str
    title: str
    subtitle: str
    video_path: Optional[str]
    html_path: Optional[str]
    signature_vector: List[float] = field(default_factory=list)
    has_audio: bool = False
    width: int = 1920
    height: int = 1080
    qa_passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VarietyAuditResult:
    """Pairwise visual & structural anti-sameness audit report across a promo batch."""

    passed: bool
    min_pairwise_distance: float
    threshold: float
    similar_pairs: List[Dict[str, Any]] = field(default_factory=list)
    trademark_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PromoBatchResult:
    """Complete B2B promo motion batch manifest and economics summary."""

    success: bool
    niche_id: str
    assets: List[Dict[str, Any]] = field(default_factory=list)
    variety_audit: Dict[str, Any] = field(default_factory=dict)
    estimated_unit_royalty_usd: float = 0.0
    alamy_blocked: bool = True
    eligible_agencies: List[str] = field(default_factory=list)
    manifest_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PromoMotionDirector:
    """Generates varied, trademark-free B2B SaaS motion assets ready for microstock."""

    def __init__(self, output_dir: Optional[str | Path] = None):
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_PROMO_DIR

    @staticmethod
    def sanitize_trademark_free(text: str) -> Tuple[str, List[str]]:
        """Detect prohibited commercial trademark strings and return scrubbed text + matches."""
        raw = text or ""
        matches = sorted({m.group(1).lower() for m in _TRADEMARK_REGEX.finditer(raw)})
        scrubbed = _TRADEMARK_REGEX.sub("EnterprisePlatform", raw)
        return scrubbed, matches

    @staticmethod
    def compute_signature_vector(
        preset: str,
        tone_idx: int,
        camera_vector: str,
        video_path: Optional[str | Path] = None,
    ) -> List[float]:
        """Compute deterministic feature signature combining visual frame stats and motion vector."""
        preset_norm = (PROMO_PRESETS.index(preset) / max(1, len(PROMO_PRESETS) - 1)) if preset in PROMO_PRESETS else 0.5
        tone_norm = (tone_idx % len(PROMO_TONE_MATRIX)) / max(1, len(PROMO_TONE_MATRIX) - 1)
        cam_map = {"pan_left": 0.1, "diagonal_glide": 0.4, "push_in": 0.7, "zoom_cascade": 1.0}
        cam_norm = cam_map.get(camera_vector, 0.5)

        b_mean, g_mean, r_mean, edge_density = 0.15, 0.20, 0.25, 0.10
        if video_path and Path(video_path).is_file():
            cap = cv2.VideoCapture(str(video_path))
            try:
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                if frame_count > 0:
                    indices = sorted({0, frame_count // 3, (2 * frame_count) // 3, max(0, frame_count - 1)})
                    b_vals, g_vals, r_vals, e_vals = [], [], [], []
                    for fidx in indices:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
                        ok, frame = cap.read()
                        if not ok or frame is None:
                            continue
                        small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
                        b_vals.append(float(np.mean(small[:, :, 0])) / 255.0)
                        g_vals.append(float(np.mean(small[:, :, 1])) / 255.0)
                        r_vals.append(float(np.mean(small[:, :, 2])) / 255.0)
                        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                        edges = cv2.Canny(gray, 50, 150)
                        e_vals.append(float(np.mean(edges > 0)))
                    if b_vals:
                        b_mean = sum(b_vals) / len(b_vals)
                        g_mean = sum(g_vals) / len(g_vals)
                        r_mean = sum(r_vals) / len(r_vals)
                        edge_density = sum(e_vals) / len(e_vals)
            finally:
                cap.release()

        return [
            round(preset_norm, 4),
            round(tone_norm, 4),
            round(cam_norm, 4),
            round(b_mean, 4),
            round(g_mean, 4),
            round(r_mean, 4),
            round(edge_density, 4),
        ]

    @staticmethod
    def audit_batch_variety(
        assets: List[PromoMotionAsset],
        min_distance: float = 0.20,
        trademark_violations: Optional[List[str]] = None,
    ) -> VarietyAuditResult:
        """Verify pairwise feature distance across batch so clips are not flagged as duplicate spam."""
        threshold = max(0.01, float(min_distance))
        trademarks = list(trademark_violations or [])
        if len(assets) <= 1:
            return VarietyAuditResult(
                passed=len(trademarks) == 0,
                min_pairwise_distance=1.0,
                threshold=threshold,
                similar_pairs=[],
                trademark_violations=trademarks,
            )

        min_dist = float("inf")
        similar: List[Dict[str, Any]] = []
        for i in range(len(assets)):
            va = assets[i].signature_vector
            for j in range(i + 1, len(assets)):
                vb = assets[j].signature_vector
                dim = min(len(va), len(vb))
                dist = math.sqrt(sum((va[k] - vb[k]) ** 2 for k in range(dim))) if dim > 0 else 0.0
                dist_r = round(dist, 4)
                if dist_r < min_dist:
                    min_dist = dist_r
                if dist_r < threshold:
                    similar.append(
                        {
                            "asset_a": assets[i].index,
                            "asset_b": assets[j].index,
                            "preset_a": assets[i].preset,
                            "preset_b": assets[j].preset,
                            "tone_a": assets[i].tone,
                            "tone_b": assets[j].tone,
                            "distance": dist_r,
                        }
                    )

        return VarietyAuditResult(
            passed=(len(similar) == 0 and len(trademarks) == 0),
            min_pairwise_distance=round(min_dist if min_dist != float("inf") else 1.0, 4),
            threshold=threshold,
            similar_pairs=similar,
            trademark_violations=trademarks,
        )

    @staticmethod
    def _eligible_agencies() -> List[str]:
        return sorted(
            name
            for name, spec in PLATFORM_RULES.items()
            if getattr(spec, "allows_ai", False) and name != "alamy"
        )

    def generate_promo_batch(
        self,
        title: str,
        subtitle: str = "SYNTHETIC TELEMETRY OVERVIEW",
        niche_id: str = "finance",
        count: int = 3,
        preset: str = "AUTO",
        width: int = 1920,
        height: int = 1080,
        duration_sec: float = 3.0,
        fps: int = 24,
        output_dir: Optional[str | Path] = None,
        strict_trademark: bool = True,
        min_variety_distance: float = 0.20,
        run_qa_gate: bool = True,
    ) -> PromoBatchResult:
        """Render a batch of trademark-free silent B2B promo clips with anti-sameness QA."""
        if not title or not title.strip():
            raise ValueError("Promo batch title cannot be empty.")

        niche_key = (niche_id or "finance").strip().lower()
        if niche_key not in NICHE_ROYALTY_RATES:
            raise ValueError(f"Unknown niche_id '{niche_id}'. Valid: {sorted(NICHE_ROYALTY_RATES)}")

        preset_upper = (preset or "AUTO").strip()
        if preset_upper.upper() != "AUTO" and preset_upper not in PROMO_PRESETS:
            raise ValueError(f"Unknown promo preset '{preset}'. Valid: ['AUTO', {', '.join(PROMO_PRESETS)}]")

        clean_title, tm_title = self.sanitize_trademark_free(title)
        clean_sub, tm_sub = self.sanitize_trademark_free(subtitle)
        violations = sorted(set(tm_title + tm_sub))
        if strict_trademark and violations:
            raise ValueError(
                f"Trademark-protected terms prohibited in microstock B2B promo UI: {violations}"
            )

        out_root = Path(output_dir) if output_dir else self.output_dir
        out_root.mkdir(parents=True, exist_ok=True)
        batch_slug = _slugify(clean_title)
        n_items = max(1, min(8, int(count)))

        hf = HyperFramesMotionEngine(output_dir=out_root)
        assets: List[PromoMotionAsset] = []
        for idx in range(n_items):
            chosen_preset = PROMO_PRESETS[idx % len(PROMO_PRESETS)] if preset_upper.upper() == "AUTO" else preset_upper
            tone_spec = PROMO_TONE_MATRIX[idx % len(PROMO_TONE_MATRIX)]
            item_title = f"{clean_title[:42]} // V{idx + 1:02d}" if n_items > 1 else clean_title
            out_clip = out_root / f"{batch_slug}_v{idx + 1:02d}_{chosen_preset}.mp4"

            comp = hf.render_motion_clip(
                template=chosen_preset,
                title=item_title,
                subtitle=clean_sub,
                output_path=out_clip,
                duration_sec=duration_sec,
                width=width,
                height=height,
                fps=fps,
                data={
                    "bg_hex": tone_spec["bg_hex"],
                    "accent_hex": tone_spec["accent_hex"],
                    "camera_vector": tone_spec["camera_vector"],
                },
                force_procedural=True,
                muted=True,
                seed=1000 + idx * 7919,
                personality=tone_spec["personality"],
                run_qa_gate=run_qa_gate,
            )

            has_audio = False
            qa_passed = True
            if comp.output_video_path and comp.output_video_path.is_file():
                has_audio = probe_video(comp.output_video_path).has_audio
            if comp.qa_report:
                qa_passed = bool(comp.qa_report.get("passed", True))

            sig = self.compute_signature_vector(
                preset=chosen_preset,
                tone_idx=idx,
                camera_vector=tone_spec["camera_vector"],
                video_path=comp.output_video_path,
            )
            assets.append(
                PromoMotionAsset(
                    index=idx + 1,
                    preset=chosen_preset,
                    tone=tone_spec["tone"],
                    camera_vector=tone_spec["camera_vector"],
                    title=item_title,
                    subtitle=clean_sub,
                    video_path=comp.output_video_path.as_posix() if comp.output_video_path else None,
                    html_path=comp.html_path.as_posix() if comp.html_path else None,
                    signature_vector=sig,
                    has_audio=has_audio,
                    width=width,
                    height=height,
                    qa_passed=qa_passed,
                )
            )

        variety = self.audit_batch_variety(
            assets=assets,
            min_distance=min_variety_distance,
            trademark_violations=violations,
        )
        royalty = float(NICHE_ROYALTY_RATES[niche_key]["video_royalty_usd"])
        eligible = self._eligible_agencies()
        manifest_path = out_root / f"{batch_slug}_promo_manifest.json"
        all_rendered = all(a.video_path is not None and not a.has_audio for a in assets)

        res = PromoBatchResult(
            success=bool(all_rendered and variety.passed),
            niche_id=niche_key,
            assets=[a.to_dict() for a in assets],
            variety_audit=variety.to_dict(),
            estimated_unit_royalty_usd=round(royalty, 2),
            alamy_blocked=True,
            eligible_agencies=eligible,
            manifest_path=manifest_path.as_posix(),
            error=(
                None
                if (all_rendered and variety.passed)
                else "One or more promo assets failed silent render or variety audit."
            ),
        )
        _atomic_write_json(manifest_path, res.to_dict())
        return res
