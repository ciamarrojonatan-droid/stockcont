"""Tests for the Commercial Sales Potential Scorer and Portfolio Analytics."""

import pytest
from fastapi.testclient import TestClient

from src.analyzer.commercial_scorer import (
    COPY_SPACE_INDICATORS,
    NICHE_DEFINITIONS,
    evaluate_sales_potential,
    get_portfolio_sales_analytics,
)
from src.dashboard.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_evaluate_sales_potential_podium():
    item = {
        "filename": "stone-pedestal-cosmetic-display-clean-white.jpg",
        "title": "Minimalist stone pedestal podium for cosmetic product presentation with clean copy space",
        "keywords": "podium, pedestal, product display, mockup, cosmetics, clean background, copy space, ai generated, generative ai",
    }
    result = evaluate_sales_potential(item)
    assert result["niche_key"] == "podium"
    assert result["niche"] == "Podium & Product Mockup"
    assert result["has_copyspace"] is True
    assert result["sales_score"] >= 80.0
    assert result["sales_tier_key"] in {"tier_s", "tier_a"}
    assert len(result["insights"]) >= 1


def test_evaluate_sales_potential_finance():
    item = {
        "filename": "candlestick-chart-financial-growth-trading.jpg",
        "title": "Stock market trading candlestick chart showing investment growth and economic forecast",
        "keywords": "trading, finance, candlestick, stock market, investment, growth, analytics, ai generated",
    }
    result = evaluate_sales_potential(item)
    assert result["niche_key"] == "finance"
    assert "Fintech" in result["buyer_intent"]
    assert result["sales_score"] >= 75.0


def test_evaluate_sales_potential_biotech():
    item = {
        "filename": "laboratory-pipetting-cleanroom-dna.jpg",
        "title": "Biotechnology cleanroom researcher pipetting chemical liquid for scientific dna testing",
        "keywords": "biotech, laboratory, cleanroom, pipetting, science, dna, pharma, ai generated",
    }
    result = evaluate_sales_potential(item)
    assert result["niche_key"] == "biotech"
    assert "Farmacêutica" in result["buyer_intent"]
    assert result["sales_score"] >= 75.0


def test_evaluate_sales_potential_tech_space():
    item = {
        "filename": "futuristic-astronaut-quantum-robotics.jpg",
        "title": "Futuristic astronaut in deep space with neural network interface and quantum robotics",
        "keywords": "astronaut, space, robot, artificial intelligence, quantum, futuristic, technology, ai generated",
    }
    result = evaluate_sales_potential(item)
    assert result["niche_key"] == "tech_space"
    assert "Startups" in result["buyer_intent"]


def test_evaluate_sales_potential_empty_metadata():
    item = {"filename": "unknown_asset.jpg"}
    result = evaluate_sales_potential(item)
    assert result["sales_score"] > 0
    assert result["niche_key"] == "abstract"
    assert isinstance(result["insights"], list)


def test_portfolio_sales_analytics_empty():
    analytics = get_portfolio_sales_analytics([])
    assert analytics["total_images"] == 0
    assert analytics["average_score"] == 0.0
    assert analytics["copyspace_count"] == 0
    assert analytics["tiers"]["tier_s"] == 0


def test_portfolio_sales_analytics_aggregation():
    sample_images = [
        {
            "filename": "img1.jpg",
            "title": "Podium",
            "sales_score": 95.0,
            "sales_tier": "Tier S",
            "sales_tier_key": "tier_s",
            "niche_key": "podium",
            "has_copyspace": True,
            "insights": ["High demand"],
        },
        {
            "filename": "img2.jpg",
            "title": "Finance",
            "sales_score": 85.0,
            "sales_tier": "Tier A",
            "sales_tier_key": "tier_a",
            "niche_key": "finance",
            "has_copyspace": False,
            "insights": ["High RPM"],
        },
    ]
    analytics = get_portfolio_sales_analytics(sample_images)
    assert analytics["total_images"] == 2
    assert analytics["average_score"] == 90.0
    assert analytics["copyspace_count"] == 1
    assert analytics["copyspace_percentage"] == 50.0
    assert analytics["tiers"]["tier_s"] == 1
    assert analytics["tiers"]["tier_a"] == 1
    assert len(analytics["top_performers"]) == 2
    assert analytics["top_performers"][0]["filename"] == "img1.jpg"


# ── API Endpoints Tests ─────────────────────────────────

def test_api_images_sales_score_and_sorting(client):
    response = client.get("/api/images?sort=sales_score")
    assert response.status_code == 200
    data = response.json()
    assert "images" in data
    assert data["total"] > 0
    images = data["images"]
    first = images[0]
    assert "sales_score" in first
    assert "sales_tier" in first
    assert "niche" in first
    assert "has_copyspace" in first

    # Verify descending sort
    scores = [img["sales_score"] for img in images]
    assert scores == sorted(scores, reverse=True)


def test_api_images_filtering_tier(client):
    response = client.get("/api/images?tier=tier_s")
    assert response.status_code == 200
    data = response.json()
    assert all(i["sales_tier_key"] == "tier_s" for i in data["images"])


def test_api_images_filtering_niche(client):
    response = client.get("/api/images?niche=biotech")
    assert response.status_code == 200
    data = response.json()
    assert all(i["niche_key"] == "biotech" for i in data["images"])


def test_api_images_filtering_copyspace(client):
    response = client.get("/api/images?copyspace=true")
    assert response.status_code == 200
    data = response.json()
    assert all(i["has_copyspace"] is True for i in data["images"])


def test_api_images_analytics_endpoint(client):
    response = client.get("/api/images/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "total_images" in data
    assert "average_score" in data
    assert "tiers" in data
    assert "niches" in data
    assert "top_performers" in data
    assert data["total_images"] > 0
