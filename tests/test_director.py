"""Unit tests for Art Director v3.0 (src/analyzer/director.py)."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.analyzer.director import (
    load_trends,
    process_image,
    main as director_main
)


@pytest.fixture
def test_image(tmp_path):
    """Create a temporary test image."""
    img_path = tmp_path / "12345.jpg"
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img.save(img_path, "JPEG")
    return img_path


def test_process_image_with_local_path(tmp_path, test_image, monkeypatch):
    """Verify process_image resolves image using the standard 'local_path' key."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_api_key_123456789")

    mock_gemini_response = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "system_version": "3.0",
                        "analysis_metadata": {"reference_available": True},
                        "visual_dna": {"style": "Photorealistic"},
                        "derivative_prompts": [
                            {
                                "id": 1,
                                "concept": "FinTech Desk",
                                "prompt_data": {
                                    "final_prompt": "Cinematic 800 word prompt text"
                                }
                            }
                        ]
                    })
                }]
            }
        }]
    }

    item = {
        "id": "12345",
        "title": "FinTech Workspace",
        "local_path": str(test_image)
    }

    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_response
        mock_post.return_value = mock_resp

        result = process_image(item)
        assert result is not None
        assert result["source_id"] == "12345"
        assert len(result["generated_prompts"]) == 1
        prompt_item = result["generated_prompts"][0]
        assert prompt_item["prompt"] == "Cinematic 800 word prompt text"
        assert prompt_item["status"] == "pending"


def test_process_image_with_local_image_path(tmp_path, test_image, monkeypatch):
    """Verify backward compatibility when 'local_image_path' is provided."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_api_key_123456789")

    mock_gemini_response = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": "```json\n" + json.dumps({
                        "system_version": "3.0",
                        "derivative_prompts": [
                            {
                                "id": 1,
                                "concept": "Abstract AI",
                                "prompt_data": {
                                    "final_prompt": "Abstract tech visual essay"
                                }
                            }
                        ]
                    }) + "\n```"
                }]
            }
        }]
    }

    item = {
        "id": "12345",
        "title": "Abstract Concept",
        "local_image_path": str(test_image)
    }

    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_response
        mock_post.return_value = mock_resp

        result = process_image(item)
        assert result is not None
        assert result["source_id"] == "12345"
        prompt_item = result["generated_prompts"][0]
        assert prompt_item["prompt"] == "Abstract tech visual essay"


def test_process_image_missing_image_textual_fallback(monkeypatch):
    """Verify process_image falls back to text metadata when image file cannot be found."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_api_key_123456789")

    mock_gemini_response = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "system_version": "3.0",
                        "analysis_metadata": {"reference_available": False},
                        "visual_dna": {"style": "Photorealistic"},
                        "derivative_prompts": [
                            {
                                "id": 1,
                                "concept": "Fallback Text Desk",
                                "prompt_data": {
                                    "final_prompt": "Cinematic text fallback prompt essay"
                                }
                            }
                        ]
                    })
                }]
            }
        }]
    }

    item = {
        "id": "missing_item_99999",
        "title": "FinTech Future AI Workspace",
        "content_type": "photo",
        "contributor_name": "ProShooter",
        "keywords": ["ai", "fintech", "workspace"],
        "local_path": "data/raw/images/non_existent_99999.jpg"
    }

    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_response
        mock_post.return_value = mock_resp

        result = process_image(item)
        assert result is not None
        assert result["source_id"] == "missing_item_99999"
        assert result["analysis_metadata"]["reference_available"] is False
        assert len(result["generated_prompts"]) == 1
        assert result["generated_prompts"][0]["prompt"] == "Cinematic text fallback prompt essay"


def test_process_image_gemini_failure(monkeypatch):
    """Verify process_image returns None when Gemini API fails completely."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_api_key_123456789")
    item = {
        "id": "item_failing_gemini",
        "title": "Fail Item",
        "local_path": "data/raw/images/non_existent.jpg"
    }
    with patch("httpx.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        result = process_image(item)
        assert result is None

