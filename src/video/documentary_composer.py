"""StockCont & DarkFactory — Word-Timed Documentary World Composer (Golden Slice).

Connects PublicDomainResearchEngine + VoiceAligner + MapAnimator + TacticalGraphicsEngine +
UniversalTimelineExporter to assemble a synchronized documentary episode:
- Grounds facts & public-domain visual assets
- Aligns transcript word-by-word against narration audio
- Renders animated theater map + Ken Burns archival image shots
- Triggers DECLASSIFIED stamps / lower-thirds at exact spoken keyword timestamps
- Exports playable H.264 MP4 + OpenTimelineIO (.otio) + SRT + atomic JSON manifest.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image

from src.video.ffmpeg_processor import get_ffmpeg_binary, probe_video
from src.video.map_animator import MapAnimator, MapPin, MapRoute
from src.video.otio_exporter import (
    TimelineClipRef,
    TimelineMarker,
    UniversalTimelineExporter,
)
from src.video.research_engine import DossierFactPack, PublicDomainResearchEngine
from src.video.tactical_graphics import LowerThirdData, TacticalGraphicsEngine
from src.video.voice_aligner import VoiceAligner, WordTriggerEvent

# Reconfigure stdout/stderr to UTF-8 on Windows consoles (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger("stockcont.video.documentary_composer")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_EPISODES_DIR = BASE_DIR / "data" / "final" / "episodes"


def _slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", (value or "episode").strip().lower()).strip("_")[:60] or "episode"


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
class DocumentaryCompositionResult:
    """Output artifact bundle for a synchronized documentary episode."""

    success: bool
    topic: str
    slug: str
    duration_sec: float
    master_video_path: Optional[str] = None
    map_video_path: Optional[str] = None
    otio_path: Optional[str] = None
    subtitles_path: Optional[str] = None
    manifest_path: Optional[str] = None
    word_triggers: List[Dict[str, Any]] = field(default_factory=list)
    facts_count: int = 0
    pd_assets_count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DocumentaryComposer:
    """Assembles word-timed documentary episodes from PD dossiers and vector maps."""

    def __init__(
        self,
        output_dir: Optional[Path | str] = None,
        research_engine: Optional[PublicDomainResearchEngine] = None,
        voice_aligner: Optional[VoiceAligner] = None,
        map_animator: Optional[MapAnimator] = None,
        graphics_engine: Optional[TacticalGraphicsEngine] = None,
        otio_exporter: Optional[UniversalTimelineExporter] = None,
    ) -> None:
        self.output_dir = Path(output_dir).resolve() if output_dir else DEFAULT_EPISODES_DIR.resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.research_engine = research_engine or PublicDomainResearchEngine()
        self.voice_aligner = voice_aligner or VoiceAligner()
        self.map_animator = map_animator or MapAnimator(output_dir=self.output_dir / "maps")
        self.graphics_engine = graphics_engine or TacticalGraphicsEngine()
        self.otio_exporter = otio_exporter or UniversalTimelineExporter(fps=24.0)

    @staticmethod
    def _build_archival_ken_burns_clip(
        image_paths: Sequence[Path],
        output_video: Path,
        duration_sec: float,
        width: int,
        height: int,
        fps: int,
    ) -> Path:
        """Render smooth slow-push archival motion over local PD images or dark slate."""
        output_video.parent.mkdir(parents=True, exist_ok=True)
        tmp_out = output_video.with_name(f"{output_video.stem}.tmp.{os.getpid()}{output_video.suffix}")

        loaded: List[np.ndarray] = []
        for p in image_paths:
            if p.is_file():
                try:
                    with Image.open(p) as im:
                        rgb = im.convert("RGB")
                        arr = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
                        loaded.append(arr)
                except Exception as exc:
                    logger.warning("Skipping unreadable archival image %s: %s", p.name, exc)

        if not loaded:
            base = np.full((height, width, 3), (14, 20, 32), dtype=np.uint8)
            cv2.putText(base, "CLASSIFIED ARCHIVE DOSSIER", (64, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180, 200, 225), 2, cv2.LINE_AA)
            loaded.append(base)

        total_frames = max(1, int(round(duration_sec * fps)))
        cmd = [
            get_ffmpeg_binary(),
            "-y",
            "-v", "error",
            "-nostats",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "bgr24",
            "-r", str(fps),
            "-i", "-",
            "-an",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            tmp_out.as_posix(),
        ]
        proc: Optional[subprocess.Popen[bytes]] = None
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            assert proc.stdin is not None
            for idx in range(total_frames):
                img_idx = min(len(loaded) - 1, int((idx / max(1, total_frames)) * len(loaded)))
                src = loaded[img_idx]
                prog = idx / max(1, total_frames - 1)
                scale = 1.0 + 0.08 * prog
                sh, sw = src.shape[:2]
                resized = cv2.resize(src, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
                rh, rw = resized.shape[:2]
                x0 = max(0, (rw - width) // 2)
                y0 = max(0, (rh - height) // 2)
                crop = resized[y0 : y0 + height, x0 : x0 + width]
                if crop.shape[:2] != (height, width):
                    crop = cv2.resize(crop, (width, height))
                proc.stdin.write(crop.tobytes())
            proc.stdin.close()
            proc.stdin = None
            err = proc.stderr.read() if proc.stderr else b""
            rc = proc.wait(timeout=120)
            if rc != 0:
                tmp_out.unlink(missing_ok=True)
                raise RuntimeError(f"FFmpeg archival Ken Burns failed: {err.decode('utf-8', errors='replace')[:240]}")
            tmp_out.replace(output_video)
            return output_video
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

    def _assemble_master_av(
        self,
        archive_clip: Path,
        map_clip: Optional[Path],
        narration_audio: Path,
        stamp_png: Path,
        triggers: Sequence[WordTriggerEvent],
        output_video: Path,
        duration_sec: float,
        width: int,
        height: int,
        fps: int,
    ) -> Path:
        """Concatenate visual beds, apply spoken-word stamp overlay, and mux voiceover audio."""
        output_video.parent.mkdir(parents=True, exist_ok=True)
        tmp_out = output_video.with_name(f"{output_video.stem}.tmp.{os.getpid()}{output_video.suffix}")

        stamp_start = triggers[0].timestamp_sec if triggers else min(0.5, duration_sec * 0.2)
        stamp_end = min(duration_sec, stamp_start + 1.8)

        if map_clip and map_clip.is_file():
            half = max(0.5, round(duration_sec * 0.5, 3))
            filter_complex = (
                f"[0:v]trim=0:{half:.3f},setpts=PTS-STARTPTS,scale={width}:{height},fps={fps}[v_arch];"
                f"[1:v]trim=0:{max(0.5, duration_sec - half):.3f},setpts=PTS-STARTPTS,scale={width}:{height},fps={fps}[v_map];"
                f"[v_arch][v_map]concat=n=2:v=1:a=0[v_base];"
                f"[2:v]scale={width}:{height}[ovr];"
                f"[v_base][ovr]overlay=0:0:enable='between(t,{stamp_start:.3f},{stamp_end:.3f})'[v_out]"
            )
            inputs = ["-i", archive_clip.as_posix(), "-i", map_clip.as_posix(), "-i", stamp_png.as_posix(), "-i", narration_audio.as_posix()]
            audio_map = "3:a"
        else:
            filter_complex = (
                f"[0:v]scale={width}:{height},fps={fps}[v_base];"
                f"[1:v]scale={width}:{height}[ovr];"
                f"[v_base][ovr]overlay=0:0:enable='between(t,{stamp_start:.3f},{stamp_end:.3f})'[v_out]"
            )
            inputs = ["-i", archive_clip.as_posix(), "-i", stamp_png.as_posix(), "-i", narration_audio.as_posix()]
            audio_map = "2:a"

        cmd = [
            get_ffmpeg_binary(),
            "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", audio_map,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            tmp_out.as_posix(),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180.0)
        if res.returncode != 0:
            tmp_out.unlink(missing_ok=True)
            err = res.stderr.decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"FFmpeg documentary master assembly failed: {err}")
        tmp_out.replace(output_video)
        return output_video

    def compose_episode(
        self,
        topic: str,
        script: str,
        narration_audio_path: Path | str,
        theater: str = "europe_cold_war",
        trigger_keywords: Optional[Sequence[str]] = None,
        width: int = 1280,
        height: int = 720,
        fps: int = 24,
    ) -> DocumentaryCompositionResult:
        """Run end-to-end synchronized documentary assembly for a topic and narration track."""
        slug = _slugify(topic)
        ep_dir = self.output_dir / slug
        ep_dir.mkdir(parents=True, exist_ok=True)

        audio_path = Path(narration_audio_path).resolve()
        if not audio_path.is_file():
            raise FileNotFoundError(f"Narration audio not found: {audio_path}")

        dossier: DossierFactPack = self.research_engine.build_dossier(topic)
        alignment = self.voice_aligner.align_transcript(
            audio_path=audio_path,
            transcript=script,
            trigger_keywords=trigger_keywords,
            save_srt=True,
            srt_output_path=ep_dir / f"{slug}.srt",
        )
        duration = max(1.0, alignment.duration_sec)

        # Render tactical vector map bed (second half of segment)
        map_res = self.map_animator.render_map_animation(
            title=topic.upper()[:38],
            subtitle=f"{len(dossier.facts)} VERIFIED FACTS // PD ARCHIVE",
            theater=theater,
            pins=[
                MapPin(label=topic.upper()[:18], lat=54.91, lon=37.41, timestamp_sec=0.25),
            ],
            routes=[
                MapRoute(origin_lat=54.91, origin_lon=37.41, dest_lat=52.52, dest_lon=13.40, start_sec=0.4, duration_sec=max(0.8, duration * 0.35)),
            ],
            duration_sec=max(1.0, duration * 0.5),
            width=width,
            height=height,
            fps=fps,
            output_path=ep_dir / f"{slug}_map.mp4",
        )

        # Render archival Ken Burns video from PD local images (first half)
        local_imgs: List[Path] = []
        for asset in dossier.media_assets:
            candidate = getattr(asset, "local_path", None) or asset.url
            if candidate and not str(candidate).startswith(("http://", "https://")):
                p = Path(candidate)
                if p.is_file():
                    local_imgs.append(p)
        archive_clip = self._build_archival_ken_burns_clip(
            image_paths=local_imgs,
            output_video=ep_dir / f"{slug}_archive.mp4",
            duration_sec=max(1.0, duration * 0.5),
            width=width,
            height=height,
            fps=fps,
        )

        # Generate spoken-word triggered tactical stamp PNG
        self.graphics_engine.width = width
        self.graphics_engine.height = height
        stamp_png = self.graphics_engine.create_declassified_stamp_overlay(
            output_png_path=ep_dir / f"{slug}_stamp.png",
            stamp_text="TOP SECRET // DECLASSIFIED",
            sub_text=f"ARCHIVE // {topic.upper()[:28]}",
        )
        lower_third_png = self.graphics_engine.create_cinematic_lower_third(
            output_png_path=ep_dir / f"{slug}_lower_third.png",
            data=LowerThirdData(
                title=topic.upper()[:36],
                subtitle=f"PD VERIFIED ({len(dossier.facts)} FACTS)",
                coordinates="54.9158° N, 37.4116° E",
                date_timestamp="ARCHIVAL TIMELINE",
                classification="PUBLIC DOMAIN / CC0",
            ),
        )

        master_mp4 = self._assemble_master_av(
            archive_clip=archive_clip,
            map_clip=Path(map_res.video_path) if map_res.video_path else None,
            narration_audio=audio_path,
            stamp_png=stamp_png,
            triggers=alignment.word_triggers,
            output_video=ep_dir / f"{slug}_master.mp4",
            duration_sec=duration,
            width=width,
            height=height,
            fps=fps,
        )
        probe_video(master_mp4)

        # Export OpenTimelineIO timeline linking V1, V2, A1 and spoken-word markers
        half = round(duration * 0.5, 3)
        v1_clips = [
            TimelineClipRef(name="Archive_KenBurns", media_path=archive_clip.as_posix(), duration_sec=half, start_offset_sec=0.0, track_type="video", track_index=1),
            TimelineClipRef(name="Theater_VectorMap", media_path=map_res.video_path or archive_clip.as_posix(), duration_sec=round(duration - half, 3), start_offset_sec=0.0, track_type="video", track_index=1),
        ]
        v2_clips = [
            TimelineClipRef(name="Declassified_Stamp", media_path=stamp_png.as_posix(), duration_sec=min(2.0, duration), start_offset_sec=alignment.word_triggers[0].timestamp_sec if alignment.word_triggers else 0.3, track_type="video", track_index=2),
            TimelineClipRef(name="LowerThird_Dossier", media_path=lower_third_png.as_posix(), duration_sec=min(2.5, duration), start_offset_sec=0.1, track_type="video", track_index=2),
        ]
        a1_clips = [
            TimelineClipRef(name="Voiceover_Master", media_path=audio_path.as_posix(), duration_sec=duration, start_offset_sec=0.0, track_type="audio", track_index=1),
        ]
        markers = [
            TimelineMarker(
                name=f"CUE_{tr.action_type.upper()}_{tr.keyword.upper()}",
                timecode_sec=tr.timestamp_sec,
                color="RED" if tr.action_type == "stamp" else "BLUE",
                comment=f"Matched spoken word '{tr.matched_word}' at {tr.timestamp_sec:.3f}s",
            )
            for tr in alignment.word_triggers
        ]
        if not markers:
            markers.append(TimelineMarker(name="CUE_OPENING", timecode_sec=0.0, color="GREEN", comment="Episode start"))

        self.otio_exporter.fps = float(fps)
        otio_doc = self.otio_exporter.build_timeline_json(
            timeline_name=f"DarkFactory_{slug}",
            video_clips=v1_clips,
            audio_narration_clips=a1_clips,
            overlay_clips=v2_clips,
            markers=markers,
        )
        otio_path = ep_dir / f"{slug}.otio"
        _atomic_write_json(otio_path, otio_doc)

        result = DocumentaryCompositionResult(
            success=True,
            topic=topic,
            slug=slug,
            duration_sec=duration,
            master_video_path=master_mp4.as_posix(),
            map_video_path=map_res.video_path,
            otio_path=otio_path.as_posix(),
            subtitles_path=alignment.subtitles_path,
            manifest_path=(ep_dir / f"{slug}_manifest.json").as_posix(),
            word_triggers=[tr.to_dict() for tr in alignment.word_triggers],
            facts_count=len(dossier.facts),
            pd_assets_count=len(dossier.media_assets),
        )
        _atomic_write_json(ep_dir / f"{slug}_manifest.json", result.to_dict())
        return result
