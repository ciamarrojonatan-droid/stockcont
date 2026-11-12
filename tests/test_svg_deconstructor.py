import struct
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from src.dashboard import readers
from src.dashboard.app import app
from src.video.hyperframes_engine import MOTION_TEMPLATES, HyperFramesMotionEngine
from src.video.svg_deconstructor import RasterToAnimatedSVG


def _create_synthetic_emblem_png(path: Path, width: int = 400, height: int = 400) -> Path:
    """Create a deterministic high-contrast geometric emblem on a dark canvas."""
    img = Image.new("RGB", (width, height), (11, 21, 36))
    draw = ImageDraw.Draw(img)
    # Outer shield/ring
    draw.ellipse([70, 70, 330, 330], outline=(240, 245, 250), width=18)
    # Inner star / diamond chevron
    draw.polygon([(200, 95), (275, 200), (200, 305), (125, 200)], fill=(235, 242, 248))
    # Horizontal bar badge
    draw.rectangle([140, 185, 260, 215], fill=(56, 189, 248))
    img.save(path, format="PNG")
    return path


def _create_synthetic_beat_wav(path: Path, duration_sec: float = 2.0, sample_rate: int = 16000) -> Path:
    """Generate deterministic PCM WAV with clean 120 BPM drum-like impulses."""
    total_samples = int(duration_sec * sample_rate)
    beat_interval = int(0.5 * sample_rate)  # 120 BPM
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total_samples):
            pos_in_beat = i % beat_interval
            val = 22000 if pos_in_beat < 240 else 80
            frames.extend(struct.pack("<h", val))
        wf.writeframes(bytes(frames))
    return path


def test_raster_to_animated_svg_emblem_semantic_groups_and_html(tmp_path):
    emblem = _create_synthetic_emblem_png(tmp_path / "emblem.png")
    svg_out = tmp_path / "emblem.semantic.svg"
    html_out = tmp_path / "emblem.semantic.html"

    deconstructor = RasterToAnimatedSVG()
    res = deconstructor.deconstruct_raster(
        image_path=emblem,
        output_svg_path=svg_out,
        output_html_path=html_out,
        title="PROJECT BLACKBIRD",
        subtitle="VECTOR TELEMETRY RECONSTRUCTION",
        max_paths=48,
        duration_sec=3.5,
        seed=42,
    )

    assert res.success is True
    assert svg_out.exists()
    assert html_out.exists()
    assert res.semantic_groups == ["grid", "mark", "callouts", "wordmark"]
    assert res.path_count >= 1
    assert res.total_vertices >= 4
    assert res.faithful_landing_iou >= 0.45
    assert res.smoothness_gate_passed is True

    root = ET.fromstring(res.svg_markup)
    group_ids = [el.attrib.get("id") for el in root.iter() if el.tag.endswith("g") and el.attrib.get("id")]
    for expected_group in ("grid", "mark", "callouts", "wordmark"):
        assert expected_group in group_ids

    html_content = html_out.read_text(encoding="utf-8")
    assert "window.__timelines" in html_content
    assert "seek:" in html_content
    assert '<g id="mark"' in html_content


def test_raster_to_animated_svg_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        RasterToAnimatedSVG().deconstruct_raster(
            image_path=tmp_path / "nonexistent.png",
            output_svg_path=tmp_path / "out.svg",
        )


def test_hyperframes_deconstructed_emblem_vector_template(tmp_path):
    assert "deconstructed_emblem_vector" in MOTION_TEMPLATES
    emblem = _create_synthetic_emblem_png(tmp_path / "badge.png")
    engine = HyperFramesMotionEngine(output_dir=tmp_path)

    result = engine.render_motion_clip(
        template="deconstructed_emblem_vector",
        title="CLASSIFIED SEAL",
        subtitle="ARCHIVAL RECONSTRUCTION",
        duration_sec=1.5,
        fps=12,
        width=640,
        height=360,
        personality="cold_war_noir",
        seed=101,
        data={"image_path": str(emblem)},
        force_procedural=True,
        run_qa_gate=True,
    )

    assert result.success is True
    assert result.output_video_path is not None and Path(result.output_video_path).exists()
    assert result.html_path is not None and Path(result.html_path).exists()
    assert result.svg_path is not None and Path(result.svg_path).exists()
    html_text = Path(result.html_path).read_text(encoding="utf-8")
    assert '<g id="mark"' in html_text
    assert result.qa_report is not None
    assert result.qa_report["passed"] is True


def test_raster_to_animated_svg_invalid_hex_raises(tmp_path):
    emblem = _create_synthetic_emblem_png(tmp_path / "emblem_hex.png")
    with pytest.raises(ValueError, match="Invalid hex color"):
        RasterToAnimatedSVG().deconstruct_raster(
            image_path=emblem,
            bg_hex="#0B1524\" onclick=\"alert(1)",
        )


def test_sprint6_motion_qa_cadence_and_svg_endpoints(tmp_path, monkeypatch):
    monkeypatch.delenv("DASHBOARD_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(readers, "BASE_DIR", tmp_path)
    (tmp_path / "data" / "raw").mkdir(parents=True, exist_ok=True)
    client = TestClient(app)

    # 1. SVG Deconstruct endpoint (isolated inside workspace data/)
    emblem = _create_synthetic_emblem_png(tmp_path / "data" / "raw" / "api_emblem.png")
    resp_svg = client.post(
        "/api/v1/video/svg-deconstruct",
        json={
            "image_path": str(emblem),
            "title": "EAGLE PROTOCOL",
            "subtitle": "VECTOR EXTRACTION",
            "max_paths": 36,
            "duration_sec": 3.0,
        },
    )
    assert resp_svg.status_code == 200
    svg_data = resp_svg.json()
    assert svg_data["success"] is True
    assert svg_data["semantic_groups"] == ["grid", "mark", "callouts", "wordmark"]
    ET.fromstring(svg_data["svg_markup"])
    assert "data/staging/telemetry/" in (svg_data["svg_path"] or "")

    # 2. Motion Overlay with QA Gate + Seed + Personality
    resp_ov = client.post(
        "/api/v1/video/motion-overlay",
        json={
            "template": "blueprint_notebook",
            "title": "QA GATE TEST",
            "subtitle": None,
            "personality": "cold_war_noir",
            "seed": 777,
            "duration_sec": 2.0,
            "fps": 12,
            "width": 640,
            "height": 360,
            "run_qa_gate": True,
        },
    )
    assert resp_ov.status_code == 200
    ov_data = resp_ov.json()
    assert ov_data["success"] is True
    assert ov_data["seed"] == 777
    assert ov_data["personality"] == "cold_war_noir"
    assert ov_data["qa_report"] is not None
    assert ov_data["qa_report"]["passed"] is True

    # 3. Direct Motion QA audit endpoint
    video_file = Path(ov_data["output_video_path"])
    resp_qa = client.post(
        "/api/v1/video/motion-qa",
        json={
            "video_path": str(video_file),
            "personality": "cold_war_noir",
            "generate_sheet": True,
            "vision_critique": False,
        },
    )
    assert resp_qa.status_code == 200
    qa_data = resp_qa.json()
    assert qa_data["passed"] is True
    assert qa_data["contrast_ratio"] >= 4.5
    assert "telemetry" in (qa_data["contact_sheet_path"] or "")

    # 4. Cadence Blueprint endpoint with WAV beat sync
    wav_path = _create_synthetic_beat_wav(tmp_path / "data" / "raw" / "beats.wav", duration_sec=2.0)
    resp_cad = client.post(
        "/api/v1/video/cadence-blueprint",
        json={
            "video_path": str(video_file),
            "audio_path": str(wav_path),
            "snap_tolerance_sec": 0.20,
            "save_json": True,
        },
    )
    assert resp_cad.status_code == 200
    cad_data = resp_cad.json()
    assert cad_data["total_duration_sec"] > 0
    assert isinstance(cad_data["normalized_beats"], list)
    assert cad_data["blueprint_json_path"] is not None
    assert "telemetry" in cad_data["blueprint_json_path"]

    # 5. Path traversal and protected-directory security guards -> HTTP 400
    protected_src_file = tmp_path / "src" / "secret.png"
    protected_src_file.parent.mkdir(parents=True, exist_ok=True)
    _create_synthetic_emblem_png(protected_src_file)
    protected_resp = client.post("/api/v1/video/svg-deconstruct", json={"image_path": str(protected_src_file)})
    assert protected_resp.status_code == 400
    assert "forbidden" in protected_resp.json()["detail"].lower()

    outside_resp = client.post("/api/v1/video/svg-deconstruct", json={"image_path": "C:/Windows/System32/drivers/etc/hosts"})
    assert outside_resp.status_code == 400

    bad_svg = client.post("/api/v1/video/svg-deconstruct", json={"image_path": str(tmp_path / "data" / "missing.png")})
    assert bad_svg.status_code == 400

    bad_qa = client.post("/api/v1/video/motion-qa", json={"video_path": str(tmp_path / "data" / "missing.mp4")})
    assert bad_qa.status_code == 400

    bad_cad = client.post("/api/v1/video/cadence-blueprint", json={"video_path": str(tmp_path / "data" / "missing.mp4")})
    assert bad_cad.status_code == 400

    # 6. Token protection guard on new Sprint 6 routes
    monkeypatch.setenv("DASHBOARD_ACCESS_TOKEN", "sprint6-secret-token")
    unauth = client.post("/api/v1/video/svg-deconstruct", json={"image_path": str(emblem)})
    assert unauth.status_code == 401
    auth_ok = client.post(
        "/api/v1/video/svg-deconstruct",
        headers={"Authorization": "Bearer sprint6-secret-token"},
        json={"image_path": str(emblem)},
    )
    assert auth_ok.status_code == 200
