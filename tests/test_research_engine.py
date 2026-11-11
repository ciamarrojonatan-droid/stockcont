import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer.seasonal_radar import (
    fetch_live_signal_boosters,
    get_merged_seasonal_opportunities,
)
from src.video.research_engine import (
    PublicDomainResearchEngine,
    is_public_domain_license,
)


def test_is_public_domain_license_strict_filter():
    assert is_public_domain_license("Public domain") is True
    assert is_public_domain_license("CC0 1.0 Universal") is True
    assert is_public_domain_license("PD-USGov-NASA") is True
    assert is_public_domain_license("All rights reserved") is False
    assert is_public_domain_license("CC-BY-NC-4.0") is False
    assert is_public_domain_license("") is False


def test_research_engine_builds_fact_pack_and_filters_licenses(tmp_path):
    cache_dir = tmp_path / "cache"
    out_dir = tmp_path / "dossiers"
    local_dir = tmp_path / "local"
    engine = PublicDomainResearchEngine(
        cache_dir=cache_dir,
        output_dir=out_dir,
        local_dossiers_dir=local_dir,
    )

    def _mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "wikipedia.org/api/rest_v1/page/summary" in url:
            resp.json.return_value = {
                "title": "Operation Paperclip",
                "extract": "Operation Paperclip was a secret US intelligence program recruiting German scientists after 1945.",
                "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Operation_Paperclip"}},
            }
        elif "commons.wikimedia.org/w/api.php" in url:
            resp.json.return_value = {
                "query": {
                    "pages": {
                        "1": {
                            "title": "File:V2_rocket_pd.jpg",
                            "imageinfo": [{
                                "url": "https://upload.wikimedia.org/v2.jpg",
                                "extmetadata": {"LicenseShortName": {"value": "Public domain"}},
                            }],
                        },
                        "2": {
                            "title": "File:Restricted_photo.jpg",
                            "imageinfo": [{
                                "url": "https://upload.wikimedia.org/restricted.jpg",
                                "extmetadata": {"LicenseShortName": {"value": "CC-BY-NC-SA 4.0"}},
                            }],
                        },
                    }
                }
            }
        elif "archive.org/advancedsearch.php" in url:
            resp.json.return_value = {
                "response": {
                    "docs": [{
                        "identifier": "paperclip_reel_1945",
                        "title": "Declassified Rocket Reel 1945",
                        "licenseurl": "http://creativecommons.org/publicdomain/mark/1.0/",
                    }]
                }
            }
        elif "images-api.nasa.gov/search" in url:
            resp.json.return_value = {
                "collection": {
                    "items": [{
                        "data": [{"nasa_id": "MSFC-6521", "title": "Von Braun Saturn V Blueprint", "description": "PD-USGov-NASA archive"}],
                        "links": [{"href": "https://images-assets.nasa.gov/MSFC-6521.jpg", "render": "image"}],
                    }]
                }
            }
        return resp

    with patch("src.video.research_engine.httpx.get", side_effect=_mock_get):
        pack = engine.build_dossier("Operation Paperclip", sources=("wikipedia", "wikimedia", "internet_archive", "nasa"))

    assert pack.topic == "Operation Paperclip"
    assert len(pack.facts) >= 1
    assert any("1945" in f.statement for f in pack.facts)
    # Restricted CC-BY-NC-SA media must be excluded!
    media_urls = [m.url for m in pack.media_assets]
    assert "https://upload.wikimedia.org/v2.jpg" in media_urls
    assert "https://upload.wikimedia.org/restricted.jpg" not in media_urls
    assert any("archive.org" in m.url for m in pack.media_assets)
    assert any("nasa.gov" in m.url for m in pack.media_assets)

    dossier_file = out_dir / "operation_paperclip.json"
    assert dossier_file.exists()
    persisted = json.loads(dossier_file.read_text(encoding="utf-8"))
    assert persisted["topic"] == "Operation Paperclip"


def test_research_engine_offline_falls_back_to_local_dossiers(tmp_path):
    local_dir = tmp_path / "local"
    local_dir.mkdir(parents=True)
    (local_dir / "operation_mincemeat.txt").write_text(
        "Operation Mincemeat was a 1943 British deception plan in World War II.",
        encoding="utf-8",
    )

    engine = PublicDomainResearchEngine(
        cache_dir=tmp_path / "cache",
        output_dir=tmp_path / "out",
        local_dossiers_dir=local_dir,
    )
    with patch("src.video.research_engine.httpx.get", side_effect=OSError("Offline sandbox")):
        pack = engine.build_dossier("Operation Mincemeat")

    assert pack.used_local_fallback is True
    assert any("1943" in f.statement for f in pack.facts)


def test_seasonal_radar_live_signals_and_graceful_offline_fallback():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "hits": [
            {"title": "Photonic AI Interconnect Chips 2026", "points": 320, "objectID": "hn1"},
            {"title": "Microbial Bioreactor Automation", "points": 185, "objectID": "hn2"},
        ]
    }
    with patch("src.analyzer.seasonal_radar.httpx.get", return_value=mock_resp):
        signals = fetch_live_signal_boosters(max_items=2)
        assert len(signals) == 2
        merged = get_merged_seasonal_opportunities(include_live_signals=True)
        assert "recommended_niches" in merged
        assert len(merged["live_signal_boosters"]) == 2

    with patch("src.analyzer.seasonal_radar.httpx.get", side_effect=RuntimeError("DNS failed")):
        merged_offline = get_merged_seasonal_opportunities(include_live_signals=True)
        assert "recommended_niches" in merged_offline
        assert merged_offline["live_signal_boosters"] == []
