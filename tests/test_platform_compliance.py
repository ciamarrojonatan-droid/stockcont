import sys
from pathlib import Path
from PIL import Image
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.cataloger.platform_compliance import (
    PLATFORM_RULES,
    ComplianceResult,
    validate_image_compliance,
    validate_all_platforms,
    sanitize_metadata_for_agency,
    read_image_properties,
    ensure_image_dpi,
)


def test_platform_rules_registered():
    """Verify all 8 platforms are registered with their core rules."""
    expected = ["adobe", "freepik", "dreamstime", "123rf", "pond5", "vecteezy", "ingram", "alamy"]
    for exp in expected:
        assert exp in PLATFORM_RULES, f"Platform {exp} must be registered in PLATFORM_RULES"

    # Alamy must strictly forbid AI
    assert PLATFORM_RULES["alamy"].allows_ai is False
    assert "PROIBIÇÃO ESTRITA DE IA" in PLATFORM_RULES["alamy"].ai_policy_notes

    # Commercial microstock platforms must accept AI
    assert PLATFORM_RULES["adobe"].allows_ai is True
    assert PLATFORM_RULES["freepik"].allows_ai is True
    assert PLATFORM_RULES["dreamstime"].allows_ai is True


def test_alamy_ai_auto_block(tmp_path):
    """Verify Alamy anti-ban safety barrier automatically blocks AI-generated images."""
    img_path = tmp_path / "ai_test_image.jpg"
    Image.new("RGB", (3840, 2160), color=(100, 150, 200)).save(img_path, "JPEG", quality=95)

    result = validate_image_compliance(img_path, platform="alamy", is_ai_generated=True)

    assert result.is_compliant is False
    assert result.blocked is True
    assert "BLOQUEADO AUTOMATICAMENTE" in result.block_reason
    assert "Alamy proíbe estritamente qualquer imagem gerada por IA" in result.block_reason


def test_adobe_compliance_success(tmp_path):
    """Verify 4K compliant image passes Adobe Stock validation."""
    img_path = tmp_path / "compliant_4k.jpg"
    # 3840 x 2160 = 8.29 MP (well above Adobe's 4.0 MP minimum)
    Image.new("RGB", (3840, 2160), color=(50, 100, 150)).save(img_path, "JPEG", quality=95)

    override = {
        "title": "Modern minimalist workspace with laptop and coffee cup",
        "description": "Generative AI illustration. Modern minimalist workspace with laptop and coffee cup.",
        "keywords": ["workspace", "laptop", "office", "minimalist", "generative ai", "ai generated", "digital art", "illustration"]
    }

    result = validate_image_compliance(
        img_path,
        platform="adobe",
        is_ai_generated=True,
        metadata_override=override
    )

    assert result.is_compliant is True
    assert result.blocked is False
    assert len(result.errors) == 0


def test_freepik_longest_side_and_title_limit(tmp_path):
    """Verify Freepik requires >= 2000px longest side and max 100 char title."""
    # Too small (1800x1200, longest side < 2000)
    small_img = tmp_path / "small_image.jpg"
    Image.new("RGB", (1800, 1200), color=(10, 20, 30)).save(small_img, "JPEG")

    result_small = validate_image_compliance(small_img, platform="freepik", is_ai_generated=True)
    assert result_small.is_compliant is False
    assert any("Lado maior" in err for err in result_small.errors)

    # Valid dimensions (2500x1600) but title > 100 characters
    valid_img = tmp_path / "valid_size.jpg"
    Image.new("RGB", (2500, 1600), color=(10, 20, 30)).save(valid_img, "JPEG")

    long_title = "This is an excessively long title designed specifically to exceed the strict one hundred character limit set by Freepik for stock image submissions"
    result_long_title = validate_image_compliance(
        valid_img,
        platform="freepik",
        is_ai_generated=True,
        metadata_override={"title": long_title, "keywords": ["office", "desk", "business", "work", "generative ai"]}
    )
    assert result_long_title.is_compliant is False
    assert any("Título excede limite" in err for err in result_long_title.errors)


def test_dreamstime_caption_warning(tmp_path):
    """Verify Dreamstime checks for 'Generative AI illustration.' caption prefix."""
    img_path = tmp_path / "dt_image.jpg"
    Image.new("RGB", (3000, 2000), color=(20, 40, 60)).save(img_path, "JPEG")

    override = {
        "title": "Futuristic skyline at dusk",
        "description": "A beautiful view of a futuristic city without standard AI disclosure prefix.",
        "keywords": ["city", "skyline", "future", "generative ai", "illustration"]
    }

    result = validate_image_compliance(
        img_path,
        platform="dreamstime",
        is_ai_generated=True,
        metadata_override=override
    )

    assert any("a descrição deve iniciar com 'Generative AI illustration.'" in w for w in result.warnings)


def test_sanitize_metadata_for_agency():
    """Verify metadata sanitization adapts titles and keywords per agency."""
    long_title = "A incredibly detailed and magnificent view of an astronaut exploring a Martian desert with futuristic rover"
    raw_kws = ["space", "astronaut", "mars", "AI Generated", "Sci-Fi", "adventure"]

    # For Freepik: title must be <= 100 characters
    fp_meta = sanitize_metadata_for_agency(
        title=long_title,
        description="Generative AI illustration. Martian exploration.",
        keywords=raw_kws,
        platform="freepik",
        is_ai_generated=True
    )
    assert len(fp_meta["title"]) <= 100
    assert "generative ai" in [k.lower() for k in fp_meta["keywords"]]

    # For Alamy: all AI keywords must be removed
    alamy_meta = sanitize_metadata_for_agency(
        title=long_title,
        description="Generative AI illustration. Martian exploration.",
        keywords=raw_kws,
        platform="alamy",
        is_ai_generated=False
    )
    alamy_kws_lower = [k.lower() for k in alamy_meta["keywords"]]
    assert "ai generated" not in alamy_kws_lower
    assert "space" in alamy_kws_lower


def test_validate_all_platforms(tmp_path):
    """Verify validate_all_platforms evaluates all 8 agencies in parallel."""
    img_path = tmp_path / "eval_all.jpg"
    Image.new("RGB", (3840, 2160), color=(100, 100, 100)).save(img_path, "JPEG")

    reports = validate_all_platforms(img_path, is_ai_generated=True)
    assert len(reports) == 8
    assert "adobe" in reports
    assert "freepik" in reports
    assert "dreamstime" in reports
    assert "alamy" in reports

    # Alamy must be blocked, others allowed
    assert reports["alamy"].blocked is True
    assert reports["adobe"].blocked is False


def test_ensure_image_dpi(tmp_path):
    """Verify ensure_image_dpi updates JFIF and EXIF density to 300 DPI."""
    import piexif

    img_path = tmp_path / "low_dpi.jpg"
    Image.new("RGB", (1000, 1000), color=(50, 50, 50)).save(img_path, "JPEG", dpi=(72, 72))

    # Before update
    props_before = read_image_properties(img_path)
    assert props_before["dpi_x"] == 72
    assert props_before["dpi_y"] == 72

    # Enforce 300 DPI
    success = ensure_image_dpi(img_path, target_dpi=300)
    assert success is True

    # After update: PIL check
    with Image.open(img_path) as img_read:
        dpi = img_read.info.get("dpi")
        assert int(round(dpi[0])) == 300
        assert int(round(dpi[1])) == 300

    # After update: EXIF check
    exif = piexif.load(str(img_path))
    assert exif["0th"][piexif.ImageIFD.XResolution] == (300, 1)
    assert exif["0th"][piexif.ImageIFD.YResolution] == (300, 1)
    assert exif["0th"][piexif.ImageIFD.ResolutionUnit] == 2

    # After update: read_image_properties check
    props_after = read_image_properties(img_path)
    assert props_after["dpi_x"] == 300
    assert props_after["dpi_y"] == 300


def test_dpi_validation_warning(tmp_path):
    """Verify validate_image_compliance warns if image DPI is below 300."""
    img_path = tmp_path / "warn_dpi.jpg"
    Image.new("RGB", (3840, 2160), color=(100, 100, 100)).save(img_path, "JPEG", dpi=(72, 72))

    res = validate_image_compliance(img_path, platform="adobe", is_ai_generated=True)
    assert any("Densidade de impressão (72x72 DPI) abaixo do padrão comercial de 300 DPI" in w for w in res.warnings)
