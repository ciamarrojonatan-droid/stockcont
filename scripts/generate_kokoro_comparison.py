"""DarkFactory & StockCont — Kokoro-82M Voice Comparison Engine.

Generates and masters complete narration sets for both British narrator voices:
1. bm_george (Classic British Male — Authoritative, Somber, BBC/Nolan)
2. bm_lewis  (Articulate British Male — Intense, Dramatic, Cold War Tension)

Applies broadcast-grade documentary mastering:
- 60Hz High-pass filter
- 90Hz Warmth boost (+2.5dB)
- 350Hz Mud-clearing dip (-1.5dB)
- 3.5kHz Consonant clarity (+2.0dB)
- Broadcast Dynamic Compression & -14 LUFS Loudness Normalization
- Synchronized SRT Subtitles
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
import soundfile as sf
import imageio_ffmpeg
from kokoro_onnx import Kokoro

# Windows UTF-8 (ADR-01)
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "data" / "models" / "kokoro"
MODEL_PATH = str(MODEL_DIR / "kokoro-v0_19.onnx")
VOICES_PATH = str(MODEL_DIR / "voices.bin")

OUTPUT_BASE = BASE_DIR / "data" / "audio" / "kokoro_comparison"
DARKFACTORY_AUDIO = BASE_DIR / "darkfactory" / "data" / "audio"

SCRIPT_PATH = BASE_DIR / "darkfactory" / "data" / "scripts" / "pilot_soviet_glitch.json"

FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()


def get_audio_duration(file_path: Path) -> float:
    """Gets audio duration in seconds."""
    info = sf.info(str(file_path))
    return float(info.duration)


def format_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(scenes: list[dict], durations: list[float], output_srt: Path):
    """Generates broadcast documentary SRT subtitles aligned to scene pauses."""
    srt_entries = []
    current_time = 0.0
    counter = 1

    for scene, dur in zip(scenes, durations):
        text = scene["audio_text"]
        clauses = []
        for sentence in text.replace("...", ".").split(". "):
            sentence = sentence.strip()
            if not sentence:
                continue
            if not sentence.endswith("."):
                sentence += "."
            if len(sentence) > 60 and ", " in sentence:
                parts = sentence.split(", ", 1)
                clauses.append(parts[0].strip() + ",")
                clauses.append(parts[1].strip())
            else:
                clauses.append(sentence)

        total_chars = sum(len(c) for c in clauses)
        scene_start = current_time

        for clause in clauses:
            portion = len(clause) / max(total_chars, 1)
            clause_dur = dur * portion
            start_str = format_srt_time(current_time)
            end_str = format_srt_time(current_time + clause_dur - 0.08)

            srt_entries.append(f"{counter}\n{start_str} --> {end_str}\n{clause}\n")
            current_time += clause_dur
            counter += 1

        current_time = scene_start + dur

    full_srt = "\n".join(srt_entries)
    with open(output_srt, "w", encoding="utf-8") as f:
        f.write(full_srt)
    return full_srt


def master_audio(input_wav: Path, output_file: Path):
    """Applies high-end documentary mastering filter chain."""
    filter_chain = (
        "highpass=f=60,"
        "equalizer=f=90:width_type=q:w=1.0:g=2.5,"
        "equalizer=f=350:width_type=q:w=1.5:g=-1.5,"
        "highshelf=f=3500:width_type=q:w=1.0:g=2.0,"
        "acompressor=threshold=-18dB:ratio=3:attack=15:release=120:makeup=2dB,"
        "loudnorm=I=-14:TP=-1.0:LRA=7"
    )

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", str(input_wav),
        "-af", filter_chain,
    ]
    if output_file.suffix.lower() == ".mp3":
        cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k", "-ar", "44100"])
    else:
        cmd.extend(["-c:a", "pcm_s24le", "-ar", "48000"])
    cmd.append(str(output_file))

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg mastering error: {res.stderr}")


def run_comparison():
    print("=" * 68)
    print("  DARKFACTORY — KOKORO-82M LOCAL NARRATOR BENCHMARK (GEORGE vs LEWIS)")
    print("=" * 68)

    if not SCRIPT_PATH.exists():
        print(f"[ERRO] Script não encontrado em {SCRIPT_PATH}")
        return False

    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    scenes = script_data.get("scenes", [])
    print(f"\n[OK] Script carregado: '{script_data.get('title')}' ({len(scenes)} cenas)")

    print("\n[OK] Inicializando motor Kokoro-82M ONNX local...")
    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)

    voices = ["bm_george", "bm_lewis"]
    results = {}

    for voice in voices:
        print("\n" + "#" * 60)
        print(f"  PROCESSANDO VOZ: {voice.upper()} (Estilo British Documentary / Nolan)")
        print("#" * 60)

        voice_dir = OUTPUT_BASE / voice
        raw_dir = voice_dir / "raw"
        mastered_dir = voice_dir / "mastered"
        subs_dir = voice_dir / "subtitles"

        raw_dir.mkdir(parents=True, exist_ok=True)
        mastered_dir.mkdir(parents=True, exist_ok=True)
        subs_dir.mkdir(parents=True, exist_ok=True)

        scene_durations = []
        scene_files = []

        # 1. Gerar cenas individuais
        for scene in scenes:
            s_id = scene["scene_id"]
            text = scene["audio_text"]
            print(f"  -> Sintetizando Cena {s_id} com {voice}...")

            samples, sr = kokoro.create(text, voice=voice, speed=0.98, lang="en-gb")

            raw_scene_wav = raw_dir / f"scene_{s_id}_raw.wav"
            sf.write(str(raw_scene_wav), samples, sr)

            mastered_scene_wav = mastered_dir / f"scene_{s_id}_mastered.wav"
            master_audio(raw_scene_wav, mastered_scene_wav)

            dur = get_audio_duration(mastered_scene_wav)
            scene_durations.append(dur)
            scene_files.append(mastered_scene_wav)
            print(f"     [OK] Cena {s_id} masterizada: {dur:.2f}s | {mastered_scene_wav.name}")

        # 2. Gerar o áudio contínuo do piloto (Full Intro)
        full_text = " ".join(s["audio_text"] for s in scenes)
        print(f"\n  -> Sintetizando Narração Completa do Piloto ({voice})...")
        full_samples, full_sr = kokoro.create(full_text, voice=voice, speed=0.98, lang="en-gb")

        raw_full_wav = raw_dir / f"pilot_full_{voice}_raw.wav"
        sf.write(str(raw_full_wav), full_samples, full_sr)

        mastered_full_wav = mastered_dir / f"pilot_full_{voice}_mastered.wav"
        mastered_full_mp3 = mastered_dir / f"pilot_full_{voice}_mastered.mp3"

        master_audio(raw_full_wav, mastered_full_wav)
        master_audio(raw_full_wav, mastered_full_mp3)

        full_dur = get_audio_duration(mastered_full_wav)

        # 3. Gerar legendas SRT sincronizadas
        srt_file = subs_dir / f"pilot_full_{voice}.srt"
        generate_srt(scenes, scene_durations, srt_file)

        # 4. Copiar para o DarkFactory oficial
        DARKFACTORY_AUDIO.mkdir(parents=True, exist_ok=True)
        df_copy_mp3 = DARKFACTORY_AUDIO / f"pilot_{voice}_mastered.mp3"
        df_copy_wav = DARKFACTORY_AUDIO / f"pilot_{voice}_mastered.wav"
        subprocess.run(["cmd", "/c", "copy", str(mastered_full_mp3), str(df_copy_mp3)], stdout=subprocess.DEVNULL)
        subprocess.run(["cmd", "/c", "copy", str(mastered_full_wav), str(df_copy_wav)], stdout=subprocess.DEVNULL)

        results[voice] = {
            "duration": full_dur,
            "mp3_path": str(mastered_full_mp3),
            "wav_path": str(mastered_full_wav),
            "srt_path": str(srt_file),
            "size_kb": round(mastered_full_mp3.stat().st_size / 1024, 1),
            "scene_durations": scene_durations,
        }
        print(f"  [CONCLUÍDO {voice.upper()}] Duração: {full_dur:.2f}s | MP3: {mastered_full_mp3.name} ({results[voice]['size_kb']} KB)")

    print("\n" + "=" * 68)
    print("  RELATÓRIO COMPARATIVO DE VOZES KOKORO-82M")
    print("=" * 68)
    for v, data in results.items():
        print(f"\n* Voz: {v}")
        print(f"  - Duração Masterizada: {data['duration']:.2f}s")
        print(f"  - Master MP3 320k: {data['mp3_path']}")
        print(f"  - Master WAV 24-bit 48kHz: {data['wav_path']}")
        print(f"  - Legendas SRT: {data['srt_path']}")

    return results


if __name__ == "__main__":
    run_comparison()
