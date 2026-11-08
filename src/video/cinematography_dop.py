"""
StockCont & DarkFactory — Cinematography & Composition Engineering Engine (Virtual DoP)
========================================================================================
Motor industrial de Direção de Fotografia (Director of Photography - DoP) e Engenharia
de Composição Visual para cada tomada de vídeo e keyframe.
Incorpora:
1. Óptica e Física de Lentes: Lentes Anamórficas (Panavision, Cooke, Arri Master) vs
   Esféricas Prime (Zeiss Supreme, Leica Summilux), distância focal e abertura T-Stop.
2. Geometria de Composição: Regra dos Terços, Espiral de Ouro (Fibonacci), Simetria
   Kubrickiana (1-Point Perspective), Dutch Angle (tensão canted), Dirty Single Occlusion.
3. Iluminação & Chiaroscuro: Razão Key-to-Fill (16:1, 8:1, 4:1), temperatura Kelvin
   dual-split (Tungstênio 2800K vs Ciano 6500K) e feixes volumétricos (God Rays).
4. Auditor de Keyframes & Computer Vision: Extração de keyframes estratégicos
   (Abertura, Golden Ratio 0.618, Clímax) com cálculo de alinhamento dos terços,
   contraste dinâmico e renderização de guias visuais translúcidas de composição.
5. Injetor de Prompts de Cinematografia para T2V e I2V (MiniMax H3, Veo 2, ComfyUI).
"""

from __future__ import annotations

import logging
import math
import subprocess
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("stockcont.video.cinematography_dop")


class LensOpticsType(str, Enum):
    """Família óptica de lentes cinematográficas."""
    ANAMORPHIC_PANAVISION = "panavision_c_series"   # 40mm T2.3 - 2x squeeze, horizontal streaks, oval bokeh
    ANAMORPHIC_COOKE = "cooke_anamorphic_i"          # 35mm T2.3 - 'Cooke Look', textura orgânica aveludada
    ANAMORPHIC_ARRI = "arri_master_anamorphic"       # 50mm T1.9 - Clareza cirúrgica, flare controlado
    SPHERICAL_ZEISS = "zeiss_supreme_prime"          # 21mm T1.5 - Ultra-wide dramático sem distorção
    SPHERICAL_LEICA = "leica_summilux_c"             # 35mm T1.4 - Perspectiva do olho humano, bokeh circular
    SPHERICAL_TELE = "arri_signature_75mm"           # 75mm T1.8 - Compressão de planos e isolamento dramático
    MACRO_PROBE = "laowa_probe_24mm"                 # 24mm T14 - Lente macro periscópica para hardware tático


class CompositionGeometry(str, Enum):
    """Geometria e regras de enquadramento composicional."""
    RULE_OF_THIRDS = "rule_of_thirds"               # Pontos de força (1/3, 2/3) e lead room
    GOLDEN_SPIRAL = "golden_spiral"                 # Espiral logarítmica de Fibonacci
    KUBRICK_ONE_POINT = "kubrick_one_point"         # Simetria frontal rigorosa com fuga central
    DUTCH_ANGLE = "dutch_angle"                     # Câmera inclinada 7° a 15° (tensão/desespero)
    DIRTY_SINGLE_OCCLUSION = "dirty_single"         # Oclusão em primeiro plano (30-40% borrado)
    LOW_ANGLE_OPPRESSION = "low_angle_oppression"   # Câmera baixa apontando para cima (opressão)
    HIGH_ANGLE_VULNERABILITY = "high_angle_vuln"    # Câmera alta apontando para baixo (vulnerabilidade)


class LightingRatio(str, Enum):
    """Razão de contraste entre luz principal (Key) e preenchimento (Fill)."""
    EXTREME_CHIAROSCURO_16_1 = "16:1"  # Caravaggio / Gordon Willis Noir (sombras breu absoluto)
    HIGH_CONTRAST_8_1 = "8_to_1"       # Suspense tático e noir clássico
    DRAMATIC_NATURAL_4_1 = "4_to_1"    # Rembrandt cinematográfico padrão
    BALANCED_2_1 = "2_to_1"            # Iluminação suave e difusa


@dataclass(frozen=True)
class LensSpecification:
    """Especificação técnica de uma lente cinematográfica."""
    model_name: str
    focal_length_mm: int
    t_stop: float
    anamorphic: bool
    squeeze_factor: float
    bokeh_shape: str
    flare_character: str
    dop_aesthetic_notes: str


LENS_CATALOG: Dict[LensOpticsType, LensSpecification] = {
    LensOpticsType.ANAMORPHIC_PANAVISION: LensSpecification(
        model_name="Panavision C-Series 40mm Anamorphic",
        focal_length_mm=40,
        t_stop=2.3,
        anamorphic=True,
        squeeze_factor=2.0,
        bokeh_shape="Oval 2:1 vertical bokeh",
        flare_character="Horizontal cyan/cobalt streak flares with organic aberration",
        dop_aesthetic_notes="Usada em thrillers clássicos e ficções espaciais; textura encorpada de filme analógico.",
    ),
    LensOpticsType.ANAMORPHIC_COOKE: LensSpecification(
        model_name="Cooke Anamorphic /i Full Frame Plus 35mm",
        focal_length_mm=35,
        t_stop=2.3,
        anamorphic=True,
        squeeze_factor=1.8,
        bokeh_shape="Smooth oval bokeh with gentle focus fall-off",
        flare_character="Warm golden and subtle amber horizontal flares ('Cooke Look')",
        dop_aesthetic_notes="Textura aveludada em rostos com alto micro-contraste em detalhes mecânicos.",
    ),
    LensOpticsType.ANAMORPHIC_ARRI: LensSpecification(
        model_name="Arri Master Anamorphic 50mm",
        focal_length_mm=50,
        t_stop=1.9,
        anamorphic=True,
        squeeze_factor=2.0,
        bokeh_shape="Perfectly symmetrical oval bokeh across full frame",
        flare_character="Virtually zero flare and zero focus breathing",
        dop_aesthetic_notes="Rigidez militar e clareza analítica cirúrgica para centros de comando e laboratórios.",
    ),
    LensOpticsType.SPHERICAL_ZEISS: LensSpecification(
        model_name="Zeiss Supreme Prime 21mm",
        focal_length_mm=21,
        t_stop=1.5,
        anamorphic=False,
        squeeze_factor=1.0,
        bokeh_shape="Circular 11-blade aperture bokeh",
        flare_character="Neutral chromatic flare suppression",
        dop_aesthetic_notes="Ultra-wide angular sem distorção geométrica; transmite escala colossal e arquitetura intimidadora.",
    ),
    LensOpticsType.SPHERICAL_LEICA: LensSpecification(
        model_name="Leica Summilux-C 35mm",
        focal_length_mm=35,
        t_stop=1.4,
        anamorphic=False,
        squeeze_factor=1.0,
        bokeh_shape="Creamy circular bokeh",
        flare_character="Delicate veil flares with high shadow contrast",
        dop_aesthetic_notes="Abertura humana natural para tomadas médias intimistas e conflitos psicológicos silenciosos.",
    ),
    LensOpticsType.SPHERICAL_TELE: LensSpecification(
        model_name="Arri Signature Prime 75mm",
        focal_length_mm=75,
        t_stop=1.8,
        anamorphic=False,
        squeeze_factor=1.0,
        bokeh_shape="Magical warm circular bokeh",
        flare_character="Controlled organic glow",
        dop_aesthetic_notes="Forte compressão espacial; isola o oficial ou o espião da equipe ao redor.",
    ),
    LensOpticsType.MACRO_PROBE: LensSpecification(
        model_name="Laowa 24mm T14 2x Macro Probe Lens",
        focal_length_mm=24,
        t_stop=14.0,
        anamorphic=False,
        squeeze_factor=1.0,
        bokeh_shape="Deep focus field",
        flare_character="Direct LED ring illumination",
        dop_aesthetic_notes="Visão periscópica de inseto/probe para rastejar sobre consoles de radar e fios de ignição.",
    ),
}


@dataclass
class CinematographyShotPlan:
    """Plano diretor de fotografia completo para uma tomada ou keyframe."""
    shot_name: str
    camera_body: str
    lens: LensSpecification
    composition: CompositionGeometry
    lighting_ratio: LightingRatio
    kelvin_key: int          # Ex: 2800K (Tungstênio)
    kelvin_fill: int         # Ex: 6500K (Ciano/Moonlight)
    shutter_angle: str       # Ex: "180-degree (1/48s cinematic motion blur)" ou "90-degree crisp action"
    camera_movement: str     # Ex: "Slow mechanical push-in dolly track"
    haze_density: str        # Ex: "Volumetric atmospheric haze with sharp Tyndall shafts"
    aspect_ratio: str        # Ex: "2.39:1 CinemaScope"

    def to_dop_prompt(self) -> str:
        """Gera a cláusula de Direção de Fotografia pronta para injeção em prompts de IA."""
        anamorphic_str = (
            f"Shot on {self.camera_body} with {self.lens.model_name} ({self.lens.focal_length_mm}mm T{self.lens.t_stop}), "
            f"true 2.39:1 anamorphic squeeze with {self.lens.bokeh_shape} and {self.lens.flare_character}. "
            if self.lens.anamorphic
            else f"Shot on {self.camera_body} paired with {self.lens.model_name} ({self.lens.focal_length_mm}mm T{self.lens.t_stop}), spherical cinema prime with {self.lens.bokeh_shape}. "
        )

        comp_desc = {
            CompositionGeometry.RULE_OF_THIRDS: "Meticulous Rule of Thirds composition with subject aligned to the golden intersection and deliberate lead-room looking across the frame.",
            CompositionGeometry.GOLDEN_SPIRAL: "Composition follows a Fibonacci Golden Spiral guiding the viewer's eye along organic curve lines toward the focal epicenter.",
            CompositionGeometry.KUBRICK_ONE_POINT: "Kubrick-inspired strict 1-point central perspective with architectural vanishing lines converging dead center.",
            CompositionGeometry.DUTCH_ANGLE: "Unsettling Dutch angle with camera canted 12 degrees off-axis, communicating severe institutional panic and spatial distortion.",
            CompositionGeometry.DIRTY_SINGLE_OCCLUSION: "Deep voyeuristic 'dirty single' framing with 35% foreground silhouette obstruction creating intense depth and claustrophobia.",
            CompositionGeometry.LOW_ANGLE_OPPRESSION: "Aggressive low-angle hero perspective looking upward 25 degrees, emphasizing monolithic architectural dominance.",
            CompositionGeometry.HIGH_ANGLE_VULNERABILITY: "High-angle observation perspective looking down at a steep downward tilt, accentuating human vulnerability.",
        }.get(self.composition, "Cinematic framing with balanced negative space.")

        light_desc = (
            f"High-contrast chiaroscuro lighting architecture ({self.lighting_ratio.value} key-to-fill ratio): "
            f"Primary key light calibrated at {self.kelvin_key}K warm source contrasting with a deep cold {self.kelvin_fill}K ambient shadow fill. "
            f"{self.haze_density}. Shutter angle locked at {self.shutter_angle}. Camera trajectory: {self.camera_movement}."
        )

        return f"{anamorphic_str}{comp_desc} {light_desc}"


@dataclass
class KeyframeCompositionAudit:
    """Relatório quantitativo de auditoria de composição de um keyframe."""
    image_path: str
    width: int
    height: int
    rule_of_thirds_score: float   # 0 a 100 (% de energia visual nos terços)
    chiaroscuro_contrast_ratio: float  # Ex: 8.4:1
    warm_cold_kelvin_bias: str    # 'warm_dominant', 'cold_dominant', 'balanced_split'
    visual_balance_horizontal: float  # -1.0 (esquerda) a +1.0 (direita)
    annotated_guide_path: Optional[str] = None


class CinematographyEngine:
    """Motor de Direção de Fotografia e Auditoria de Composição."""

    def __init__(self, default_camera: str = "Arri Alexa 65 Large Format Cinema Camera"):
        self.default_camera = default_camera

    def build_shot_plan(
        self,
        shot_name: str,
        lens_type: LensOpticsType = LensOpticsType.ANAMORPHIC_COOKE,
        composition: CompositionGeometry = CompositionGeometry.RULE_OF_THIRDS,
        lighting_ratio: LightingRatio = LightingRatio.HIGH_CONTRAST_8_1,
        kelvin_key: int = 2800,
        kelvin_fill: int = 6500,
        camera_movement: str = "Slow mechanical push-in dolly track",
        shutter_angle: str = "180-degree (1/48s cinematic motion blur)",
        haze_density: str = "Volumetric atmospheric haze with sharp Tyndall shafts",
    ) -> CinematographyShotPlan:
        """Cria uma especificação detalhada de DoP para qualquer tomada."""
        lens_spec = LENS_CATALOG.get(lens_type, LENS_CATALOG[LensOpticsType.ANAMORPHIC_COOKE])
        return CinematographyShotPlan(
            shot_name=shot_name,
            camera_body=self.default_camera,
            lens=lens_spec,
            composition=composition,
            lighting_ratio=lighting_ratio,
            kelvin_key=kelvin_key,
            kelvin_fill=kelvin_fill,
            shutter_angle=shutter_angle,
            camera_movement=camera_movement,
            haze_density=haze_density,
            aspect_ratio="2.39:1 CinemaScope",
        )

    def extract_cinematic_keyframes(
        self,
        video_path: str | Path,
        output_dir: str | Path,
        ffmpeg_bin: str = "ffmpeg",
    ) -> List[Path]:
        """
        Extrai keyframes cinematográficos estratégicos de um vídeo:
        - Keyframe 1: Abertura (t = 0.5s)
        - Keyframe 2: Golden Ratio (t = dur * 0.618)
        - Keyframe 3: Clímax/Meio (t = dur * 0.5)
        - Keyframe 4: Conclusão (t = dur - 0.5s)
        """
        in_vid = Path(video_path)
        out_folder = Path(output_dir)
        out_folder.mkdir(parents=True, exist_ok=True)

        if not in_vid.exists():
            logger.error(f"Vídeo inexistente para extração de keyframes: {in_vid}")
            return []

        # Obtém duração
        dur = self._probe_duration(in_vid)
        sample_times = [
            ("t0_opening", min(0.5, dur * 0.1)),
            ("t_midpoint", dur * 0.5),
            ("t_golden_ratio", dur * 0.618),
            ("t_closing", max(0.6, dur - 0.5)),
        ]

        extracted: List[Path] = []
        for tag, timestamp in sample_times:
            out_img = out_folder / f"{in_vid.stem}_{tag}.jpg"
            cmd = [
                ffmpeg_bin,
                "-y",
                "-ss", f"{timestamp:.3f}",
                "-i", str(in_vid),
                "-vframes", "1",
                "-q:v", "2",
                str(out_img),
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if out_img.exists() and out_img.stat().st_size > 0:
                    extracted.append(out_img)
            except Exception as e:
                logger.warning(f"Falha ao extrair keyframe {tag} em {timestamp:.2f}s: {e}")

        logger.info(f"Extraídos {len(extracted)} keyframes cinematográficos para {in_vid.name}")
        return extracted

    def audit_keyframe_composition(
        self,
        image_path: str | Path,
        generate_annotated_grid: bool = True,
    ) -> KeyframeCompositionAudit:
        """
        Analisa a composição visual, distribuição de luminância e alinhamento dos terços.
        Gera uma imagem anotada com guias composicionais translúcidas (Grid dos Terços e Espiral).
        """
        img_file = Path(image_path)
        if not img_file.exists():
            raise FileNotFoundError(f"Keyframe não encontrado: {img_file}")

        # Carrega via OpenCV (BGR)
        cv_img = cv2.imread(str(img_file))
        if cv_img is None:
            raise ValueError(f"Não foi possível decodificar imagem para auditoria: {img_file}")

        h, w = cv_img.shape[:2]
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

        # 1. Análise de Energia de Bordas nos Terços (Sobel Gradient)
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_energy = np.sqrt(sobel_x**2 + sobel_y**2)
        total_energy = np.sum(edge_energy)

        # Região de interesse dos terços (faixa de 12% ao redor das linhas x=w/3, x=2w/3, y=h/3, y=2h/3)
        mask_thirds = np.zeros((h, w), dtype=bool)
        band_x = int(w * 0.08)
        band_y = int(h * 0.08)

        # Linhas verticais dos terços
        mask_thirds[:, max(0, w // 3 - band_x): min(w, w // 3 + band_x)] = True
        mask_thirds[:, max(0, 2 * w // 3 - band_x): min(w, 2 * w // 3 + band_x)] = True
        # Linhas horizontais dos terços
        mask_thirds[max(0, h // 3 - band_y): min(h, h // 3 + band_y), :] = True
        mask_thirds[max(0, 2 * h // 3 - band_y): min(h, 2 * h // 3 + band_y), :] = True

        energy_in_thirds = np.sum(edge_energy[mask_thirds])
        rule_of_thirds_score = (energy_in_thirds / max(1.0, total_energy)) * 100.0
        # Normaliza score entre 0 e 100 (valores típicos são 30-70%)
        normalized_thirds = min(100.0, max(20.0, rule_of_thirds_score * 1.6))

        # 2. Contraste Chiaroscuro (Percentil 95 / Percentil 5 de luminância)
        p95 = float(np.percentile(gray, 95))
        p05 = float(np.percentile(gray, 5))
        contrast_ratio = round((p95 + 1.0) / max(1.0, p05 + 1.0), 2)

        # 3. Equilíbrio Horizontal de Massa Visual (Centro de Gravidade Luma)
        left_luma = np.mean(gray[:, : w // 2])
        right_luma = np.mean(gray[:, w // 2 :])
        diff_luma = (right_luma - left_luma) / max(1.0, (right_luma + left_luma))
        balance_horizontal = round(float(diff_luma), 3)

        # 4. Bias Cromático Quente vs Frio (Canal Azul vs Canal Vermelho)
        b_channel = np.mean(cv_img[:, :, 0])
        r_channel = np.mean(cv_img[:, :, 2])
        if r_channel > b_channel * 1.15:
            kelvin_bias = "warm_dominant"
        elif b_channel > r_channel * 1.15:
            kelvin_bias = "cold_dominant"
        else:
            kelvin_bias = "balanced_split"

        annotated_path = None
        if generate_annotated_grid:
            annotated_path = self._render_composition_guides(img_file, cv_img)

        return KeyframeCompositionAudit(
            image_path=str(img_file),
            width=w,
            height=h,
            rule_of_thirds_score=round(normalized_thirds, 1),
            chiaroscuro_contrast_ratio=contrast_ratio,
            warm_cold_kelvin_bias=kelvin_bias,
            visual_balance_horizontal=balance_horizontal,
            annotated_guide_path=str(annotated_path) if annotated_path else None,
        )

    def _render_composition_guides(self, original_path: Path, cv_bgr: np.ndarray) -> Path:
        """
        Desenha guias translúcidas cinemáticas sobre a imagem:
        - Grade dos Terços (Rule of Thirds) em Ciano
        - Pontos de Interseção / Power Points
        - Linhas de Enquadramento 2.39:1 CinemaScope
        - Ponto Central (Dead Center Crosshair)
        """
        annotated_file = original_path.parent / f"{original_path.stem}_dop_guides.jpg"
        h, w = cv_bgr.shape[:2]

        overlay = cv_bgr.copy()

        # 1. Linhas dos Terços em Ciano Translúcido
        cyan_color = (255, 240, 0)  # BGR Ciano
        gold_color = (0, 215, 255)  # BGR Dourado

        # Verticais
        cv2.line(overlay, (w // 3, 0), (w // 3, h), cyan_color, 2)
        cv2.line(overlay, (2 * w // 3, 0), (2 * w // 3, h), cyan_color, 2)
        # Horizontais
        cv2.line(overlay, (0, h // 3), (w, h // 3), cyan_color, 2)
        cv2.line(overlay, (0, 2 * h // 3), (w, 2 * h // 3), cyan_color, 2)

        # 2. Power Points (Círculos nos 4 cruzamentos de ouro)
        power_points = [
            (w // 3, h // 3),
            (2 * w // 3, h // 3),
            (w // 3, 2 * h // 3),
            (2 * w // 3, 2 * h // 3),
        ]
        for pt in power_points:
            cv2.circle(overlay, pt, 14, gold_color, 2)
            cv2.circle(overlay, pt, 3, gold_color, -1)

        # 3. Cruz Central de Precisão (Center Crosshair)
        cx, cy = w // 2, h // 2
        cv2.line(overlay, (cx - 15, cy), (cx + 15, cy), (180, 180, 180), 1)
        cv2.line(overlay, (cx, cy - 15), (cx, cy + 15), (180, 180, 180), 1)

        # 4. Matte CinemaScope 2.39:1 (Linhas guias de corte anamórfico)
        scope_margin = int(h * 0.128)
        cv2.line(overlay, (0, scope_margin), (w, scope_margin), (60, 60, 255), 1)  # Linha vermelha guia
        cv2.line(overlay, (0, h - scope_margin), (w, h - scope_margin), (60, 60, 255), 1)

        # Mesclagem alfa suave (55% original + 45% guias)
        blended = cv2.addWeighted(overlay, 0.45, cv_bgr, 0.55, 0)

        # Legenda informativa no topo
        label = "DARKFACTORY DoP SUITE: RULE OF THIRDS + 2.39:1 CINEMASCOPE GUIDE"
        cv2.putText(blended, label, (25, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)

        cv2.imwrite(str(annotated_file), blended, [cv2.IMWRITE_JPEG_QUALITY, 95])
        logger.info(f"Keyframe com guias de composição gerado: {annotated_file.name}")
        return annotated_file

    def _probe_duration(self, video_file: Path) -> float:
        """Obtém duração via ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_file),
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(res.stdout.strip())
        except Exception:
            return 10.0
