"""StockCont — Unit Economics, GPU Batch Costing & Niche ROI Calculator.

Quantifica o custo unitário real por ativo (Gemini Vision + QC + GPU RunningHub
Lite/Plus + SeedVR 8K) frente à receita líquida projetada por nicho comercial
(`NICHE_DEFINITIONS`), recomendando alocação de lotes de maior margem.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.analyzer.commercial_scorer import NICHE_DEFINITIONS

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_ECONOMICS_REPORT = BASE_DIR / "data" / "processed" / "unit_economics_report.json"

# Conservative blended royalty per download (USD) across Adobe Stock / Freepik / 123RF / Pond5
NICHE_ROYALTY_RATES: Dict[str, Dict[str, float]] = {
    "finance": {"image_royalty_usd": 1.45, "video_royalty_usd": 18.50, "conversion_multiplier": 1.18},
    "biotech": {"image_royalty_usd": 1.35, "video_royalty_usd": 17.00, "conversion_multiplier": 1.15},
    "podium": {"image_royalty_usd": 0.98, "video_royalty_usd": 12.00, "conversion_multiplier": 1.12},
    "tech_space": {"image_royalty_usd": 1.05, "video_royalty_usd": 14.50, "conversion_multiplier": 1.05},
    "abstract": {"image_royalty_usd": 0.68, "video_royalty_usd": 8.50, "conversion_multiplier": 0.95},
}


@dataclass(frozen=True)
class UnitCostBreakdown:
    asset_type: str
    gemini_usd: float
    gpu_usd: float
    upscale_usd: float
    storage_and_sync_usd: float
    total_cost_usd: float


class UnitEconomicsCalculator:
    """Computes asset-level unit costs, break-even downloads, and niche ROI rankings."""

    def __init__(
        self,
        gemini_vision_cost_per_prompt: float = 0.0025,
        gemini_qc_cost_per_asset: float = 0.0015,
        raw_gpu_cost_per_image: float = 0.0120,
        upscale_gpu_cost_per_image: float = 0.0080,
        video_gpu_cost_per_clip: float = 0.0950,
        storage_cost_per_asset: float = 0.0012,
    ):
        self.gemini_vision_cost_per_prompt = gemini_vision_cost_per_prompt
        self.gemini_qc_cost_per_asset = gemini_qc_cost_per_asset
        self.raw_gpu_cost_per_image = raw_gpu_cost_per_image
        self.upscale_gpu_cost_per_image = upscale_gpu_cost_per_image
        self.video_gpu_cost_per_clip = video_gpu_cost_per_clip
        self.storage_cost_per_asset = storage_cost_per_asset

    def calculate_asset_unit_cost(
        self,
        asset_type: str = "image",
        include_upscale: bool = True,
        gemini_calls: int = 1,
        batch_utilization: float = 1.0,
    ) -> Dict[str, Any]:
        """Return itemized USD production cost for a single generated stock asset."""
        kind = (asset_type or "image").strip().lower()
        if kind not in ("image", "video"):
            raise ValueError(f"Unsupported asset_type '{asset_type}'; expected 'image' or 'video'.")

        utilization = max(0.10, min(1.0, float(batch_utilization)))
        calls = max(0, int(gemini_calls))
        gemini_usd = calls * (self.gemini_vision_cost_per_prompt + self.gemini_qc_cost_per_asset)

        if kind == "video":
            gpu_usd = self.video_gpu_cost_per_clip / utilization
            upscale_usd = 0.0
            storage_usd = self.storage_cost_per_asset * 3.0
        else:
            gpu_usd = self.raw_gpu_cost_per_image / utilization
            upscale_usd = (self.upscale_gpu_cost_per_image / utilization) if include_upscale else 0.0
            storage_usd = self.storage_cost_per_asset

        total = gemini_usd + gpu_usd + upscale_usd + storage_usd
        breakdown = UnitCostBreakdown(
            asset_type=kind,
            gemini_usd=round(gemini_usd, 6),
            gpu_usd=round(gpu_usd, 6),
            upscale_usd=round(upscale_usd, 6),
            storage_and_sync_usd=round(storage_usd, 6),
            total_cost_usd=round(total, 6),
        )
        return asdict(breakdown)

    def calculate_niche_roi(
        self,
        niche_id: str,
        asset_type: str = "image",
        batch_size: int = 210,
        expected_downloads_per_asset: float = 1.5,
        include_upscale: bool = True,
    ) -> Dict[str, Any]:
        """Compute batch unit economics and ROI for one niche in `NICHE_DEFINITIONS`."""
        if niche_id not in NICHE_DEFINITIONS:
            raise ValueError(f"Unknown niche_id '{niche_id}'. Valid: {sorted(NICHE_DEFINITIONS)}")

        kind = (asset_type or "image").strip().lower()
        n_assets = max(1, int(batch_size))
        dl_per_asset = max(0.0, float(expected_downloads_per_asset))

        cost_info = self.calculate_asset_unit_cost(asset_type=kind, include_upscale=include_upscale)
        unit_cost = cost_info["total_cost_usd"]
        batch_cost = round(unit_cost * n_assets, 4)

        niche_meta = NICHE_DEFINITIONS[niche_id]
        rate_meta = NICHE_ROYALTY_RATES.get(
            niche_id,
            {"image_royalty_usd": 0.90, "video_royalty_usd": 11.0, "conversion_multiplier": 1.0},
        )
        royalty_key = "video_royalty_usd" if kind == "video" else "image_royalty_usd"
        base_royalty = rate_meta[royalty_key]
        bonus_factor = 1.0 + max(0.0, float(niche_meta.get("bonus", 20.0)) - 20.0) * 0.015
        effective_royalty = base_royalty * bonus_factor
        effective_downloads = dl_per_asset * rate_meta.get("conversion_multiplier", 1.0)

        projected_gross = round(n_assets * effective_downloads * effective_royalty, 4)
        projected_net = round(projected_gross - batch_cost, 4)
        roi_pct = round(((projected_gross - batch_cost) / max(1e-9, batch_cost)) * 100.0, 2)
        breakeven_dl = round(unit_cost / max(1e-9, effective_royalty), 4)

        return {
            "niche_id": niche_id,
            "niche_name": niche_meta["name"],
            "buyer_intent": niche_meta["buyer_intent"],
            "asset_type": kind,
            "batch_size": n_assets,
            "unit_cost_usd": unit_cost,
            "effective_royalty_usd": round(effective_royalty, 4),
            "batch_cost_usd": batch_cost,
            "projected_gross_usd": projected_gross,
            "projected_net_usd": projected_net,
            "roi_pct": roi_pct,
            "breakeven_downloads_per_asset": breakeven_dl,
        }

    def recommend_priority_niches(
        self,
        asset_type: str = "image",
        batch_size: int = 210,
        expected_downloads_per_asset: float = 1.5,
        include_upscale: bool = True,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Rank all configured commercial niches by projected ROI descending."""
        rows = [
            self.calculate_niche_roi(
                niche_id=niche_id,
                asset_type=asset_type,
                batch_size=batch_size,
                expected_downloads_per_asset=expected_downloads_per_asset,
                include_upscale=include_upscale,
            )
            for niche_id in NICHE_DEFINITIONS
        ]
        rows.sort(key=lambda item: (item["roi_pct"], item["projected_net_usd"]), reverse=True)
        if top_k is not None and top_k > 0:
            return rows[:top_k]
        return rows

    def export_report(
        self,
        output_path: str | Path = DEFAULT_ECONOMICS_REPORT,
        asset_type: str = "image",
        batch_size: int = 210,
        expected_downloads_per_asset: float = 1.5,
    ) -> Path:
        """Write an atomic JSON unit economics report (ADR-02)."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "asset_type": asset_type,
            "batch_size": batch_size,
            "expected_downloads_per_asset": expected_downloads_per_asset,
            "unit_cost_breakdown": self.calculate_asset_unit_cost(asset_type=asset_type),
            "niches": self.recommend_priority_niches(
                asset_type=asset_type,
                batch_size=batch_size,
                expected_downloads_per_asset=expected_downloads_per_asset,
            ),
        }
        tmp_path = target.with_name(f"{target.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        tmp_path.replace(target)
        return target
