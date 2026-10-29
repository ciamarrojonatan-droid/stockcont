#!/usr/bin/env python3
"""StockCont Multi-Platform Compliance & Anti-Ban Safety Engine.

Enforces strict compliance with submission guidelines across all target microstock agencies:
  - Adobe Stock: Full AI support with mandatory AI disclosure tags.
  - Freepik: AI allowed, 2000px longest side, max 100 char title, 5-50 keywords.
  - Dreamstime: AI allowed, caption MUST start with "Generative AI illustration. ".
  - 123RF: AI allowed as illustration/digital art, min 4MP, 7-50 keywords.
  - Pond5: AI allowed, Full HD/4K minimum.
  - Vecteezy: AI allowed, min 4MP.
  - Ingram: AI allowed, min 4MP.
  - Alamy: STRICT BAN on AI-generated content (Section 1.3 of Contributor Contract).
           Any AI image sent to Alamy causes QC rejection and immediate account termination.
           This engine AUTOMATICALLY BLOCKS any AI asset from being dispatched to Alamy.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
import os
import re

from PIL import Image
import iptcinfo3
import piexif

logger = logging.getLogger("PlatformCompliance")
logging.getLogger("iptcinfo").setLevel(logging.ERROR)


@dataclass
class PlatformRules:
    key: str
    name: str
    allows_ai: bool
    ai_policy_notes: str
    min_megapixels: float = 4.0
    max_megapixels: float = 100.0
    min_dimension_px: int = 2000
    max_file_size_mb: float = 45.0
    min_uncompressed_mb: float = 0.0
    min_keywords: int = 5
    max_keywords: int = 50
    min_title_length: int = 5
    max_title_length: int = 200
    min_title_words: int = 3
    mandatory_ai_keywords: List[str] = field(default_factory=list)
    forbidden_keywords: List[str] = field(default_factory=list)
    required_caption_prefix: str = ""
    allowed_formats: List[str] = field(default_factory=lambda: [".jpg", ".jpeg"])
    allowed_color_modes: List[str] = field(default_factory=lambda: ["RGB"])
    min_dpi: int = 300
    # Video Specific Rules
    allows_video: bool = True
    min_video_duration_sec: float = 5.0
    max_video_duration_sec: float = 60.0
    min_video_resolution: Tuple[int, int] = (1920, 1080)
    allowed_video_codecs: List[str] = field(default_factory=lambda: ["h264", "prores", "hevc"])
    allowed_video_containers: List[str] = field(default_factory=lambda: [".mp4", ".mov"])
    require_silent_audio: bool = True


PLATFORM_RULES: Dict[str, PlatformRules] = {
    "adobe": PlatformRules(
        key="adobe",
        name="Adobe Stock",
        allows_ai=True,
        ai_policy_notes="Conteúdo de IA totalmente aceito. Requer disclosure mandatório em keywords e categoria.",
        min_megapixels=4.0,
        max_megapixels=100.0,
        min_dimension_px=1500,
        max_file_size_mb=45.0,
        min_keywords=5,
        max_keywords=50,
        min_title_length=5,
        max_title_length=200,
        mandatory_ai_keywords=["ai generated", "generative ai", "digital art", "illustration"],
    ),
    "freepik": PlatformRules(
        key="freepik",
        name="Freepik",
        allows_ai=True,
        ai_policy_notes="Conteúdo de IA aceito. Exige lado maior >= 2000px, título com no máx 100 caracteres e 5 a 50 tags.",
        min_megapixels=0.5,
        max_megapixels=100.0,
        min_dimension_px=2000,
        max_file_size_mb=80.0,
        min_keywords=5,
        max_keywords=50,
        min_title_length=5,
        max_title_length=100,
        min_title_words=3,
        mandatory_ai_keywords=["generative ai", "ai generated"],
    ),
    "dreamstime": PlatformRules(
        key="dreamstime",
        name="Dreamstime",
        allows_ai=True,
        ai_policy_notes="Conteúdo de IA aceito. A descrição/caption DEVE começar com 'Generative AI illustration. '.",
        min_megapixels=3.0,
        max_megapixels=100.0,
        min_dimension_px=1500,
        max_file_size_mb=50.0,
        min_keywords=5,
        max_keywords=80,
        min_title_length=5,
        max_title_length=200,
        required_caption_prefix="Generative AI illustration.",
        mandatory_ai_keywords=["ai generated", "generative ai", "illustration"],
    ),
    "123rf": PlatformRules(
        key="123rf",
        name="123RF",
        allows_ai=True,
        ai_policy_notes="Conteúdo de IA aceito como ilustração/arte digital. Mínimo 4MP e 7 a 50 keywords.",
        min_megapixels=4.0,
        max_megapixels=100.0,
        min_dimension_px=2000,
        max_file_size_mb=50.0,
        min_keywords=7,
        max_keywords=50,
        min_title_length=5,
        max_title_length=200,
        mandatory_ai_keywords=["generative ai", "illustration"],
    ),
    "pond5": PlatformRules(
        key="pond5",
        name="Pond5",
        allows_ai=True,
        ai_policy_notes="Conteúdo de IA aceito. Mínimo Full HD / 4K.",
        min_megapixels=2.0,
        max_megapixels=100.0,
        min_dimension_px=1920,
        max_file_size_mb=50.0,
        min_keywords=5,
        max_keywords=50,
        min_title_length=5,
        max_title_length=200,
    ),
    "vecteezy": PlatformRules(
        key="vecteezy",
        name="Vecteezy",
        allows_ai=True,
        ai_policy_notes="Conteúdo de IA aceito no programa de imagens de IA. Mínimo 4MP.",
        min_megapixels=4.0,
        max_megapixels=100.0,
        min_dimension_px=2000,
        max_file_size_mb=50.0,
        min_keywords=5,
        max_keywords=50,
        min_title_length=5,
        max_title_length=200,
    ),
    "ingram": PlatformRules(
        key="ingram",
        name="Ingram",
        allows_ai=True,
        ai_policy_notes="Conteúdo de IA aceito com declaração comercial. Mínimo 4MP.",
        min_megapixels=4.0,
        max_megapixels=100.0,
        min_dimension_px=2000,
        max_file_size_mb=50.0,
        min_keywords=5,
        max_keywords=50,
        min_title_length=5,
        max_title_length=200,
    ),
    "alamy": PlatformRules(
        key="alamy",
        name="Alamy",
        allows_ai=False,
        ai_policy_notes="PROIBIÇÃO ESTRITA DE IA: A Alamy proíbe terminantemente qualquer imagem gerada por IA "
                        "(Seção 1.3 do Contrato de Contribuinte). Submeter IA resulta em falha no QC e banimento "
                        "permanente da conta. O StockCont bloqueia automaticamente o envio para proteger sua conta.",
        min_megapixels=6.0,
        max_megapixels=150.0,
        min_dimension_px=2000,
        max_file_size_mb=100.0,
        min_uncompressed_mb=17.0,  # Regra dos 17MB descompactados (width * height * 3 > 17MB)
        min_keywords=5,
        max_keywords=50,
        min_title_length=5,
        max_title_length=200,
        forbidden_keywords=["ai generated", "generative ai", "ai", "artificial intelligence", "midjourney", "flux", "stable diffusion", "dall-e", "prompt"],
    ),
}


@dataclass
class ComplianceResult:
    platform: str
    platform_name: str
    is_compliant: bool
    blocked: bool = False
    block_reason: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "platform_name": self.platform_name,
            "is_compliant": self.is_compliant,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
        }


def ensure_image_dpi(image_path: Path, target_dpi: int = 300) -> bool:
    """Enforces target DPI (300 DPI) across both JFIF APP0 and EXIF IFD0 headers without recompression.
    
    Returns True if successfully updated or already compliant.
    """
    if not image_path.exists():
        return False

    try:
        # 1. Update EXIF XResolution, YResolution, and ResolutionUnit in-place
        try:
            exif_dict = piexif.load(str(image_path))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

        if "0th" not in exif_dict:
            exif_dict["0th"] = {}

        exif_dict["0th"][piexif.ImageIFD.XResolution] = (target_dpi, 1)
        exif_dict["0th"][piexif.ImageIFD.YResolution] = (target_dpi, 1)
        exif_dict["0th"][piexif.ImageIFD.ResolutionUnit] = 2  # 2 = Inches (DPI)

        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, str(image_path))

        # 2. Update JFIF APP0 header if present (fast binary in-place update)
        with open(image_path, "r+b") as f:
            header_sample = f.read(64)
            if header_sample.startswith(b"\xff\xd8\xff\xe0") and b"JFIF\x00" in header_sample:
                jfif_pos = header_sample.find(b"JFIF\x00")
                # unit (1 = inches) at jfif_pos + 7, Xdensity at +8, Ydensity at +10
                f.seek(jfif_pos + 7)
                f.write(bytes([
                    1,
                    (target_dpi >> 8) & 0xFF,
                    target_dpi & 0xFF,
                    (target_dpi >> 8) & 0xFF,
                    target_dpi & 0xFF,
                ]))

        logger.debug(f"Applied {target_dpi} DPI to {image_path.name}")
        return True
    except Exception as e:
        logger.warning(f"Could not apply {target_dpi} DPI to {image_path.name}: {e}")
        return False


def read_image_properties(image_path: Path) -> Dict[str, Any]:
    """Inspects physical file properties, dimensions, color mode, uncompressed size, DPI, and IPTC tags."""
    props: Dict[str, Any] = {
        "exists": False,
        "width": 0,
        "height": 0,
        "mode": "",
        "format": "",
        "megapixels": 0.0,
        "file_size_mb": 0.0,
        "uncompressed_mb": 0.0,
        "dpi": (72, 72),
        "dpi_x": 72,
        "dpi_y": 72,
        "title": "",
        "caption": "",
        "keywords": [],
        "has_ai_metadata": False,
    }

    if not image_path.exists():
        return props

    props["exists"] = True
    props["file_size_mb"] = round(image_path.stat().st_size / (1024 * 1024), 2)

    try:
        with Image.open(image_path) as img:
            props["width"] = img.width
            props["height"] = img.height
            props["mode"] = img.mode
            props["format"] = img.format or image_path.suffix.upper().replace(".", "")
            mp = (img.width * img.height) / 1_000_000.0
            props["megapixels"] = round(mp, 2)
            # Photoshop uncompressed RGB file size in MB: width * height * 3 bytes / 1024^2
            uncomp = (img.width * img.height * 3) / (1024 * 1024)
            props["uncompressed_mb"] = round(uncomp, 2)

            raw_dpi = img.info.get("dpi")
            if raw_dpi and isinstance(raw_dpi, (tuple, list)) and len(raw_dpi) >= 2:
                try:
                    dpi_x = int(round(raw_dpi[0]))
                    dpi_y = int(round(raw_dpi[1]))
                    props["dpi"] = (dpi_x, dpi_y)
                    props["dpi_x"] = dpi_x
                    props["dpi_y"] = dpi_y
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Could not open image {image_path.name} with PIL: {e}")
        return props

    # Read EXIF DPI fallback if present
    try:
        exif = piexif.load(str(image_path))
        if "0th" in exif:
            x_res = exif["0th"].get(piexif.ImageIFD.XResolution)
            y_res = exif["0th"].get(piexif.ImageIFD.YResolution)
            if x_res and isinstance(x_res, tuple) and x_res[1] != 0:
                props["dpi_x"] = int(round(x_res[0] / x_res[1]))
            if y_res and isinstance(y_res, tuple) and y_res[1] != 0:
                props["dpi_y"] = int(round(y_res[0] / y_res[1]))
            props["dpi"] = (props["dpi_x"], props["dpi_y"])
    except Exception:
        pass

    # Read IPTC metadata if present
    try:
        iptc = iptcinfo3.IPTCInfo(str(image_path), force=True)
        if iptc.get("object name"):
            raw_title = iptc["object name"]
            props["title"] = raw_title.decode("utf-8", "ignore") if isinstance(raw_title, bytes) else str(raw_title)

        if iptc.get("caption/abstract"):
            raw_caption = iptc["caption/abstract"]
            props["caption"] = raw_caption.decode("utf-8", "ignore") if isinstance(raw_caption, bytes) else str(raw_caption)

        if iptc.get("keywords"):
            raw_kws = iptc["keywords"]
            kws_list = []
            for k in raw_kws:
                decoded = k.decode("utf-8", "ignore") if isinstance(k, bytes) else str(k)
                if decoded.strip():
                    kws_list.append(decoded.strip())
            props["keywords"] = kws_list

        # Detect AI markers
        caption_lower = props["caption"].lower()
        title_lower = props["title"].lower()
        kws_lower = [k.lower() for k in props["keywords"]]
        ai_terms = {"generative ai", "ai generated", "artificial intelligence", "digital art", "midjourney", "flux", "stable diffusion"}
        if (
            any(term in caption_lower for term in ["generative ai", "ai generated"])
            or any(term in title_lower for term in ["generative ai", "ai generated"])
            or any(term in kws_lower for term in ai_terms)
        ):
            props["has_ai_metadata"] = True

    except Exception:
        pass

    return props


def validate_image_compliance(
    image_path: Path,
    platform: str,
    is_ai_generated: bool = True,
    metadata_override: Optional[Dict[str, Any]] = None,
) -> ComplianceResult:
    """Validates an image against the exact compliance rules of a specific agency.
    
    If platform is 'alamy' and the image is generated by AI or contains AI metadata,
    it is AUTOMATICALLY BLOCKED with a safety barrier to protect the user's account.
    """
    rules = PLATFORM_RULES.get(platform.lower())
    if not rules:
        return ComplianceResult(
            platform=platform,
            platform_name=platform,
            is_compliant=True,
            warnings=[f"Nenhuma regra específica cadastrada para a agência '{platform}'."],
        )

    props = read_image_properties(image_path)
    if metadata_override:
        if "title" in metadata_override:
            props["title"] = metadata_override["title"]
        if "description" in metadata_override:
            props["caption"] = metadata_override["description"]
        if "keywords" in metadata_override:
            props["keywords"] = metadata_override["keywords"]

    result = ComplianceResult(
        platform=rules.key,
        platform_name=rules.name,
        is_compliant=True,
        details=props,
    )

    if not props["exists"]:
        result.is_compliant = False
        result.errors.append(f"Arquivo não encontrado: {image_path}")
        return result

    # 1. ANTI-BAN BARRIER FOR ALAMY
    if rules.key == "alamy":
        if is_ai_generated or props["has_ai_metadata"]:
            result.is_compliant = False
            result.blocked = True
            result.block_reason = (
                "⛔ BLOQUEADO AUTOMATICAMENTE: A Alamy proíbe estritamente qualquer imagem gerada por IA "
                "(Contrato de Contribuinte Seção 1.3). O envio foi abortado para proteger sua conta contra "
                "rejeição em massa e banimento permanente."
            )
            result.errors.append("Alamy proíbe conteúdo gerado por IA.")
            return result

        # If non-AI (real camera photograph): check Alamy's 17MB uncompressed rule
        if props["uncompressed_mb"] < rules.min_uncompressed_mb:
            result.is_compliant = False
            result.errors.append(
                f"Tamanho descompactado insuficiente para a Alamy ({props['uncompressed_mb']} MB < {rules.min_uncompressed_mb} MB exigidos)."
            )

        # Check for forbidden AI keywords on Alamy
        for fk in rules.forbidden_keywords:
            if fk in [k.lower() for k in props["keywords"]]:
                result.is_compliant = False
                result.errors.append(f"Palavra-chave proibida na Alamy detectada: '{fk}'")

    # 2. File Format and Color Mode Checks
    ext = image_path.suffix.lower()
    if ext not in rules.allowed_formats:
        result.is_compliant = False
        result.errors.append(f"Formato {ext} não aceito. Formatos permitidos: {rules.allowed_formats}")

    if props["mode"] not in rules.allowed_color_modes:
        result.is_compliant = False
        result.errors.append(f"Modo de cor '{props['mode']}' inválido. Exigido: {rules.allowed_color_modes}")

    # 3. File Size (MB)
    if props["file_size_mb"] > rules.max_file_size_mb:
        result.is_compliant = False
        result.errors.append(f"Tamanho do arquivo ({props['file_size_mb']} MB) excede o limite máximo de {rules.max_file_size_mb} MB.")

    # 4. Resolution Checks (Megapixels & Dimensions)
    if props["megapixels"] < rules.min_megapixels:
        result.is_compliant = False
        result.errors.append(f"Resolução ({props['megapixels']} MP) abaixo do mínimo exigido de {rules.min_megapixels} MP.")

    if props["megapixels"] > rules.max_megapixels:
        result.is_compliant = False
        result.errors.append(f"Resolução ({props['megapixels']} MP) acima do limite de {rules.max_megapixels} MP.")

    longest_side = max(props["width"], props["height"])
    if longest_side < rules.min_dimension_px:
        result.is_compliant = False
        result.errors.append(f"Lado maior ({longest_side}px) menor que o mínimo exigido de {rules.min_dimension_px}px.")

    # 5. Metadata Compliance
    keywords = props.get("keywords", [])
    if keywords:
        if len(keywords) < rules.min_keywords:
            result.is_compliant = False
            result.errors.append(f"Quantidade de palavras-chave ({len(keywords)}) menor que o mínimo de {rules.min_keywords}.")
        elif len(keywords) > rules.max_keywords:
            result.is_compliant = False
            result.errors.append(f"Quantidade de palavras-chave ({len(keywords)}) excede o máximo de {rules.max_keywords}.")

    # Mandatory AI keywords check for platforms that require disclosure
    if is_ai_generated and rules.mandatory_ai_keywords:
        lower_kws = [k.lower() for k in keywords]
        has_mandatory = any(mkw in lower_kws for mkw in rules.mandatory_ai_keywords)
        if not has_mandatory:
            result.warnings.append(
                f"Nenhuma tag obrigatória de IA encontrada para {rules.name}. Tags recomendadas: {rules.mandatory_ai_keywords}"
            )

    # Dreamstime Caption check
    if is_ai_generated and rules.required_caption_prefix:
        caption = props.get("caption", "")
        if not caption.startswith(rules.required_caption_prefix):
            result.warnings.append(
                f"Para {rules.name}, a descrição deve iniciar com '{rules.required_caption_prefix}'."
            )

    # Title Length & Word Count Check (especially Freepik max 100 chars, min 3 words)
    title = props.get("title", "")
    if title:
        if len(title) < rules.min_title_length:
            result.is_compliant = False
            result.errors.append(f"Título muito curto ({len(title)} caracteres < {rules.min_title_length}).")
        if len(title) > rules.max_title_length:
            result.is_compliant = False
            result.errors.append(f"Título excede limite da agência ({len(title)} caracteres > {rules.max_title_length}).")
        
        word_count = len(title.split())
        if word_count < rules.min_title_words:
            result.is_compliant = False
            result.errors.append(f"Título possui poucas palavras ({word_count} palavras < {rules.min_title_words}).")

    # 6. Commercial Print DPI Density Check (Standard: 300 DPI)
    if props["dpi_x"] < rules.min_dpi or props["dpi_y"] < rules.min_dpi:
        result.warnings.append(
            f"Densidade de impressão ({props['dpi_x']}x{props['dpi_y']} DPI) abaixo do padrão comercial de {rules.min_dpi} DPI."
        )

    return result


def validate_all_platforms(
    image_path: Path,
    is_ai_generated: bool = True,
    metadata_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, ComplianceResult]:
    """Validates an image against all known microstock platforms."""
    results: Dict[str, ComplianceResult] = {}
    for key in PLATFORM_RULES:
        results[key] = validate_image_compliance(
            image_path=image_path,
            platform=key,
            is_ai_generated=is_ai_generated,
            metadata_override=metadata_override,
        )
    return results


def sanitize_metadata_for_agency(
    title: str,
    description: str,
    keywords: List[str],
    platform: str,
    is_ai_generated: bool = True,
) -> Dict[str, Any]:
    """Adapts title, description, and keywords to strictly conform to an agency's limits."""
    rules = PLATFORM_RULES.get(platform.lower())
    if not rules:
        return {"title": title, "description": description, "keywords": keywords}

    # 1. Sanitize Title
    clean_title = title.strip()
    if len(clean_title) > rules.max_title_length:
        clean_title = clean_title[: rules.max_title_length]
        if " " in clean_title:
            clean_title = clean_title.rsplit(" ", 1)[0]

    # 2. Sanitize Description
    clean_desc = description.strip()
    if is_ai_generated and rules.required_caption_prefix and not clean_desc.startswith(rules.required_caption_prefix):
        clean_desc = f"{rules.required_caption_prefix} {clean_desc}".strip()

    # 3. Sanitize Keywords
    clean_kws: List[str] = []
    seen = set()
    for k in keywords:
        k_clean = k.strip()
        if k_clean and k_clean.lower() not in seen:
            seen.add(k_clean.lower())
            clean_kws.append(k_clean)

    # Ensure mandatory AI keywords if allowed and AI generated
    if is_ai_generated and rules.allows_ai and rules.mandatory_ai_keywords:
        for mkw in rules.mandatory_ai_keywords:
            if mkw not in seen:
                clean_kws.append(mkw)
                seen.add(mkw)

    # Remove forbidden keywords (e.g., Alamy)
    if rules.forbidden_keywords:
        forbidden_set = set(rules.forbidden_keywords)
        clean_kws = [k for k in clean_kws if k.lower() not in forbidden_set]

    # Cap to agency max
    if len(clean_kws) > rules.max_keywords:
        clean_kws = clean_kws[: rules.max_keywords]

    return {
        "title": clean_title,
        "description": clean_desc,
        "keywords": clean_kws,
    }


def validate_video_compliance(
    video_path: Path | str,
    platform: str = "adobe",
    is_ai_generated: bool = True,
    metadata_override: Optional[Dict[str, Any]] = None,
) -> ComplianceResult:
    """Validates video compliance against microstock platform rules with Anti-Ban safety barrier."""
    from src.video.ffmpeg_processor import probe_video

    path = Path(video_path).resolve()
    platform_key = platform.lower()
    rules = PLATFORM_RULES.get(platform_key)

    if not rules:
        return ComplianceResult(
            platform=platform,
            platform_name=platform,
            is_compliant=False,
            errors=[f"Plataforma desconhecida: '{platform}'"],
        )

    # 1. ADR-05 Anti-Ban Safety Barrier (Alamy strictly forbids AI video/footage)
    if is_ai_generated and not rules.allows_ai:
        return ComplianceResult(
            platform=rules.key,
            platform_name=rules.name,
            is_compliant=False,
            blocked=True,
            block_reason=(
                f"BLOQUEADO AUTOMATICAMENTE (Anti-Ban Safety Barrier): {rules.name} proíbe "
                f"estritamente qualquer vídeo gerado por IA ({rules.ai_policy_notes}). "
                f"Envio cancelado para evitar banimento da conta."
            ),
            errors=[f"Envio bloqueado: {rules.name} proíbe vídeos gerados por IA."],
        )

    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    if not path.is_file():
        return ComplianceResult(
            platform=rules.key,
            platform_name=rules.name,
            is_compliant=False,
            errors=[f"Arquivo de vídeo não encontrado: {path}"],
        )

    # Check container extension
    ext = path.suffix.lower()
    if ext not in rules.allowed_video_containers:
        errors.append(
            f"Extensão de vídeo '{ext}' não aceita pela {rules.name}. "
            f"Formatos aceitos: {', '.join(rules.allowed_video_containers)}"
        )

    # Probe video technical properties
    try:
        props = probe_video(path)
        details["width"] = props.width
        details["height"] = props.height
        details["duration_seconds"] = props.duration_seconds
        details["fps"] = props.fps
        details["video_codec"] = props.video_codec
        details["audio_codec"] = props.audio_codec
        details["has_audio"] = props.has_audio
        details["filesize_mb"] = round(props.filesize_bytes / (1024 * 1024), 2)
        details["aspect_ratio"] = props.aspect_ratio

        # Duration validation
        if props.duration_seconds < rules.min_video_duration_sec:
            errors.append(
                f"Duração ({props.duration_seconds}s) inferior ao mínimo de {rules.min_video_duration_sec}s."
            )
        elif props.duration_seconds > rules.max_video_duration_sec:
            errors.append(
                f"Duração ({props.duration_seconds}s) superior ao máximo de {rules.max_video_duration_sec}s."
            )

        # Resolution validation (support both 16:9 Landscape and 9:16 Vertical)
        min_w, min_h = rules.min_video_resolution
        is_landscape_ok = props.width >= min_w and props.height >= min_h
        is_vertical_ok = props.width >= min_h and props.height >= min_w
        if not (is_landscape_ok or is_vertical_ok):
            errors.append(
                f"Resolução ({props.width}x{props.height}) abaixo do mínimo exigido "
                f"({min_w}x{min_h} ou {min_h}x{min_w})."
            )

        # Codec validation
        normalized_codecs = [c.lower() for c in rules.allowed_video_codecs]
        if props.video_codec.lower() not in normalized_codecs:
            errors.append(
                f"Codec de vídeo '{props.video_codec}' não permitido. "
                f"Aceitos: {', '.join(rules.allowed_video_codecs)}"
            )

        # Audio check
        if rules.require_silent_audio and props.has_audio:
            warnings.append(
                f"Vídeo contém faixa de áudio '{props.audio_codec}'. "
                f"Microstocks preferem vídeo mudo (-an) para evitar rejeição por ruído."
            )

    except Exception as e:
        errors.append(f"Erro ao analisar propriedades do vídeo com ffprobe: {e}")

    # Metadata validation if provided
    if metadata_override:
        title = metadata_override.get("title", "")
        keywords = metadata_override.get("keywords", [])
        if title and len(title) > rules.max_title_length:
            warnings.append(f"Título ({len(title)} caracteres) excede o limite de {rules.max_title_length}.")
        if keywords and len(keywords) > rules.max_keywords:
            warnings.append(f"Número de keywords ({len(keywords)}) excede o máximo de {rules.max_keywords}.")

    return ComplianceResult(
        platform=rules.key,
        platform_name=rules.name,
        is_compliant=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        details=details,
    )


def validate_all_platforms_video(
    video_path: Path | str,
    is_ai_generated: bool = True,
    metadata_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, ComplianceResult]:
    """Validates a video against all configured microstock platforms."""
    results: Dict[str, ComplianceResult] = {}
    for key in PLATFORM_RULES:
        results[key] = validate_video_compliance(
            video_path=video_path,
            platform=key,
            is_ai_generated=is_ai_generated,
            metadata_override=metadata_override,
        )
    return results
