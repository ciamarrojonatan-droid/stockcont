"""
StockCont & DarkFactory — Cinematic Color Science & Film Emulation Engine
========================================================================
Aplica tratamentos de cor cinematográficos (Hollywood Grade) a vídeos brutos
de IA (Google Veo 2, MiniMax H3, ComfyUI) usando perfis de película 35mm
(Kodak 2383, Fuji Eterna, Bleach Bypass, Oppenheimer Monochrome, Cold War Noir),
simulação de granulação analógica (Film Grain) e matte anamórfico 2.39:1 (CinemaScope).
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("stockcont.video.cinematic_color")


class FilmLookProfile(str, Enum):
    """Perfis cinemáticos de emulação de película e tonalidade de diretor."""
    KODAK_2383 = "kodak_2383"
    FUJI_ETERNA = "fuji_eterna"
    BLEACH_BYPASS = "bleach_bypass"
    OPPENHEIMER_MONO = "oppenheimer_mono"
    COLD_WAR_NOIR = "cold_war_noir"
    CYBER_TACTICAL = "cyber_tactical"


@dataclass(frozen=True)
class LookSpecification:
    """Especificação técnica e estética de cada perfil cinemático."""
    id: str
    name: str
    director_vibe: str
    description: str
    gamma: float
    contrast: float
    saturation: float
    brightness: float
    color_balance_r: float
    color_balance_g: float
    color_balance_b: float
    recommended_grain: float  # 0.0 a 1.0


LOOK_REGISTRY: Dict[FilmLookProfile, LookSpecification] = {
    FilmLookProfile.KODAK_2383: LookSpecification(
        id="kodak_2383",
        name="Kodak Vision3 / 2383 Print Look",
        director_vibe="Christopher Nolan (Oppenheimer, Interstellar, Inception)",
        description="Emulação da lendária película Kodak 2383: sombras cyan/teal profundas, realces âmbar dourados quentes e curva S elegante.",
        gamma=0.96,
        contrast=1.12,
        saturation=1.08,
        brightness=-0.02,
        color_balance_r=0.06,
        color_balance_g=-0.02,
        color_balance_b=-0.04,
        recommended_grain=0.14,
    ),
    FilmLookProfile.FUJI_ETERNA: LookSpecification(
        id="fuji_eterna",
        name="Fuji Eterna 500T Muted Mystery",
        director_vibe="David Fincher (Zodiac, Mindhunter, The Girl with the Dragon Tattoo)",
        description="Baixo contraste harmônico, tons de pele pastéis orgânicos, verdes e azuis dessaturados e atmosfera taciturna de suspense investigativo.",
        gamma=1.04,
        contrast=0.98,
        saturation=0.82,
        brightness=0.01,
        color_balance_r=-0.03,
        color_balance_g=0.04,
        color_balance_b=-0.02,
        recommended_grain=0.10,
    ),
    FilmLookProfile.BLEACH_BYPASS: LookSpecification(
        id="bleach_bypass",
        name="Bleach Bypass (Silver Retention)",
        director_vibe="Janusz Kamiński / Steven Spielberg (Saving Private Ryan, Minority Report)",
        description="Retenção de prata na película: contraste extremo, sombras esmagadas sem ruído digital, saturação reduzida e textura metálica cortante.",
        gamma=0.92,
        contrast=1.35,
        saturation=0.62,
        brightness=-0.04,
        color_balance_r=0.02,
        color_balance_g=0.02,
        color_balance_b=0.02,
        recommended_grain=0.22,
    ),
    FilmLookProfile.OPPENHEIMER_MONO: LookSpecification(
        id="oppenheimer_mono",
        name="Oppenheimer Silver Gelatin Monochrome",
        director_vibe="Hoyte van Hoytema / Christopher Nolan (Oppenheimer Black & White Sections)",
        description="Preto e branco cinemático emulando película Kodak Double-X 65mm: separação tonal refinada, pretos aveludados e realces puros sem clipping.",
        gamma=1.00,
        contrast=1.24,
        saturation=0.00,  # 100% Dessaturado P&B
        brightness=0.00,
        color_balance_r=0.00,
        color_balance_g=0.00,
        color_balance_b=0.00,
        recommended_grain=0.20,
    ),
    FilmLookProfile.COLD_WAR_NOIR: LookSpecification(
        id="cold_war_noir",
        name="Cold War Dossier Noir",
        director_vibe="Tomas Alfredson (Tinker Tailor Soldier Spy) & DarkFactory Original",
        description="Estética de documentos desclassificados da Guerra Fria: tons de tungstênio, iluminação verde-lodo de bunker subterrâneo e granulação densa.",
        gamma=0.98,
        contrast=1.18,
        saturation=0.74,
        brightness=-0.03,
        color_balance_r=-0.04,
        color_balance_g=0.05,
        color_balance_b=-0.05,
        recommended_grain=0.25,
    ),
    FilmLookProfile.CYBER_TACTICAL: LookSpecification(
        id="cyber_tactical",
        name="Tactical Cyber Warfare Amber/Cyan",
        director_vibe="Denis Villeneuve (Sicario / Blade Runner 2049 Night Scenes)",
        description="Separação tática com pretos cirúrgicos, sombras escuras e realces em âmbar de fósforo e ciano cibernético de alta tensão.",
        gamma=0.95,
        contrast=1.28,
        saturation=1.15,
        brightness=-0.03,
        color_balance_r=0.04,
        color_balance_g=0.01,
        color_balance_b=0.06,
        recommended_grain=0.08,
    ),
}


class CinematicColorGrader:
    """Motor de color grading e emulação de película via FFmpeg."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg"):
        self.ffmpeg_bin = ffmpeg_bin

    def get_profile(self, profile: str | FilmLookProfile) -> LookSpecification:
        """Obtém a especificação técnica de um perfil."""
        if isinstance(profile, FilmLookProfile):
            return LOOK_REGISTRY[profile]
        
        try:
            return LOOK_REGISTRY[FilmLookProfile(profile.lower())]
        except (ValueError, KeyError):
            logger.warning(f"Perfil '{profile}' desconhecido. Utilizando 'kodak_2383' como fallback.")
            return LOOK_REGISTRY[FilmLookProfile.KODAK_2383]

    def list_profiles(self) -> List[Dict[str, Any]]:
        """Retorna metadados de todos os perfis disponíveis."""
        return [
            {
                "id": spec.id,
                "name": spec.name,
                "director_vibe": spec.director_vibe,
                "description": spec.description,
                "recommended_grain": spec.recommended_grain,
            }
            for spec in LOOK_REGISTRY.values()
        ]

    def build_filter_graph(
        self,
        profile: str | FilmLookProfile,
        film_grain: bool = True,
        grain_strength: Optional[float] = None,
        letterbox_239: bool = False,
        custom_lut_path: Optional[str | Path] = None,
    ) -> str:
        """
        Gera a string de filtros complexos (filter_complex) do FFmpeg.
        Combina curva paramétrica, balanceamento de cor, grão de película e matte 2.39:1.
        """
        spec = self.get_profile(profile)
        filters: List[str] = []

        # 1. Se houver LUT 3D externa fornecida (.cube), aplica prioritariamente
        if custom_lut_path and Path(custom_lut_path).exists():
            lut_str = str(Path(custom_lut_path).as_posix())
            filters.append(f"lut3d=file='{lut_str}'")
        else:
            # 2. Emulação Procedural de Película de Alta Precisão (Sem dependência de arquivo externo)
            eq_filter = (
                f"eq=contrast={spec.contrast:.3f}:"
                f"brightness={spec.brightness:.3f}:"
                f"saturation={spec.saturation:.3f}:"
                f"gamma={spec.gamma:.3f}"
            )
            filters.append(eq_filter)

            # Balanceamento de canais RGB se não for P&B total
            if spec.saturation > 0.0 and (spec.color_balance_r != 0 or spec.color_balance_g != 0 or spec.color_balance_b != 0):
                cb_filter = (
                    f"colorbalance=rs={spec.color_balance_r:.2f}:"
                    f"gs={spec.color_balance_g:.2f}:"
                    f"bs={spec.color_balance_b:.2f}:"
                    f"rh={spec.color_balance_r * 0.8:.2f}:"
                    f"gh={spec.color_balance_g * 0.8:.2f}:"
                    f"bh={spec.color_balance_b * 0.8:.2f}"
                )
                filters.append(cb_filter)

        # 3. Granulação de Película 35mm Realista (Noise temporal orgânico)
        if film_grain:
            strength = grain_strength if grain_strength is not None else spec.recommended_grain
            # Mapeia 0.0 - 1.0 para intensidade de ruído do FFmpeg (5 a 30)
            noise_val = int(max(4, min(35, strength * 45)))
            # c0s: intensidade luma, c0f: temporal noise (grão vivo não estático)
            grain_filter = f"noise=c0s={noise_val}:c0f=t+u"
            filters.append(grain_filter)

        # 4. Matte Anamórfico CinemaScope 2.39:1 (Letterboxing cinemático preto em 16:9)
        if letterbox_239:
            # Em 1920x1080 (16:9), altura 2.39 é ~804px. Faixas superior/inferior = ~138px cada.
            # Em 3840x2160 (16:9), altura 2.39 é ~1608px. Faixas = ~276px cada.
            # Fórmula universal FFmpeg: desenha duas faixas pretas proporcionalmente
            letterbox_filter = (
                "drawbox=y=0:h=ih*0.128:color=black@1.0:t=fill,"
                "drawbox=y=ih-ih*0.128:h=ih*0.128:color=black@1.0:t=fill"
            )
            filters.append(letterbox_filter)

        return ",".join(filters)

    def apply_grade(
        self,
        input_path: str | Path,
        output_path: str | Path,
        profile: str | FilmLookProfile = FilmLookProfile.KODAK_2383,
        film_grain: bool = True,
        grain_strength: Optional[float] = None,
        letterbox_239: bool = False,
        custom_lut_path: Optional[str | Path] = None,
    ) -> bool:
        """
        Executa a aplicação do color grading no arquivo de vídeo com aceleração libx264.
        """
        in_file = Path(input_path)
        out_file = Path(output_path)

        if not in_file.exists():
            logger.error(f"Arquivo de entrada não encontrado: {in_file}")
            return False

        out_file.parent.mkdir(parents=True, exist_ok=True)
        filter_str = self.build_filter_graph(
            profile=profile,
            film_grain=film_grain,
            grain_strength=grain_strength,
            letterbox_239=letterbox_239,
            custom_lut_path=custom_lut_path,
        )

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i", str(in_file),
            "-vf", filter_str,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "17",  # Quase sem perda visual (Mastering Grade)
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",  # Preserva áudio masterizado
            str(out_file),
        ]

        logger.info(f"Aplicando Look '{profile}' no vídeo: {in_file.name} ➔ {out_file.name}")
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return out_file.exists() and out_file.stat().st_size > 0
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao aplicar grading FFmpeg: {e.stderr}")
            return False
