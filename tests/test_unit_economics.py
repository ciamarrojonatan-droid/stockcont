import pytest
from fastapi.testclient import TestClient

from src.analyzer.commercial_scorer import NICHE_DEFINITIONS
from src.analyzer.unit_economics import UnitEconomicsCalculator
from src.dashboard.app import app


def test_calculate_asset_unit_cost_breakdown():
    calc = UnitEconomicsCalculator()
    img_cost = calc.calculate_asset_unit_cost(asset_type="image", include_upscale=True)
    vid_cost = calc.calculate_asset_unit_cost(asset_type="video", include_upscale=False)

    assert img_cost["total_cost_usd"] > 0
    assert img_cost["gemini_usd"] >= 0
    assert img_cost["gpu_usd"] > 0
    assert vid_cost["total_cost_usd"] > img_cost["total_cost_usd"]


def test_calculate_niche_roi_covers_all_scorer_niches():
    calc = UnitEconomicsCalculator()
    ranked = calc.recommend_priority_niches(asset_type="image", batch_size=210, expected_downloads_per_asset=2.0)

    assert len(ranked) == len(NICHE_DEFINITIONS)
    returned_niches = {row["niche_id"] for row in ranked}
    assert returned_niches == set(NICHE_DEFINITIONS.keys())
    # Must be sorted strictly descending by roi_pct
    roi_values = [row["roi_pct"] for row in ranked]
    assert roi_values == sorted(roi_values, reverse=True)
    for row in ranked:
        assert "projected_gross_usd" in row
        assert "batch_cost_usd" in row
        assert "projected_net_usd" in row
        assert "breakeven_downloads_per_asset" in row


def test_calculate_niche_roi_rejects_unknown_niche():
    calc = UnitEconomicsCalculator()
    with pytest.raises(ValueError):
        calc.calculate_niche_roi("unknown_niche_xyz")


def test_dashboard_unit_economics_endpoint():
    client = TestClient(app)
    resp = client.get("/api/v1/analytics/unit-economics?batch_size=100&expected_downloads=1.5")
    assert resp.status_code == 200
    data = resp.json()
    assert "niches" in data
    assert len(data["niches"]) == len(NICHE_DEFINITIONS)
    assert data["batch_size"] == 100
