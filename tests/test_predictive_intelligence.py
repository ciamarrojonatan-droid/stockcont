import sys
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.analyzer.seasonal_radar import get_target_procurement_window, SEASONAL_CALENDAR
from src.analyzer.saturation_index import calculate_saturation_index, MarketZone
from src.analyzer.director import SYSTEM_PROMPT
from src.dashboard.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_seasonal_calendar_d75_calculation():
    """Verify that seasonal calendar projects D+75 days lead time."""
    ref_date = datetime(2026, 10, 21, tzinfo=timezone.utc)
    forecast = get_target_procurement_window(reference_date=ref_date)

    assert forecast["current_date"] == "2026-10-21"
    assert "target_procurement_date" in forecast
    assert forecast["lead_time_days"] == 75
    assert len(forecast["recommended_niches"]) > 0

    for niche in forecast["recommended_niches"]:
        assert "name" in niche
        assert "query" in niche
        assert "target_buyers" in niche
        assert "suggested_layout" in niche
        assert isinstance(niche["target_buyers"], list)
        assert len(niche["target_buyers"]) > 0


def test_saturation_index_classifications():
    """Verify mathematical calculation and zone categorization of saturation index."""
    # 1. Blue ocean: high downloads, low total indexed competition
    blue_report = calculate_saturation_index(
        query="precision agriculture drone telemetry",
        average_downloads=1200.0,
        total_indexed_assets=15000,
    )
    assert blue_report.market_zone == MarketZone.BLUE_OCEAN
    assert "Blue Ocean" in blue_report.verdict
    assert blue_report.saturation_score > 0.025

    # 2. Moderate market: healthy velocity, moderate competition
    mod_report = calculate_saturation_index(
        query="corporate team meeting",
        average_downloads=350.0,
        total_indexed_assets=45000,
    )
    assert mod_report.market_zone in [MarketZone.MODERATE, MarketZone.BLUE_OCEAN]

    # 3. Red ocean: saturated market
    red_report = calculate_saturation_index(
        query="generic handshake",
        average_downloads=10.0,
        total_indexed_assets=800000,
    )
    assert red_report.market_zone == MarketZone.RED_OCEAN
    assert "Red Ocean" in red_report.verdict
    assert red_report.saturation_score < 0.005


def test_director_v3_prompt_mandate_and_specifications():
    """Ensure System Prompt v3.0 enforces 700-1000 words and adaptive copy-space."""
    assert "v3.0" in SYSTEM_PROMPT
    assert "700" in SYSTEM_PROMPT
    assert "1,000" in SYSTEM_PROMPT or "1000" in SYSTEM_PROMPT
    assert "copy-space" in SYSTEM_PROMPT.lower() or "copy_space" in SYSTEM_PROMPT.lower()
    assert "left_third_copy_space" in SYSTEM_PROMPT
    assert "hero_banner_top_space" in SYSTEM_PROMPT


def test_api_seasonal_endpoint(client):
    """Test dashboard endpoint for dynamic seasonal forecast."""
    response = client.get("/api/seasonal")
    assert response.status_code == 200
    data = response.json()
    assert "target_procurement_date" in data
    assert "recommended_niches" in data
    assert isinstance(data["recommended_niches"], list)
    assert len(data["recommended_niches"]) > 0


def test_api_saturation_endpoint(client):
    """Test dashboard endpoint for saturation calculation."""
    response = client.get("/api/saturation?query=fintech&downloads=500&indexed=10000")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "fintech"
    assert "market_zone" in data
    assert "saturation_score" in data
