import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from PIL import Image
import iptcinfo3
import piexif
import pytest

from src.cataloger.adobe_csv_maker import (
    sanitize_filename,
    normalize_keywords,
    format_description,
    embed_metadata,
    MANDATORY_AI_KEYWORDS,
)


def test_sanitize_filename_dangling_stopwords():
    title = "A lone astronaut walking towards a futuristic outpost on an alien planet"
    sanitized = sanitize_filename(title, max_length=60)
    assert not sanitized.endswith("-a")
    assert not sanitized.endswith("-on")
    assert not sanitized.endswith("-an")
    assert sanitized == "lone-astronaut-walking-towards-a-futuristic-outpost"


def test_sanitize_filename_ai_prefix_variants():
    assert sanitize_filename("Generative AI: Modern Office Desk", 75) == "modern-office-desk"
    assert sanitize_filename("Generative AI art: Cyberpunk city", 75) == "cyberpunk-city"
    assert sanitize_filename("AI Generated Image: Mountain sunset", 75) == "mountain-sunset"
    assert sanitize_filename("Generative AI illustration of a futuristic robot", 75) == "futuristic-robot"


def test_normalize_keywords_capping_and_preservation():
    # 55 initial keywords without AI tags
    raw_kws = [f"tag_{i}" for i in range(55)]
    clean_kws, kws_str = normalize_keywords(raw_kws, max_keywords=50)

    assert len(clean_kws) == 50
    for mkw in MANDATORY_AI_KEYWORDS:
        assert mkw in clean_kws, f"Mandatory keyword {mkw} must be preserved"
    assert len(kws_str.split(", ")) == 50


def test_normalize_keywords_deduplication():
    raw_kws = ["Astronaut", "astronaut", "SPACE", "Space", "AI Generated"]
    clean_kws, _ = normalize_keywords(raw_kws)
    assert len(clean_kws) == len(set(k.lower() for k in clean_kws))


def test_format_description():
    # Regular title
    desc1 = format_description("Lone astronaut walking on alien planet")
    assert desc1 == "Generative AI illustration. Lone astronaut walking on alien planet."

    # Already has period
    desc2 = format_description("Lone astronaut walking on alien planet.")
    assert desc2 == "Generative AI illustration. Lone astronaut walking on alien planet."

    # Already contains AI prefix
    desc3 = format_description(
        "Astronaut",
        description="Generative AI illustration: A detailed view of an astronaut exploring Mars.",
    )
    assert desc3 == "Generative AI illustration. A detailed view of an astronaut exploring Mars."

    desc4 = format_description(
        "Astronaut",
        description="AI generated image of an alien base.",
    )
    assert desc4 == "Generative AI illustration. An alien base."


def test_embed_metadata_iptc_and_exif(tmp_path):
    img_src = tmp_path / "test_input.png"
    img_target = tmp_path / "test_output.jpg"
    Image.new("RGB", (100, 100), color=(10, 20, 30)).save(img_src, "PNG")

    long_title = "Lone astronaut walking towards a futuristic outpost on a distant mountainous alien planet during sunrise"
    raw_kws = ["astronaut", "space", "outpost", "alien planet"]
    
    result_path = embed_metadata(
        img_src,
        img_target,
        long_title,
        raw_kws,
        description="A lone astronaut walks on an alien mountain ridge.",
    )

    assert result_path.exists()
    assert result_path.suffix.lower() == ".jpg"

    # Verify IPTC
    iptc = iptcinfo3.IPTCInfo(str(result_path))
    iptc_obj_name = iptc["object name"].decode("utf-8")
    iptc_caption = iptc["caption/abstract"].decode("utf-8")
    iptc_kws = [k.decode("utf-8") for k in iptc["keywords"]]

    assert len(iptc_obj_name.encode("utf-8")) <= 64
    assert not iptc_obj_name.endswith(" ")
    assert iptc_caption.startswith("Generative AI illustration.")
    for mkw in MANDATORY_AI_KEYWORDS:
        assert mkw in iptc_kws

    # Verify EXIF null-terminated XP tags
    exif = piexif.load(str(result_path))
    xp_title_raw = bytes(exif["0th"][0x9C9B])
    xp_desc_raw = bytes(exif["0th"][0x9C9C])

    assert xp_title_raw.endswith(b"\x00\x00")
    assert xp_desc_raw.endswith(b"\x00\x00")

    # Verify 300 DPI in EXIF and PIL
    assert exif["0th"][piexif.ImageIFD.XResolution] == (300, 1)
    assert exif["0th"][piexif.ImageIFD.YResolution] == (300, 1)
    assert exif["0th"][piexif.ImageIFD.ResolutionUnit] == 2
    with Image.open(result_path) as res_img:
        dpi_val = res_img.info.get("dpi", (0, 0))
        assert int(round(dpi_val[0])) == 300
        assert int(round(dpi_val[1])) == 300
