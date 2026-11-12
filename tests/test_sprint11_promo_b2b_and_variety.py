"""Sprint 11 TDD Suite: Zero-Trademark B2B Promo Motion Templates & Variety/Anti-Sameness Audit."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.analyzer.unit_economics import NICHE_ROYALTY_RATES
from src.dashboard.app import app
from src.video.ffmpeg_processor import probe_video
from src.video.hyperframes_engine import HyperFramesMotionEngine
from src.video.promo_motion_director import (
    PROMO_PRESETS,
    PromoMotionAsset,
    PromoMotionDirector,
)


def test_sprint10_and_11_templates_render_silent_clean_mp4(tmp_path):
    engine = HyperFramesMotionEngine(output_dir=tmp_path)

    for preset in PROMO_PRESETS:
        out = tmp_path / f"{preset}.mp4"
        res = engine.render_motion_clip(
            template=preset,
            title="Q4 TREASURY LIQUIDITY OVERVIEW",
            subtitle="SYNTHETIC TELEMETRY FEED // USD +42%",
            output_path=out,
            duration_sec=1.5,
            width=640,
            height=360,
            fps=12,
            force_procedural=True,
            muted=True,
            seed=42,
        )
        assert res.success is True, res.error
        props = probe_video(out)
        assert props.width == 640
        assert props.height == 360
        assert props.has_audio is False

        cap = cv2.VideoCapture(str(out))
        ret, frame = cap.read()
        cap.release()
        assert ret is True and frame is not None
        assert float(np.std(frame)) > 5.0

    for vertical_tpl in ("vertical_dossier_short", "vertical_kinetic_quote"):
        out_v = tmp_path / f"{vertical_tpl}.mp4"
        res_v = engine.render_motion_clip(
            template=vertical_tpl,
            title="CLASSIFIED DOSSIER BRIEF",
            subtitle="ARCHIVAL RECORD 1983",
            output_path=out_v,
            duration_sec=1.5,
            width=360,
            height=640,
            fps=12,
            force_procedural=True,
            muted=True,
            seed=77,
        )
        assert res_v.success is True, res_v.error
        props_v = probe_video(out_v)
        assert props_v.width == 360
        assert props_v.height == 640
        assert props_v.has_audio is False


def test_trademark_sanitization_and_strict_enforcement(tmp_path):
    scrubbed, matches = PromoMotionDirector.sanitize_trademark_free(
        "Apple iPhones analytics compared with Stripe, Teslas and ChatGPT4 billing"
    )
    assert "apple" in matches
    assert "iphone" in matches
    assert "stripe" in matches
    assert "tesla" in matches
    assert "chatgpt" in matches
    assert "iphones" not in scrubbed.lower()
    assert "chatgpt4" not in scrubbed.lower()
    assert "EnterprisePlatform" in scrubbed

    director = PromoMotionDirector(output_dir=tmp_path)
    with pytest.raises(ValueError, match="Trademark-protected"):
        director.generate_promo_batch(
            title="Google Cloud vs Nvidia Metrics",
            niche_id="finance",
            strict_trademark=True,
        )


def test_variety_audit_passes_varied_batch_and_flags_clones(tmp_path):
    director = PromoMotionDirector(output_dir=tmp_path)
    batch = director.generate_promo_batch(
        title="Autonomous Settlement Architecture",
        subtitle="REALTIME TREASURY FLOW TELEMETRY",
        niche_id="finance",
        count=3,
        preset="AUTO",
        width=640,
        height=360,
        duration_sec=1.5,
        fps=12,
    )

    assert batch.success is True, batch.error
    assert len(batch.assets) == 3
    assert batch.variety_audit["passed"] is True
    assert batch.variety_audit["min_pairwise_distance"] >= 0.20
    assert batch.estimated_unit_royalty_usd == float(NICHE_ROYALTY_RATES["finance"]["video_royalty_usd"])
    assert batch.alamy_blocked is True
    assert "alamy" not in batch.eligible_agencies
    assert "adobe" in batch.eligible_agencies

    seen_presets = {a["preset"] for a in batch.assets}
    seen_tones = {a["tone"] for a in batch.assets}
    assert len(seen_presets) == 3
    assert len(seen_tones) == 3

    for asset in batch.assets:
        clip = Path(asset["video_path"])
        assert clip.is_file()
        assert probe_video(clip).has_audio is False

    manifest = json.loads(Path(batch.manifest_path).read_text(encoding="utf-8"))
    assert manifest["variety_audit"]["passed"] is True

    # Identical pair triggers variety collision warning
    cloned_assets = [
        PromoMotionAsset(
            index=0,
            preset="onetake_bento_launch",
            tone="fintech_cobalt",
            camera_vector="pan_left",
            title="Twin A",
            subtitle="Clean Telemetry",
            video_path=None,
            html_path=None,
            signature_vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        ),
        PromoMotionAsset(
            index=1,
            preset="onetake_bento_launch",
            tone="fintech_cobalt",
            camera_vector="pan_left",
            title="Twin B",
            subtitle="Clean Telemetry",
            video_path=None,
            html_path=None,
            signature_vector=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        ),
    ]
    clone_audit = director.audit_batch_variety(cloned_assets, min_distance=0.20)
    assert clone_audit.passed is False
    assert len(clone_audit.similar_pairs) == 1


def test_sprint11_promo_endpoint_and_validation():
    client = TestClient(app)
    paths_to_clean: list[Path] = []

    try:
        res = client.post(
            "/api/v1/video/promo-motion-pack",
            json={
                "title": "Global Treasury Compliance Feed",
                "subtitle": "AUTOMATED LEDGER SETTLEMENT",
                "niche_id": "finance",
                "count": 2,
                "preset": "AUTO",
                "width": 640,
                "height": 360,
                "duration_sec": 1.2,
                "fps": 12,
                "strict_trademark": True,
            },
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["success"] is True
        assert body["alamy_blocked"] is True
        assert body["variety_audit"]["passed"] is True
        assert body["estimated_unit_royalty_usd"] == float(NICHE_ROYALTY_RATES["finance"]["video_royalty_usd"])
        assert len(body["assets"]) == 2

        if body.get("manifest_path"):
            paths_to_clean.append(Path(body["manifest_path"]))
        for asset in body["assets"]:
            for k in ("video_path", "html_path"):
                if asset.get(k):
                    p = Path(asset[k])
                    assert p.is_file()
                    paths_to_clean.append(p)
                    if k == "video_path":
                        paths_to_clean.append(p.with_name(f"{p.stem}_contact_sheet.png"))

        # Validation error gates return HTTP 400
        res_tm = client.post(
            "/api/v1/video/promo-motion-pack",
            json={"title": "Stripe Payment Telemetry", "strict_trademark": True},
        )
        assert res_tm.status_code == 400

        res_niche = client.post(
            "/api/v1/video/promo-motion-pack",
            json={"title": "Clean Telemetry", "niche_id": "nonexistent_niche"},
        )
        assert res_niche.status_code == 400

        res_preset = client.post(
            "/api/v1/video/promo-motion-pack",
            json={"title": "Clean Telemetry", "preset": "unknown_preset"},
        )
        assert res_preset.status_code == 400

        res_ws = client.post(
            "/api/v1/video/promo-motion-pack",
            json={"title": "   "},
        )
        assert res_ws.status_code == 400
    finally:
        for p in paths_to_clean:
            p.unlink(missing_ok=True)
