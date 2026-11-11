import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.director import (
    DIRECTOR_MODES,
    IMAGE_CODES_CATALOG,
    TECHNICAL_CODES_SUPPLEMENT,
    build_system_prompt,
    detect_director_mode,
    process_image,
)
from src.video.ffmpeg_processor import probe_video
from src.video.hyperframes_engine import HyperFramesMotionEngine, MOTION_TEMPLATES


def test_director_modes_and_seven_image_codes_present():
    assert "commercial_b2b" in DIRECTOR_MODES
    assert "image_codes_technical" in DIRECTOR_MODES

    expected_codes = {
        "/explodedview",
        "/blueprint",
        "/anatomy",
        "/360view",
        "/crosssection",
        "/xray",
        "/knolling",
    }
    assert expected_codes.issubset(set(IMAGE_CODES_CATALOG.keys()))
    for code in expected_codes:
        assert code in TECHNICAL_CODES_SUPPLEMENT


def test_detect_director_mode_auto_routes_technical_vs_commercial():
    assert detect_director_mode({"title": "Exploded view of industrial turbine engine schematic", "keywords": ["cad", "mechanical"]}) == "image_codes_technical"
    assert detect_director_mode({"title": "Minimalist corporate FinTech office workspace", "keywords": ["business", "laptop"]}) == "commercial_b2b"
    assert detect_director_mode({"title": "Random item"}, requested_mode="technical") == "image_codes_technical"
    assert detect_director_mode({"title": "Exploded turbine schematic"}, requested_mode="commercial") == "commercial_b2b"


def test_build_system_prompt_injects_image_codes_for_technical_mode():
    commercial_prompt = build_system_prompt(mode="commercial")
    technical_prompt = build_system_prompt(mode="technical")

    assert "/explodedview" not in commercial_prompt
    assert "/explodedview" in technical_prompt
    assert "/knolling" in technical_prompt
    assert "700 and 1,000 words" in technical_prompt
    assert "700 to 1,000 word count" in technical_prompt


def test_process_image_technical_mode_preserves_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    img_path = tmp_path / "turbine.jpg"
    from PIL import Image

    Image.new("RGB", (64, 64), color=(15, 30, 50)).save(img_path)

    long_prompt = " ".join(["Precision"] * 750)
    fake_payload = {
        "analysis": {"dominant_subject": "Turbine", "copy_space": "top_left"},
        "generated_prompts": [
            {
                "id": i + 1,
                "concept": f"Technical cutaway {i + 1}",
                "image_code": "/explodedview",
                "layout_type": "left_third_copy_space",
                "copy_space_zone": "left_40_percent",
                "target_buyer": "engineering_enterprise",
                "prompt": long_prompt,
                "estimated_word_count": 750,
            }
            for i in range(10)
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(fake_payload)}]}}]
    }

    with patch("src.analyzer.director.httpx.post", return_value=mock_resp):
        result = process_image(
            {"id": "tech_001", "title": "Exploded jet turbine CAD schematic", "local_path": str(img_path), "keywords": ["schematic", "cad"]},
            mode="auto",
        )

    assert result is not None
    assert result["source_id"] == "tech_001"
    assert len(result["generated_prompts"]) == 10
    assert result["analysis_metadata"]["director_mode"] == "image_codes_technical"
    assert all(p["status"] == "pending" for p in result["generated_prompts"])


@pytest.mark.parametrize(
    "b2b_template",
    [
        "saas_fintech_telemetry_ui",
        "isometric_architecture_flow",
        "kinetic_grid_background",
        "hud_data_overlay_loop",
    ],
)
def test_b2b_stock_templates_config_4k_and_render_muted(tmp_path, b2b_template):
    assert MOTION_TEMPLATES[b2b_template]["default_width"] == 3840
    assert MOTION_TEMPLATES[b2b_template]["default_height"] == 2160
    assert MOTION_TEMPLATES[b2b_template]["muted"] is True

    engine = HyperFramesMotionEngine()
    res = engine.render_b2b_stock_clip(
        template=b2b_template,
        title="B2B TELEMETRY LOOP",
        subtitle="ENTERPRISE METRICS",
        output_dir=tmp_path,
        duration_sec=1.0,
        resolution=(640, 360),
        fps=12,
        force_procedural=True,
    )
    assert res.success is True
    assert res.output_video_path is not None and res.output_video_path.exists()
    props = probe_video(res.output_video_path)
    assert props.has_audio is False
