"""
StockCont & DarkFactory — Tactical Motion Graphics & Cinematic Overlays Engine
==============================================================================
Gera grafismos táticos, documentos desclassificados animados e interfaces
de telemetria analógica para documentários dark e filmes de espionagem/militar:
- Carimbo 'TOP SECRET // DECLASSIFIED // LEVEL 5'
- HUD de Radar Tático com mira militar e coordenadas geográficas
- Lower-Third Cinemático em tipografia militar monoespaçada com cursor pulsante
- Faixas de Redação Confidencial ('Black Bar Redaction')
- Máscara Anamórfica 2.39:1 (CinemaScope Matte)
Compatível com Pillow (render transparente RGBA), FFmpeg filters e Movis composition.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("stockcont.video.tactical_graphics")


@dataclass
class LowerThirdData:
    """Dados para identificação de personagens ou locais na narrativa."""
    title: str               # Ex: "GEN. STANISLAV PETROV"
    subtitle: str            # Ex: "Comandante Operacional // Bunker Serpukhov-15"
    coordinates: str         # Ex: "54.9158° N, 37.4116° E"
    date_timestamp: str      # Ex: "26 SET 1983 - 00:23:40 UTC"
    classification: str      # Ex: "DECLASSIFIED BY US/SOV ARCHIVE"


class TacticalGraphicsEngine:
    """Motor de geração de motion graphics e elementos táticos em vídeo."""

    def __init__(self, default_width: int = 1920, default_height: int = 1080):
        self.width = default_width
        self.height = default_height

    def create_declassified_stamp_overlay(
        self,
        output_png_path: str | Path,
        stamp_text: str = "TOP SECRET // DECLASSIFIED",
        sub_text: str = "ARCHIVE ORDER NO. 49-B // EYES ONLY",
        angle_deg: float = -12.0,
        stamp_color: Tuple[int, int, int, int] = (204, 34, 34, 215),  # Vermelho carimbo carmesim
    ) -> Path:
        """
        Gera uma imagem PNG transparente com um carimbo tático militar angulado.
        """
        out_file = Path(output_png_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Imagem base transparente
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        
        # Cria carimbo em tela menor para rotação perfeita
        stamp_w, stamp_h = 750, 200
        stamp_img = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(stamp_img)

        # Retângulo com borda dupla clássica de carimbo militar
        draw.rectangle([(10, 10), (stamp_w - 10, stamp_h - 10)], outline=stamp_color, width=6)
        draw.rectangle([(20, 20), (stamp_w - 20, stamp_h - 20)], outline=stamp_color, width=2)

        # Texto do carimbo
        draw.text((stamp_w // 2, 60), stamp_text, fill=stamp_color, anchor="mm", font_size=40)
        draw.text((stamp_w // 2, 130), sub_text, fill=stamp_color, anchor="mm", font_size=22)

        # Rotaciona com interpolação suave
        rotated_stamp = stamp_img.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=True)

        # Cola no canto superior direito (área clássica de documentos militares)
        pos_x = self.width - rotated_stamp.width - 80
        pos_y = 70
        img.paste(rotated_stamp, (pos_x, pos_y), rotated_stamp)

        img.save(out_file, "PNG")
        logger.info(f"Carimbo militar de desclassificação gerado: {out_file.name}")
        return out_file

    def create_tactical_hud_overlay(
        self,
        output_png_path: str | Path,
        coordinates: str = "54°54'57\"N 37°24'42\"E",
        target_name: str = "TARGET: SERPUKHOV-15 MISSILE BUNKER",
        warning_status: str = "DEFCON 2 // EARLY WARNING MISSILE RADAR",
        color_rgba: Tuple[int, int, int, int] = (0, 240, 255, 175),  # Ciano tático
    ) -> Path:
        """
        Gera um HUD militar com mira de radar, cantoneiras angulares e telemetria.
        """
        out_file = Path(output_png_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Cantoneiras táticas (Corner Brackets)
        margin = 60
        bracket_len = 50
        thick = 3

        # Top-Left
        draw.line([(margin, margin), (margin + bracket_len, margin)], fill=color_rgba, width=thick)
        draw.line([(margin, margin), (margin, margin + bracket_len)], fill=color_rgba, width=thick)

        # Top-Right
        draw.line([(self.width - margin, margin), (self.width - margin - bracket_len, margin)], fill=color_rgba, width=thick)
        draw.line([(self.width - margin, margin), (self.width - margin, margin + bracket_len)], fill=color_rgba, width=thick)

        # Bottom-Left
        draw.line([(margin, self.height - margin), (margin + bracket_len, self.height - margin)], fill=color_rgba, width=thick)
        draw.line([(margin, self.height - margin), (margin, self.height - margin - bracket_len)], fill=color_rgba, width=thick)

        # Bottom-Right
        draw.line([(self.width - margin, self.height - margin), (self.width - margin - bracket_len, self.height - margin)], fill=color_rgba, width=thick)
        draw.line([(self.width - margin, self.height - margin), (self.width - margin, self.height - margin - bracket_len)], fill=color_rgba, width=thick)

        # Mira Central de Tensão (Tactical Crosshair)
        cx, cy = self.width // 2, self.height // 2
        cross_len = 20
        draw.line([(cx - cross_len, cy), (cx - 5, cy)], fill=color_rgba, width=2)
        draw.line([(cx + 5, cy), (cx + cross_len, cy)], fill=color_rgba, width=2)
        draw.line([(cx, cy - cross_len), (cx, cy - 5)], fill=color_rgba, width=2)
        draw.line([(cx, cy + 5), (cx, cy + cross_len)], fill=color_rgba, width=2)
        draw.ellipse([(cx - 35, cy - 35), (cx + 35, cy + 35)], outline=color_rgba, width=1)

        # Informações táticas superiores
        draw.text((margin + 15, margin + 10), target_name, fill=color_rgba, font_size=18)
        draw.text((margin + 15, margin + 35), f"COORD: {coordinates}", fill=color_rgba, font_size=15)

        # Status inferior de alerta
        draw.text((margin + 15, self.height - margin - 35), f"[STATUS]: {warning_status}", fill=(255, 60, 60, 210), font_size=18)

        img.save(out_file, "PNG")
        logger.info(f"HUD tático de radar gerado: {out_file.name}")
        return out_file

    def create_cinematic_lower_third(
        self,
        output_png_path: str | Path,
        data: LowerThirdData,
    ) -> Path:
        """
        Gera uma cartela cinemática de identificação (Lower-Third) em tipografia mono.
        """
        out_file = Path(output_png_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Painel de fundo escurecido semi-transparente no terço inferior esquerdo
        box_x = 80
        box_y = self.height - 240
        box_w = 720
        box_h = 150

        # Gradiente suave / fundo preto transparente
        draw.rectangle([(box_x, box_y), (box_x + box_w, box_y + box_h)], fill=(12, 16, 20, 200))
        
        # Barra lateral de acento (Vermelho tático ou Âmbar)
        draw.rectangle([(box_x, box_y), (box_x + 6, box_y + box_h)], fill=(220, 40, 40, 240))

        # Tipografia
        draw.text((box_x + 25, box_y + 18), data.title.upper(), fill=(255, 255, 255, 255), font_size=28)
        draw.text((box_x + 25, box_y + 58), data.subtitle, fill=(200, 210, 220, 220), font_size=18)
        
        # Linha fina divisória
        draw.line([(box_x + 25, box_y + 92), (box_x + box_w - 25, box_y + 92)], fill=(70, 80, 90, 150), width=1)
        
        # Metadados de coordenadas e arquivo
        meta_str = f"{data.coordinates}  |  {data.date_timestamp}  |  {data.classification}"
        draw.text((box_x + 25, box_y + 104), meta_str, fill=(160, 175, 190, 180), font_size=13)

        img.save(out_file, "PNG")
        logger.info(f"Lower-third cinemático gerado: {out_file.name}")
        return out_file

    def apply_overlay_to_video(
        self,
        input_video_path: str | Path,
        overlay_png_path: str | Path,
        output_video_path: str | Path,
        start_time_sec: float = 0.0,
        duration_sec: Optional[float] = None,
        ffmpeg_bin: str = "ffmpeg",
    ) -> bool:
        """
        Aplica o overlay PNG sobre o vídeo via filtro overlay do FFmpeg.
        """
        in_vid = Path(input_video_path)
        in_overlay = Path(overlay_png_path)
        out_vid = Path(output_video_path)

        if not in_vid.exists() or not in_overlay.exists():
            logger.error("Vídeo ou overlay inexistente para composição.")
            return False

        out_vid.parent.mkdir(parents=True, exist_ok=True)

        if duration_sec is not None:
            enable_expr = f"between(t,{start_time_sec},{start_time_sec + duration_sec})"
        else:
            enable_expr = f"gte(t,{start_time_sec})"

        filter_str = f"[0:v][1:v]overlay=0:0:enable='{enable_expr}'[v]"

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", str(in_vid),
            "-i", str(in_overlay),
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "17",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(out_vid),
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return out_vid.exists() and out_vid.stat().st_size > 0
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao aplicar overlay com FFmpeg: {e.stderr}")
            return False
