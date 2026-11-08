"""
StockCont & DarkFactory — Color Psychology, Semiotics & 60-30-10 Chromatic Engine
===================================================================================
Motor de engenharia cromática, psicologia das cores e semiótica cinematográfica:
1. Regra Proporcional 60-30-10:
   - 60% Cor Dominante (Base / Atmosfera / Ambiente)
   - 30% Cor Secundária (Sujeito / Estrutura / Vestimenta / Luz de Preenchimento)
   - 10% Cor de Acento (Punctum Visual / Gatilho Emocional / Alarme / Ponto Focal)
2. Harmonia Cromática: Complementar, Análoga, Split-Complementar, Triádica, Monocromática.
3. Semiótica Psicológica: Cold War Paranoia, Nuclear Dread Siren, Cyber Espionage,
   Deep Space Void, Bio-Pathogen Hazard, Gordon Willis Noir.
4. Auditor de Paleta por Visão Computacional: Agrupamento K-Means de cores no espaço Lab/RGB,
   cálculo de aderência à proporção 60-30-10 e geração de cartela visual de swatches.
5. Injetor de Prompts Cromáticos para T2V, I2V e Síntese de Imagem.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("stockcont.video.color_psychology")


class ColorHarmonyType(str, Enum):
    """Estrutura geométrica da harmonia no círculo cromático."""
    COMPLEMENTARY = "complementary"         # Contraste máximo de opostos (Teal & Orange)
    SPLIT_COMPLEMENTARY = "split_comp"      # Tensão refinada (Azul ardósia com Âmbar e Carmesim)
    ANALOGOUS_TENSION = "analogous"         # Claustrofobia psicológica (Verde militar, Oliva, Lodo)
    TRIADIC_VINTAGE = "triadic"             # Equilíbrio gráfico retrô da Guerra Fria
    MONOCHROMATIC_TONAL = "monochromatic"   # Isolamento e gravidade existencial P&B / Sepia


class ColorPsychologyArchetype(str, Enum):
    """Arquétipos semióticos de cor para documentários históricos e thrillers."""
    COLD_WAR_PARANOIA = "cold_war_paranoia"
    NUCLEAR_DREAD_SIREN = "nuclear_dread_siren"
    CYBER_ESPIONAGE = "cyber_espionage"
    DEEP_SPACE_VOID = "deep_space_void"
    BIO_PATHOGEN_HAZARD = "bio_pathogen_hazard"
    GORDON_WILLIS_NOIR = "gordon_willis_noir"
    FINCHER_MUTED_SAGE = "fincher_muted_sage"


@dataclass(frozen=True)
class ColorSwatch:
    """Definição de uma cor na paleta."""
    name: str
    hex_code: str
    rgb: Tuple[int, int, int]
    role: str  # 'dominant_60', 'secondary_30', 'accent_10'
    psychological_meaning: str


@dataclass(frozen=True)
class CinematicPalette:
    """Paleta cinematográfica estruturada sob a regra 60-30-10."""
    id: str
    name: str
    archetype: ColorPsychologyArchetype
    harmony: ColorHarmonyType
    psychological_thesis: str
    dominant_60: ColorSwatch
    secondary_30: ColorSwatch
    accent_10: ColorSwatch
    director_references: str

    def to_color_prompt(self) -> str:
        """Gera a cláusula de cores calibrada para injeção em prompts de IA."""
        return (
            f"Color Psychology & 60-30-10 Palette ({self.name}): "
            f"60% Dominant Environmental Base: {self.dominant_60.name} ({self.dominant_60.hex_code}), establishing {self.dominant_60.psychological_meaning}. "
            f"30% Secondary Subject/Architecture Tone: {self.secondary_30.name} ({self.secondary_30.hex_code}), reinforcing {self.secondary_30.psychological_meaning}. "
            f"10% High-Contrast Punctum Accent: {self.accent_10.name} ({self.accent_10.hex_code}), serving as sharp emotional focal point for {self.accent_10.psychological_meaning}. "
            f"Color harmony: {self.harmony.value} with disciplined saturation control and zero chromatic noise."
        )


PALETTE_REGISTRY: Dict[ColorPsychologyArchetype, CinematicPalette] = {
    ColorPsychologyArchetype.COLD_WAR_PARANOIA: CinematicPalette(
        id="cold_war_paranoia",
        name="Cold War Bunker Paranoia",
        archetype=ColorPsychologyArchetype.COLD_WAR_PARANOIA,
        harmony=ColorHarmonyType.SPLIT_COMPLEMENTARY,
        psychological_thesis="Sensação de claustrofobia institucional, espionagem governamental e paranoia antes do colapso.",
        dominant_60=ColorSwatch(
            name="Subterranean Concrete Slate",
            hex_code="#141920",
            rgb=(20, 25, 32),
            role="dominant_60",
            psychological_meaning="opressão de bunkers herméticos e paredes de concreto sem janelas",
        ),
        secondary_30=ColorSwatch(
            name="Soviet Muted Olive Drab",
            hex_code="#324233",
            rgb=(50, 66, 51),
            role="secondary_30",
            psychological_meaning="rigidez burocrática militar e uniformes de oficiais sob pressão",
        ),
        accent_10=ColorSwatch(
            name="Phosphor Radar CRT Green",
            hex_code="#00FF66",
            rgb=(0, 255, 102),
            role="accent_10",
            psychological_meaning="telemetria de mísseis balísticos e dados eletrônicos ameaçadores",
        ),
        director_references="Tomas Alfredson (Tinker Tailor Soldier Spy), Chernobyl (HBO)",
    ),
    ColorPsychologyArchetype.NUCLEAR_DREAD_SIREN: CinematicPalette(
        id="nuclear_dread_siren",
        name="Nuclear Emergency Red Siren",
        archetype=ColorPsychologyArchetype.NUCLEAR_DREAD_SIREN,
        harmony=ColorHarmonyType.COMPLEMENTARY,
        psychological_thesis="Urgência existencial absoluta, pânico biológico e contagem regressiva para catástrofe.",
        dominant_60=ColorSwatch(
            name="Shadowed Carbon Black",
            hex_code="#0B0D11",
            rgb=(11, 13, 17),
            role="dominant_60",
            psychological_meaning="vácuo e escuridão de uma sala de comando sem energia auxiliar",
        ),
        secondary_30=ColorSwatch(
            name="Tungsten Industrial Taupe",
            hex_code="#4A3F35",
            rgb=(74, 63, 53),
            role="secondary_30",
            psychological_meaning="painéis de aço escovado e consoles mecânicos vibrando de tensão",
        ),
        accent_10=ColorSwatch(
            name="Pulsating Strobe Blood Red",
            hex_code="#FF1122",
            rgb=(255, 17, 34),
            role="accent_10",
            psychological_meaning="alarme nuclear de emergência máxima e batimento cardíaco acelerado",
        ),
        director_references="Christopher Nolan (Oppenheimer Trinity Test), Crimson Tide",
    ),
    ColorPsychologyArchetype.CYBER_ESPIONAGE: CinematicPalette(
        id="cyber_espionage",
        name="Tactical Cyber Espionage & Intelligence",
        archetype=ColorPsychologyArchetype.CYBER_ESPIONAGE,
        harmony=ColorHarmonyType.COMPLEMENTARY,
        psychological_thesis="Guerra cibernética de alta frequência, precisão cirúrgica e invasão de satélites espiões.",
        dominant_60=ColorSwatch(
            name="Deep Obsidian Abyss",
            hex_code="#060C16",
            rgb=(6, 12, 22),
            role="dominant_60",
            psychological_meaning="espaço silencioso da rede e salas de servidores blindadas",
        ),
        secondary_30=ColorSwatch(
            name="Tactical Cobalt Steel",
            hex_code="#1C385C",
            rgb=(28, 56, 92),
            role="secondary_30",
            psychological_meaning="carcaças de supercomputadores e iluminação fria de estações de trabalho",
        ),
        accent_10=ColorSwatch(
            name="Electric Neon Cyan",
            hex_code="#00E5FF",
            rgb=(0, 229, 255),
            role="accent_10",
            psychological_meaning="dados criptográficos em trânsito e mira laser de satélite",
        ),
        director_references="Denis Villeneuve (Sicario / Blade Runner 2049), Mr. Robot",
    ),
    ColorPsychologyArchetype.DEEP_SPACE_VOID: CinematicPalette(
        id="deep_space_void",
        name="Deep Space Cosmic Silence",
        archetype=ColorPsychologyArchetype.DEEP_SPACE_VOID,
        harmony=ColorHarmonyType.SPLIT_COMPLEMENTARY,
        psychological_thesis="Insignificância humana perante a imensidão do cosmos e isolamento tecnológico.",
        dominant_60=ColorSwatch(
            name="True Cosmic Void Black",
            hex_code="#020306",
            rgb=(2, 3, 6),
            role="dominant_60",
            psychological_meaning="silêncio infinito do vácuo espacial absoluto",
        ),
        secondary_30=ColorSwatch(
            name="Cryogenic Titanium Silver",
            hex_code="#334155",
            rgb=(51, 65, 85),
            role="secondary_30",
            psychological_meaning="fuselagem externa e módulos pressurizados de sobrevivência",
        ),
        accent_10=ColorSwatch(
            name="Coronal Warning Amber",
            hex_code="#F59E0B",
            rgb=(245, 158, 11),
            role="accent_10",
            psychological_meaning="radiação solar distante e propulsores de manobra de emergência",
        ),
        director_references="Stanley Kubrick (2001: A Space Odyssey), Christopher Nolan (Interstellar)",
    ),
    ColorPsychologyArchetype.BIO_PATHOGEN_HAZARD: CinematicPalette(
        id="bio_pathogen_hazard",
        name="Bio-Pathogen Quarantine Protocol",
        archetype=ColorPsychologyArchetype.BIO_PATHOGEN_HAZARD,
        harmony=ColorHarmonyType.TRIADIC_VINTAGE,
        psychological_thesis="Ameaça invisível de contaminação viral, atmosfera estéril e ruptura biológica.",
        dominant_60=ColorSwatch(
            name="Sterile Clinic Bleached Grey",
            hex_code="#202428",
            rgb=(32, 36, 40),
            role="dominant_60",
            psychological_meaning="enfermarias vedadas com plástico e câmaras de despressurização",
        ),
        secondary_30=ColorSwatch(
            name="Industrial Hazmat Ochre",
            hex_code="#B45309",
            rgb=(180, 83, 9),
            role="secondary_30",
            psychological_meaning="macacões biológicos de proteção nível 4 e filtros químicos",
        ),
        accent_10=ColorSwatch(
            name="UV Sterilization Violet",
            hex_code="#8B5CF6",
            rgb=(139, 92, 246),
            role="accent_10",
            psychological_meaning="lâmpadas germicidas ultravioleta e sinalizadores de biohazard",
        ),
        director_references="Steven Soderbergh (Contagion), 28 Days Later",
    ),
    ColorPsychologyArchetype.GORDON_WILLIS_NOIR: CinematicPalette(
        id="gordon_willis_noir",
        name="Gordon Willis Under-Exposed Master Noir",
        archetype=ColorPsychologyArchetype.GORDON_WILLIS_NOIR,
        harmony=ColorHarmonyType.ANALOGOUS_TENSION,
        psychological_thesis="Decadência moral, conspirações em salas fechadas e poder exercido nas sombras.",
        dominant_60=ColorSwatch(
            name="Under-Exposed Velvet Black",
            hex_code="#070707",
            rgb=(7, 7, 7),
            role="dominant_60",
            psychological_meaning="escuridão densa em que os olhos do personagem desaparecem",
        ),
        secondary_30=ColorSwatch(
            name="Aged Sepia Leather & Wood",
            hex_code="#3E2718",
            rgb=(62, 39, 24),
            role="secondary_30",
            psychological_meaning="móveis coloniais pesados e uísque âmbar em copos de cristal",
        ),
        accent_10=ColorSwatch(
            name="Incandescent Brass Chiaroscuro Rim",
            hex_code="#EAB308",
            rgb=(234, 179, 8),
            role="accent_10",
            psychological_meaning="único facho de luz de abajur recortando o perfil do antagonista",
        ),
        director_references="Gordon Willis (The Godfather, All the President's Men)",
    ),
    ColorPsychologyArchetype.FINCHER_MUTED_SAGE: CinematicPalette(
        id="fincher_muted_sage",
        name="Fincher Muted Sage & Low-Contrast Mystery",
        archetype=ColorPsychologyArchetype.FINCHER_MUTED_SAGE,
        harmony=ColorHarmonyType.SPLIT_COMPLEMENTARY,
        psychological_thesis="Investigação meticulosa e obsessiva, desespero contido e atmosfera taciturna.",
        dominant_60=ColorSwatch(
            name="Desaturated Muted Charcoal",
            hex_code="#1A1F24",
            rgb=(26, 31, 36),
            role="dominant_60",
            psychological_meaning="chuva constante, asfalto molhado e arquivos policiais poeirentos",
        ),
        secondary_30=ColorSwatch(
            name="Pale Celadon Sage Green",
            hex_code="#3D4A41",
            rgb=(61, 74, 65),
            role="secondary_30",
            psychological_meaning="lâmpadas fluorescentes hospitalares e paredes institucionais frias",
        ),
        accent_10=ColorSwatch(
            name="Tungsten Incandescent Glow",
            hex_code="#F59E0B",
            rgb=(245, 158, 11),
            role="accent_10",
            psychological_meaning="lâmpada solitária de mesa sobre pilhas de evidências datilografadas",
        ),
        director_references="David Fincher (Zodiac, Se7en, Mindhunter)",
    ),
}


@dataclass
class ColorDistributionAudit:
    """Resultado da auditoria por visão computacional da regra 60-30-10."""
    image_path: str
    dominant_pct: float     # Ideal: ~60%
    secondary_pct: float    # Ideal: ~30%
    accent_pct: float       # Ideal: ~10%
    rule_60_30_10_adherence_score: float  # 0 a 100
    closest_archetype: str
    dominant_color_hex: str
    secondary_color_hex: str
    accent_color_hex: str
    annotated_palette_card_path: Optional[str] = None


class ColorPsychologyEngine:
    """Motor de orquestração de cores, semiótica e auditoria visual."""

    def get_palette(self, archetype: ColorPsychologyArchetype | str) -> CinematicPalette:
        """Obtém a paleta cinematográfica calibrada."""
        if isinstance(archetype, ColorPsychologyArchetype):
            return PALETTE_REGISTRY[archetype]
        try:
            return PALETTE_REGISTRY[ColorPsychologyArchetype(archetype.lower())]
        except (ValueError, KeyError):
            logger.warning(f"Paleta '{archetype}' desconhecida. Usando 'cold_war_paranoia'.")
            return PALETTE_REGISTRY[ColorPsychologyArchetype.COLD_WAR_PARANOIA]

    def list_palettes(self) -> List[Dict[str, Any]]:
        """Lista todas as paletas cinematográficas disponíveis."""
        return [
            {
                "id": p.id,
                "name": p.name,
                "harmony": p.harmony.value,
                "psychological_thesis": p.psychological_thesis,
                "dominant_60": {"name": p.dominant_60.name, "hex": p.dominant_60.hex_code},
                "secondary_30": {"name": p.secondary_30.name, "hex": p.secondary_30.hex_code},
                "accent_10": {"name": p.accent_10.name, "hex": p.accent_10.hex_code},
                "director_references": p.director_references,
            }
            for p in PALETTE_REGISTRY.values()
        ]

    def audit_keyframe_palette(
        self,
        image_path: str | Path,
        render_swatch_card: bool = True,
    ) -> ColorDistributionAudit:
        """
        Executa K-Means clustering (k=3) na imagem para calcular
        a distribuição real de pixels (60-30-10) e gera a cartela anotada.
        """
        img_file = Path(image_path)
        if not img_file.exists():
            raise FileNotFoundError(f"Imagem não encontrada: {img_file}")

        cv_img = cv2.imread(str(img_file))
        if cv_img is None:
            raise ValueError(f"Falha ao carregar imagem para auditoria cromática: {img_file}")

        # Reduz tamanho para aceleração K-Means
        small = cv2.resize(cv_img, (320, 180), interpolation=cv2.INTER_AREA)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        pixels = rgb_small.reshape(-1, 3).astype(np.float32)

        # K-Means com k=3 para isolar Dominante, Secundária e Acento
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 15, 0.2)
        _, labels, centers = cv2.kmeans(pixels, 3, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        counts = np.bincount(labels.flatten())
        total = float(len(labels))
        percentages = (counts / total) * 100.0

        # Ordena por frequência decrescente: cluster 0 (maior), cluster 1, cluster 2 (menor)
        sorted_indices = np.argsort(percentages)[::-1]
        dominant_pct = float(percentages[sorted_indices[0]])
        secondary_pct = float(percentages[sorted_indices[1]])
        accent_pct = float(percentages[sorted_indices[2]])

        dom_rgb = centers[sorted_indices[0]].astype(int)
        sec_rgb = centers[sorted_indices[1]].astype(int)
        acc_rgb = centers[sorted_indices[2]].astype(int)

        dom_hex = "#{:02x}{:02x}{:02x}".format(*dom_rgb)
        sec_hex = "#{:02x}{:02x}{:02x}".format(*sec_rgb)
        acc_hex = "#{:02x}{:02x}{:02x}".format(*acc_rgb)

        # Cálculo da aderência à regra 60-30-10:
        # Erro = |dom - 60| + |sec - 30| + |acc - 10|
        error = abs(dominant_pct - 60.0) + abs(secondary_pct - 30.0) + abs(accent_pct - 10.0)
        adherence_score = max(0.0, min(100.0, 100.0 - (error * 1.25)))

        # Encontra o arquétipo mais próximo comparando as distâncias euclidianas dos centros RGB
        best_archetype = self._match_closest_archetype(dom_rgb, sec_rgb, acc_rgb)

        card_path = None
        if render_swatch_card:
            card_path = self._render_palette_swatch_card(
                img_file, cv_img, dom_rgb, sec_rgb, acc_rgb, dominant_pct, secondary_pct, accent_pct, adherence_score, best_archetype
            )

        return ColorDistributionAudit(
            image_path=str(img_file),
            dominant_pct=round(dominant_pct, 1),
            secondary_pct=round(secondary_pct, 1),
            accent_pct=round(accent_pct, 1),
            rule_60_30_10_adherence_score=round(adherence_score, 1),
            closest_archetype=best_archetype,
            dominant_color_hex=dom_hex,
            secondary_color_hex=sec_hex,
            accent_color_hex=acc_hex,
            annotated_palette_card_path=str(card_path) if card_path else None,
        )

    def _match_closest_archetype(
        self,
        dom_rgb: np.ndarray,
        sec_rgb: np.ndarray,
        acc_rgb: np.ndarray,
    ) -> str:
        """Determina qual arquétipo pré-calibrado mais se aproxima dos clusters de cor."""
        best_match = ColorPsychologyArchetype.COLD_WAR_PARANOIA.value
        min_dist = float("inf")

        for arch_key, pal in PALETTE_REGISTRY.items():
            ref_dom = np.array(pal.dominant_60.rgb)
            ref_sec = np.array(pal.secondary_30.rgb)
            ref_acc = np.array(pal.accent_10.rgb)

            # Distância ponderada (Dom tem mais peso que Acc)
            dist = (
                np.linalg.norm(dom_rgb - ref_dom) * 0.5 +
                np.linalg.norm(sec_rgb - ref_sec) * 0.3 +
                np.linalg.norm(acc_rgb - ref_acc) * 0.2
            )
            if dist < min_dist:
                min_dist = dist
                best_match = arch_key.value

        return best_match

    def _render_palette_swatch_card(
        self,
        original_path: Path,
        cv_bgr: np.ndarray,
        dom_rgb: np.ndarray,
        sec_rgb: np.ndarray,
        acc_rgb: np.ndarray,
        dom_pct: float,
        sec_pct: float,
        acc_pct: float,
        adherence_score: float,
        archetype: str,
    ) -> Path:
        """
        Adiciona uma barra de amostras cromáticas de cinema (Cinema Swatch Banner)
        no rodapé da imagem com dados da proporção 60-30-10.
        """
        out_file = original_path.parent / f"{original_path.stem}_palette_603010.jpg"
        h, w = cv_bgr.shape[:2]

        banner_h = 100
        canvas = np.zeros((h + banner_h, w, 3), dtype=np.uint8)
        canvas[:h, :w] = cv_bgr

        # Fundo do banner em grafite escuro
        canvas[h:, :] = (15, 18, 22)

        # Larguras das 3 faixas cromáticas
        w_dom = int(w * (dom_pct / 100.0))
        w_sec = int(w * (sec_pct / 100.0))
        w_acc = w - (w_dom + w_sec)

        # Desenha as 3 faixas proporcionais no topo do banner (altura 30px)
        # Nota: cv_bgr usa BGR, então convertemos RGB -> BGR
        cv2.rectangle(canvas, (0, h), (w_dom, h + 30), (int(dom_rgb[2]), int(dom_rgb[1]), int(dom_rgb[0])), -1)
        cv2.rectangle(canvas, (w_dom, h), (w_dom + w_sec, h + 30), (int(sec_rgb[2]), int(sec_rgb[1]), int(sec_rgb[0])), -1)
        cv2.rectangle(canvas, (w_dom + w_sec, h), (w, h + 30), (int(acc_rgb[2]), int(acc_rgb[1]), int(acc_rgb[0])), -1)

        # Informações tipográficas
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_y = h + 65
        label_left = f"60% BASE: {dom_pct:.1f}%  |  30% SECONDARY: {sec_pct:.1f}%  |  10% ACCENT: {acc_pct:.1f}%"
        cv2.putText(canvas, label_left, (25, text_y), font, 0.65, (220, 225, 230), 2, cv2.LINE_AA)

        label_right = f"ADHERENCE: {adherence_score:.1f}%  |  ARCHETYPE: {archetype.upper()}"
        text_size = cv2.getTextSize(label_right, font, 0.65, 2)[0]
        cv2.putText(canvas, label_right, (w - text_size[0] - 25, text_y), font, 0.65, (0, 255, 220), 2, cv2.LINE_AA)

        cv2.imwrite(str(out_file), canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
        logger.info(f"Cartela cromática 60-30-10 gerada: {out_file.name}")
        return out_file
