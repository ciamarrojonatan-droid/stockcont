"""StockCont & DarkFactory — Storyboard & Budget Compiler.

Compiles a raw documentary narration script + B2B niche into an audited,
multi-track production storyboard with 0.5s spatial overlap verification,
retention gate telemetry (Murch/MrBeast/Cron), and unit economics budgeting.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.analyzer.unit_economics import NICHE_DEFINITIONS, UnitEconomicsCalculator
from src.video.motion_qa import MotionQAInspector, OverlayPlacement
from src.video.story_validator import DarkFactoryStoryValidator

# Reconfigure stdout/stderr to UTF-8 on Windows (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_STORYBOARD_DIR = BASE_DIR / "data" / "processed" / "storyboards"


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", (value or "storyboard").strip().lower()).strip("_")[:60] or "storyboard"


def _atomic_write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return path


@dataclass
class StoryboardScene:
    """Single compiled visual beat in a documentary storyboard."""

    scene_id: int
    start_sec: float
    end_sec: float
    duration_sec: float
    narration_excerpt: str
    visual_track: str  # "pd_archival" | "vector_map" | "t2v_shot" | "tactical_hud"
    camera_directive: str
    hud_overlay: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoryboardCompileResult:
    """Compiled storyboard manifest with retention, overlap, and budget telemetry."""

    success: bool
    title: str
    slug: str
    target_niche: str
    total_duration_sec: float
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    hook_audit: Dict[str, Any] = field(default_factory=dict)
    story_audit: Dict[str, Any] = field(default_factory=dict)
    overlap_audit: Dict[str, Any] = field(default_factory=dict)
    budget_estimate: Dict[str, Any] = field(default_factory=dict)
    manifest_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StoryboardCompiler:
    """Transforms narration scripts into budgeted, layout-verified production manifests."""

    VISUAL_TRACK_CYCLE = (
        ("pd_archival", "Slow archival push-in across grain-preserved primary document"),
        ("vector_map", "12fps geopolitical corridor animation panning between target coordinates"),
        ("t2v_shot", "Low-key moody Cold War bunker dolly shot with amber CRT rim lighting"),
        ("tactical_hud", "Declassified stamp pop + typewriter telemetry readout over darkened bed"),
    )

    def __init__(self, output_dir: Optional[Path | str] = None) -> None:
        self.output_dir = Path(output_dir).resolve() if output_dir else DEFAULT_STORYBOARD_DIR.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compile_storyboard(
        self,
        title: str,
        script: str,
        target_niche: str = "industrial_automation",
        target_duration_sec: float = 20.0,
        theater: str = "europe_cold_war",
    ) -> StoryboardCompileResult:
        """Split script into beats, validate retention/HUD overlaps, and project budget."""
        clean_title = (title or "Untitled Episode").strip()
        clean_script = re.sub(r"\s+", " ", (script or "").strip())
        if not clean_script:
            raise ValueError("Script cannot be empty when compiling a storyboard.")

        slug = _slugify(clean_title)
        total_dur = max(4.0, float(target_duration_sec))

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_script) if s.strip()]
        if not sentences:
            sentences = [clean_script]
        # Ensure at least 4 dynamic cuts even for compact prompts (MrBeast/Murch cadence)
        while len(sentences) < 4:
            longest_idx = max(range(len(sentences)), key=lambda i: len(sentences[i]))
            words = sentences[longest_idx].split()
            if len(words) < 6:
                sentences.append(sentences[longest_idx])
            else:
                mid = len(words) // 2
                sentences[longest_idx : longest_idx + 1] = [" ".join(words[:mid]), " ".join(words[mid:])]

        per_scene = round(total_dur / len(sentences), 3)
        scenes: List[StoryboardScene] = []
        placements: List[OverlayPlacement] = []
        validator_scenes: List[Dict[str, Any]] = []

        cursor = 0.0
        for idx, excerpt in enumerate(sentences, start=1):
            dur = per_scene if idx < len(sentences) else round(max(1.0, total_dur - cursor), 3)
            end_t = round(cursor + dur, 3)
            track, cam = self.VISUAL_TRACK_CYCLE[(idx - 1) % len(self.VISUAL_TRACK_CYCLE)]
            hud_kind = "lower_third" if idx % 2 == 1 else "stamp_badge"

            scenes.append(
                StoryboardScene(
                    scene_id=idx,
                    start_sec=round(cursor, 3),
                    end_sec=end_t,
                    duration_sec=dur,
                    narration_excerpt=excerpt,
                    visual_track=track,
                    camera_directive=cam,
                    hud_overlay=hud_kind,
                )
            )
            if hud_kind == "lower_third":
                placements.append(
                    OverlayPlacement(
                        overlay_id=f"lt_{idx}",
                        label=f"Lower Third Scene {idx}",
                        start_sec=round(cursor + 0.1, 3),
                        end_sec=max(round(cursor + 0.2, 3), round(end_t - 0.1, 3)),
                        x=0.05,
                        y=0.77,
                        width=0.52,
                        height=0.14,
                    )
                )
            else:
                placements.append(
                    OverlayPlacement(
                        overlay_id=f"badge_{idx}",
                        label=f"Declassified Stamp {idx}",
                        start_sec=round(cursor + 0.1, 3),
                        end_sec=max(round(cursor + 0.2, 3), round(end_t - 0.1, 3)),
                        x=0.70,
                        y=0.06,
                        width=0.24,
                        height=0.13,
                    )
                )

            half_d = round(max(0.5, dur * 0.5), 3)
            validator_scenes.append(
                {
                    "scene_id": idx,
                    "narrative_beat": f"Beat {idx}: {excerpt[:40]}",
                    "shot_a": {"duration": half_d, "subject": excerpt},
                    "shot_b": {"duration": round(max(0.5, dur - half_d), 3), "subject": cam},
                }
            )
            cursor = end_t

        validator = DarkFactoryStoryValidator()
        hook_res = validator.audit_5s_hook_clarity(sentences[0])
        story_res = validator.audit_episode_manifest(
            project_title=clean_title,
            scenes=validator_scenes,
            script_narration_full=clean_script,
        )
        overlap_res = MotionQAInspector().audit_overlay_overlaps(
            placements=placements,
            total_duration_sec=total_dur,
            step_sec=0.5,
        )

        # Unit economics & niche projection
        econ = UnitEconomicsCalculator()
        unit_video = econ.calculate_asset_unit_cost(asset_type="video", gemini_calls=2)
        niche_key = target_niche if target_niche in NICHE_DEFINITIONS else next(iter(NICHE_DEFINITIONS))
        niche_roi = econ.calculate_niche_roi(
            niche_id=niche_key,
            asset_type="video",
            batch_size=max(3, len(scenes)),
            expected_downloads_per_asset=1.5,
        )
        budget_estimate = {
            "niche_id": niche_key,
            "scene_count": len(scenes),
            "per_clip_unit_cost_usd": unit_video["total_cost_usd"],
            "total_production_cost_usd": round(unit_video["total_cost_usd"] * len(scenes), 4),
            "projected_stock_broll_gross_usd": niche_roi["projected_gross_usd"],
            "projected_stock_broll_net_usd": niche_roi["projected_net_usd"],
            "projected_roi_pct": niche_roi["roi_pct"],
            "breakdown": unit_video,
        }

        manifest_file = self.output_dir / f"{slug}_storyboard.json"
        payload = {
            "success": True,
            "title": clean_title,
            "slug": slug,
            "target_niche": niche_key,
            "theater": theater,
            "total_duration_sec": round(cursor, 3),
            "scenes": [s.to_dict() for s in scenes],
            "hook_audit": hook_res.to_dict(),
            "story_audit": story_res.to_dict(),
            "overlap_audit": overlap_res.to_dict(),
            "budget_estimate": budget_estimate,
        }
        _atomic_write_json(manifest_file, payload)

        return StoryboardCompileResult(
            success=True,
            title=clean_title,
            slug=slug,
            target_niche=niche_key,
            total_duration_sec=round(cursor, 3),
            scenes=[s.to_dict() for s in scenes],
            hook_audit=hook_res.to_dict(),
            story_audit=story_res.to_dict(),
            overlap_audit=overlap_res.to_dict(),
            budget_estimate=budget_estimate,
            manifest_path=manifest_file.as_posix(),
        )
