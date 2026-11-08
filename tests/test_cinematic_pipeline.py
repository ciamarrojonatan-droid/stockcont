"""
StockCont & DarkFactory — Cinematic Video Pipeline Test Suite
=============================================================
Testes automatizados cobrindo:
1. CinematicColorGrader (Emulação de película 35mm, LUTs, Film Grain e Letterbox)
2. CinematicPacingAnalyzer (MSL, Cuts Per Minute, Tension Score e Monotonia)
3. UniversalTimelineExporter (OpenTimelineIO para DaVinci Resolve)
4. TacticalGraphicsEngine (HUD Militar, Carimbo Desclassificado e Lower-Thirds)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.video.cinematic_color import (
    CinematicColorGrader,
    FilmLookProfile,
    LOOK_REGISTRY,
    LookSpecification,
)
from src.video.otio_exporter import (
    TimelineClipRef,
    TimelineMarker,
    UniversalTimelineExporter,
)
from src.video.pacing_analyzer import (
    CinematicPacingAnalyzer,
    PacingReport,
    ShotSegment,
)
from src.video.tactical_graphics import (
    LowerThirdData,
    TacticalGraphicsEngine,
)


class TestCinematicColorGrader:
    """Testes do motor de ciência de cor cinematográfica."""

    def test_all_profiles_registered_and_valid(self):
        grader = CinematicColorGrader()
        profiles = grader.list_profiles()
        assert len(profiles) == len(FilmLookProfile)
        
        for p in profiles:
            assert p["id"] in [e.value for e in FilmLookProfile]
            assert "name" in p
            assert "director_vibe" in p
            assert 0.0 <= p["recommended_grain"] <= 1.0

    def test_build_filter_graph_kodak_with_grain_and_letterbox(self):
        grader = CinematicColorGrader()
        fg = grader.build_filter_graph(
            profile=FilmLookProfile.KODAK_2383,
            film_grain=True,
            letterbox_239=True,
        )
        assert "eq=" in fg
        assert "contrast=" in fg
        assert "noise=c0s=" in fg
        assert "drawbox=y=0" in fg  # Anamorphic letterbox matte

    def test_build_filter_graph_oppenheimer_mono_no_colorbalance(self):
        grader = CinematicColorGrader()
        fg = grader.build_filter_graph(
            profile=FilmLookProfile.OPPENHEIMER_MONO,
            film_grain=True,
            letterbox_239=False,
        )
        assert "saturation=0.000" in fg
        assert "colorbalance=" not in fg  # P&B não deve ter balanceamento RGB

    def test_build_filter_graph_custom_lut(self, tmp_path):
        lut_file = tmp_path / "test_kodak.cube"
        lut_file.write_text("LUT_3D_SIZE 2\n0 0 0\n", encoding="utf-8")
        grader = CinematicColorGrader()
        fg = grader.build_filter_graph(
            profile=FilmLookProfile.KODAK_2383,
            custom_lut_path=lut_file,
            film_grain=False,
        )
        assert "lut3d=file=" in fg
        assert "eq=" not in fg

    def test_unknown_profile_fallback(self):
        grader = CinematicColorGrader()
        spec = grader.get_profile("non_existent_profile")
        assert spec.id == FilmLookProfile.KODAK_2383.value

    @patch("subprocess.run")
    def test_apply_grade_execution(self, mock_run, tmp_path):
        in_vid = tmp_path / "input.mp4"
        in_vid.write_bytes(b"dummy video")
        out_vid = tmp_path / "output.mp4"
        
        # Simula saída criada pelo subprocess
        def fake_run(cmd, **kwargs):
            out_vid.write_bytes(b"graded video")
            return MagicMock(returncode=0)

        mock_run.side_effect = fake_run
        grader = CinematicColorGrader()
        success = grader.apply_grade(
            input_path=in_vid,
            output_path=out_vid,
            profile=FilmLookProfile.BLEACH_BYPASS,
            film_grain=True,
        )
        assert success is True
        assert out_vid.exists()


class TestCinematicPacingAnalyzer:
    """Testes do analisador de ritmo de montagem."""

    def test_classify_energy_levels(self):
        analyzer = CinematicPacingAnalyzer()
        assert analyzer._classify_energy(1.2) == "climax"
        assert analyzer._classify_energy(2.5) == "high"
        assert analyzer._classify_energy(4.0) == "medium"
        assert analyzer._classify_energy(7.0) == "low"

    def test_build_pacing_report_dynamic(self, tmp_path):
        vid_file = tmp_path / "montage.mp4"
        vid_file.write_bytes(b"dummy")
        analyzer = CinematicPacingAnalyzer()

        # Simula 4 tomadas com durações variadas (ritmo cinematográfico)
        shots = [
            ShotSegment(1, 0.0, 3.5, 3.5, "medium"),
            ShotSegment(2, 3.5, 6.0, 2.5, "high"),
            ShotSegment(3, 6.0, 7.8, 1.8, "high"),
            ShotSegment(4, 7.8, 9.0, 1.2, "climax"),
        ]
        report = analyzer._build_pacing_report(vid_file, 9.0, shots)
        assert report.total_shots == 4
        assert report.total_duration_sec == 9.0
        assert report.mean_shot_length == 2.25
        assert report.cuts_per_minute == pytest.approx((4 / 9.0) * 60.0, abs=0.2)
        assert report.pacing_archetype in ["action_climax", "tactical_thriller"]
        assert report.tension_score >= 80

    def test_fallback_segmentation(self, tmp_path):
        vid_file = tmp_path / "single_shot.mp4"
        vid_file.write_bytes(b"dummy")
        analyzer = CinematicPacingAnalyzer()
        shots = analyzer._fallback_shot_segmentation(vid_file, 6.0)
        assert len(shots) == 1
        assert shots[0].duration_sec == 6.0


class TestUniversalTimelineExporter:
    """Testes de intercâmbio com OpenTimelineIO."""

    def test_build_timeline_json_structure(self):
        exporter = UniversalTimelineExporter(fps=24.0)
        clips = [
            TimelineClipRef(name="Shot_01", media_path="data/final/shot1.mp4", duration_sec=4.0),
            TimelineClipRef(name="Shot_02", media_path="data/final/shot2.mp4", duration_sec=3.0),
        ]
        narration = [
            TimelineClipRef(name="Voice_01", media_path="data/final/voice.wav", duration_sec=7.0),
        ]
        markers = [
            TimelineMarker(name="Chapter 1: Incident", timecode_sec=0.0, color="RED"),
        ]
        doc = exporter.build_timeline_json(
            timeline_name="Test_Dark_Doc",
            video_clips=clips,
            audio_narration_clips=narration,
            markers=markers,
        )

        assert doc["OTIO_SCHEMA"] == "Timeline.1"
        assert doc["name"] == "Test_Dark_Doc"
        assert len(doc["tracks"]["children"]) == 2  # Video + Audio
        assert doc["tracks"]["children"][0]["kind"] == "Video"
        assert doc["tracks"]["children"][1]["kind"] == "Audio"
        assert len(doc["markers"]) == 1
        assert doc["markers"][0]["name"] == "Chapter 1: Incident"

    def test_export_to_file(self, tmp_path):
        exporter = UniversalTimelineExporter(fps=24.0)
        out_file = tmp_path / "test_timeline.otio"
        clips = [
            TimelineClipRef(name="Clip_A", media_path="/media/clip_a.mp4", duration_sec=5.0),
        ]
        exported = exporter.export_to_file(
            output_path=out_file,
            timeline_name="DaVinci_Project",
            video_clips=clips,
        )
        assert exported.exists()
        content = json.loads(exported.read_text(encoding="utf-8"))
        assert "OTIO_SCHEMA" in content


class TestTacticalGraphicsEngine:
    """Testes do motor de overlays e gráficos táticos."""

    def test_create_declassified_stamp(self, tmp_path):
        engine = TacticalGraphicsEngine(default_width=1280, default_height=720)
        out_png = tmp_path / "stamp.png"
        res = engine.create_declassified_stamp_overlay(out_png)
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1280, 720)
            assert img.mode == "RGBA"

    def test_create_tactical_hud(self, tmp_path):
        engine = TacticalGraphicsEngine(default_width=1280, default_height=720)
        out_png = tmp_path / "hud.png"
        res = engine.create_tactical_hud_overlay(out_png)
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1280, 720)
            assert img.mode == "RGBA"

    def test_create_cinematic_lower_third(self, tmp_path):
        engine = TacticalGraphicsEngine(default_width=1280, default_height=720)
        out_png = tmp_path / "lower_third.png"
        data = LowerThirdData(
            title="Dr. J. Robert Oppenheimer",
            subtitle="Diretor do Laboratório de Los Alamos",
            coordinates="35.8817° N, 106.3031° W",
            date_timestamp="16 JUL 1945 - 05:29:45 MWT",
            classification="MANHATTAN PROJECT // TOP SECRET",
        )
        res = engine.create_cinematic_lower_third(out_png, data)
        assert res.exists()
        with Image.open(res) as img:
            assert img.size == (1280, 720)
            assert img.mode == "RGBA"
