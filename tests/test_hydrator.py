"""Unit tests for Raw Reference Hydrator (src/scraper/hydrator.py)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.scraper.hydrator import hydrate_raw_references


@pytest.fixture
def sample_trends_file(tmp_path):
    """Create a temporary trends.json file with diverse test entries."""
    trends_path = tmp_path / "trends.json"
    data = [
        {
            "id": "item_1",
            "title": "Corporate Office",
            "original_url": "https://example.com/item_1.jpg",
            "local_path": "data/raw/images/item_1.jpg"
        },
        {
            "id": "item_2",
            "title": "Minimalist Desk",
            "thumbnail_url": "https://example.com/item_2.jpg",
            "local_path": "data/raw/images/item_2.jpg"
        },
        {
            "id": "item_no_url",
            "title": "No URL item",
            "local_path": "data/raw/images/item_no_url.jpg"
        }
    ]
    with open(trends_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return trends_path


def test_hydrate_already_present(sample_trends_file, tmp_path):
    """If all images already exist, no network download should occur."""
    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Pre-create image files
    (images_dir / "item_1.jpg").write_bytes(b"fake_jpg_data_1")
    (images_dir / "item_2.jpg").write_bytes(b"fake_jpg_data_2")

    with patch("httpx.Client.get") as mock_get:
        stats = hydrate_raw_references(
            trends_file=sample_trends_file,
            target_dir=images_dir,
            force=False
        )

        assert stats["total"] == 3
        assert stats["already_present"] == 2
        assert stats["downloaded"] == 0
        assert stats["failed"] == 1  # item_no_url has no URL and no file
        mock_get.assert_not_called()


def test_hydrate_missing_concurrent(sample_trends_file, tmp_path):
    """Missing images should be downloaded concurrently and saved to target_dir."""
    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.content = b"downloaded_binary_image_content"
        resp.raise_for_status = MagicMock()
        return resp

    with patch("httpx.Client.get", side_effect=mock_get):
        stats = hydrate_raw_references(
            trends_file=sample_trends_file,
            target_dir=images_dir,
            max_workers=2
        )

        assert stats["total"] == 3
        assert stats["downloaded"] == 2
        assert stats["already_present"] == 0
        assert stats["failed"] == 1  # item_no_url

        assert (images_dir / "item_1.jpg").is_file()
        assert (images_dir / "item_2.jpg").is_file()
        assert (images_dir / "item_1.jpg").read_bytes() == b"downloaded_binary_image_content"


def test_hydrate_network_error_resilience(sample_trends_file, tmp_path):
    """Network failures (404/500/timeout) should be logged without crashing."""
    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    def mock_get_fail(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 404
        import httpx
        raise httpx.HTTPStatusError("Not Found", request=MagicMock(), response=resp)

    with patch("httpx.Client.get", side_effect=mock_get_fail):
        stats = hydrate_raw_references(
            trends_file=sample_trends_file,
            target_dir=images_dir
        )

        assert stats["total"] == 3
        assert stats["downloaded"] == 0
        assert stats["failed"] == 3  # All 3 failed (2 network, 1 missing url)


def test_hydrate_empty_or_missing_trends(tmp_path):
    """Non-existent trends file should return zeroed stats gracefully."""
    missing_file = tmp_path / "does_not_exist.json"
    stats = hydrate_raw_references(trends_file=missing_file, target_dir=tmp_path / "images")
    assert stats["total"] == 0
    assert stats["downloaded"] == 0
