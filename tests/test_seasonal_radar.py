"""Unit tests for Seasonal Radar & live signal boosters."""

from unittest.mock import MagicMock, patch

from src.analyzer.seasonal_radar import (
    fetch_live_signal_boosters,
    get_merged_seasonal_opportunities,
)


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
