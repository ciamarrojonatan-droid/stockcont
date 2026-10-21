"""Seasonal Calendar Engine for Microstock Demand Forecasting.

Calculates the optimal commercial submission window (D+60 to D+90 days)
based on global advertising agency buying cycles, ensuring assets are indexed
and ranked precisely when enterprise buyers begin high-volume acquisition.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SeasonalNiche:
    """Represents a specific high-demand micro-niche for a commercial window."""
    name: str
    query: str
    target_buyers: List[str]
    rationale: str
    recommended_tags: List[str] = field(default_factory=list)
    suggested_layout: str = "left_third_copy_space"


@dataclass
class SeasonalWindow:
    """Represents an active seasonal buying cycle."""
    month_target: int
    quarter_target: str
    macro_theme: str
    lead_time_days: int
    niches: List[SeasonalNiche]


# ── Global Commercial Advertising Calendar (D+60 to D+90 Projection) ─────────
# When enterprise and ad agencies plan campaigns, they procure stock assets 2-3 months early.

SEASONAL_CALENDAR: Dict[int, SeasonalWindow] = {
    # ── Target Window: January - February (Procured in Oct - Nov) ────────────
    1: SeasonalWindow(
        month_target=1,
        quarter_target="Q1",
        macro_theme="Annual Strategy, FinTech Reboot, Health & Wellness Resolutions",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="FinTech High-Frequency Analytics & Tax Prep",
                query="fintech analytics dashboard modern workstation",
                target_buyers=["Banking Apps", "SaaS Dashboards", "Financial Advisory"],
                rationale="Enterprises and tax software launch annual financial portals in early Q1.",
                recommended_tags=["finance", "fintech", "analytics", "tax", "dashboard", "data visualization", "workspace"],
                suggested_layout="left_third_copy_space"
            ),
            SeasonalNiche(
                name="Biohacking & Precision Longevity Clinic",
                query="biotech longevity laboratory precision medicine",
                target_buyers=["HealthTech Startups", "Pharma", "Wellness Portals"],
                rationale="Post-holiday wellness boom shifts corporate budgets to preventive health campaigns.",
                recommended_tags=["healthtech", "biotechnology", "longevity", "laboratory", "medicine", "clinical"],
                suggested_layout="right_third_copy_space"
            ),
            SeasonalNiche(
                name="Eco-Conscious Corporate Architecture & ESG",
                query="sustainable architecture modern green office atrium",
                target_buyers=["Corporate ESG Reports", "Green Energy", "Real Estate"],
                rationale="Annual ESG and sustainability corporate reports published in January and February.",
                recommended_tags=["sustainable", "green office", "esg", "biophilic architecture", "clean energy"],
                suggested_layout="hero_banner_top_space"
            ),
        ]
    ),
    2: SeasonalWindow(
        month_target=2,
        quarter_target="Q1",
        macro_theme="B2B Supply Chain, Cloud Infrastructure, Agile Remote Teams",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="Autonomous Robotics Logistics & Warehouse",
                query="automated warehouse logistics robotic arm inspection",
                target_buyers=["E-commerce Logistics", "Automation Providers", "B2B Tech"],
                rationale="Supply chain modernization initiatives peak in Q1 planning.",
                recommended_tags=["warehouse", "robotics", "automation", "logistics", "supply chain", "industry 4.0"],
                suggested_layout="left_third_copy_space"
            ),
            SeasonalNiche(
                name="Cloud Cybersecurity Operations Center (SOC)",
                query="cybersecurity operations center modern network telemetry",
                target_buyers=["Enterprise Security", "DevOps Platforms", "Cloud Providers"],
                rationale="Critical high-ticket category with consistent year-round B2B enterprise demand.",
                recommended_tags=["cybersecurity", "soc", "network", "data center", "telemetry", "security"],
                suggested_layout="hero_banner_top_space"
            ),
        ]
    ),
    # ── Target Window: March - April (Procured in Dec - Jan) ──────────────────
    3: SeasonalWindow(
        month_target=3,
        quarter_target="Q1/Q2",
        macro_theme="Spring Corporate Renewal, Diversity in Tech, Global Logistics",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="Diverse Executive Boardroom Decision Making",
                query="inclusive corporate leadership modern boardroom strategy",
                target_buyers=["Corporate Websites", "Consulting Firms", "HR Campaigns"],
                rationale="High ongoing demand for authentic, non-cliché corporate diversity.",
                recommended_tags=["leadership", "boardroom", "corporate", "inclusion", "strategy", "executive"],
                suggested_layout="right_third_copy_space"
            ),
            SeasonalNiche(
                name="Smart Agriculture & Agritech Drone Telemetry",
                query="precision agriculture drone telemetry crop monitoring",
                target_buyers=["Agritech Startups", "Food Security Initiatives", "Green Tech"],
                rationale="Spring planting season campaigns require modern high-tech farming imagery.",
                recommended_tags=["agritech", "drone", "smart farming", "agriculture", "food security"],
                suggested_layout="left_third_copy_space"
            ),
        ]
    ),
    4: SeasonalWindow(
        month_target=4,
        quarter_target="Q2",
        macro_theme="Earth Day, Biophilic Design, Clean Mobility & Renewable Grid",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="Next-Gen Solid State Battery & EV Charging Hub",
                query="electric vehicle modern charging station renewable energy",
                target_buyers=["Clean Tech", "Automotive", "Smart Cities"],
                rationale="Earth Day (April 22) advertising campaigns start massive asset acquisition in February.",
                recommended_tags=["electric vehicle", "clean energy", "ev charging", "solar grid", "sustainability"],
                suggested_layout="hero_banner_top_space"
            ),
            SeasonalNiche(
                name="Biophilic Interior Design & Home Office Ergonomics",
                query="minimalist biophilic home office natural light wood",
                target_buyers=["Interior Design Brands", "Remote SaaS", "Ergonomics"],
                rationale="Spring home improvement and ergonomic wellness campaigns.",
                recommended_tags=["biophilic", "home office", "interior design", "natural light", "minimalist"],
                suggested_layout="left_third_copy_space"
            ),
        ]
    ),
    # ── Target Window: May - June (Procured in Feb - Mar) ────────────────────
    5: SeasonalWindow(
        month_target=5,
        quarter_target="Q2",
        macro_theme="Digital Nomad Productivity, Global Travel & Leisure Tech",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="Digital Nomad High-Tech Workstation Waterfront",
                query="remote worker modern laptop ocean view terrace daylight",
                target_buyers=["FinTech Nomad Cards", "Remote Work SaaS", "Travel Insurance"],
                rationale="Summer digital nomad campaigns kick off in late spring.",
                recommended_tags=["digital nomad", "remote work", "laptop", "coastal", "lifestyle", "entrepreneur"],
                suggested_layout="right_third_copy_space"
            ),
        ]
    ),
    6: SeasonalWindow(
        month_target=6,
        quarter_target="Q2/Q3",
        macro_theme="Summer Leisure, Mid-Year Performance Reviews, AI Dev Summits",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="Generative AI Neural Architecture Visualization",
                query="neural network quantum computing abstract light beams",
                target_buyers=["AI Infrastructure", "Tech Conferences", "SaaS Backends"],
                rationale="Developer conferences and mid-year tech launches heavily license abstract AI visuals.",
                recommended_tags=["artificial intelligence", "neural network", "quantum computing", "data science"],
                suggested_layout="hero_banner_top_space"
            ),
        ]
    ),
    # ── Target Window: July - August (Procured in Apr - May) ─────────────────
    7: SeasonalWindow(
        month_target=7,
        quarter_target="Q3",
        macro_theme="Back-to-School B2B, Autumn Retail Previews, Logistics Prep",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="Modern STEM Classroom & Augmented Reality Education",
                query="futuristic stem education augmented reality classroom",
                target_buyers=["EdTech Companies", "Universities", "E-learning Apps"],
                rationale="Back-to-school marketing by major tech brands begins in July.",
                recommended_tags=["edtech", "stem", "education", "augmented reality", "learning", "classroom"],
                suggested_layout="left_third_copy_space"
            ),
        ]
    ),
    # ── Target Window: September - October (Procured in Jun - Jul) ───────────
    9: SeasonalWindow(
        month_target=9,
        quarter_target="Q3/Q4",
        macro_theme="Autumn Seasonal Retail, Q4 Budget Planning, Cyber Security Awareness",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="Cybersecurity Awareness Month & Threat Defense",
                query="biometric authentication server room cybersecurity lock",
                target_buyers=["Enterprise Security", "Insurance", "SaaS"],
                rationale="October is National Cyber Security Awareness Month worldwide.",
                recommended_tags=["cybersecurity", "biometrics", "data protection", "threat detection", "encryption"],
                suggested_layout="right_third_copy_space"
            ),
        ]
    ),
    # ── Target Window: November - December (Procured in Aug - Sep) ───────────
    11: SeasonalWindow(
        month_target=11,
        quarter_target="Q4",
        macro_theme="Black Friday Logistics, Cyber Monday, Retail Tech Boom",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="High-Volume E-Commerce Fulfillment & Mobile Checkout",
                query="smartphone contactless payment delivery logistics warehouse",
                target_buyers=["FinTech", "Payment Gateways", "Retailers"],
                rationale="Peak shopping season advertising accounts for 40% of annual ad spend.",
                recommended_tags=["ecommerce", "contactless payment", "black friday", "delivery", "retail"],
                suggested_layout="left_third_copy_space"
            ),
        ]
    ),
    12: SeasonalWindow(
        month_target=12,
        quarter_target="Q4",
        macro_theme="Holiday Celebrations, Year-End Corporate Awards & 2027 Vision",
        lead_time_days=75,
        niches=[
            SeasonalNiche(
                name="Elegant Corporate Gala & Year-End Achievement Celebration",
                query="modern corporate celebration toast business team champagne bokeh",
                target_buyers=["Corporate Event Planners", "HR Agencies", "Financial Firms"],
                rationale="Holiday corporate greetings and annual reports require premium celebration imagery.",
                recommended_tags=["celebration", "corporate achievement", "gala", "year end", "success", "team"],
                suggested_layout="left_third_copy_space"
            ),
            SeasonalNiche(
                name="New Year Strategic Roadmap & Futuristic Forecasting",
                query="business executives looking at holographic roadmap horizon sunrise",
                target_buyers=["Consulting Firms", "Tech Visionaries", "Annual Reports"],
                rationale="New Year strategic outlook campaigns require visionary, forward-looking visuals.",
                recommended_tags=["vision", "future", "roadmap", "strategy", "new year", "sunrise", "leadership"],
                suggested_layout="hero_banner_top_space"
            ),
        ]
    )
}


def get_target_procurement_window(reference_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Calculate the target commercial season based on D+75 days lead time.
    
    Args:
        reference_date: Current date (defaults to UTC now).
        
    Returns:
        Dictionary containing current date, target procurement date, target month, and recommended niches.
    """
    now = reference_date or datetime.now(timezone.utc)
    target_date = now + timedelta(days=75)
    target_month = target_date.month

    # Fallback to closest configured seasonal window
    seasonal_win = SEASONAL_CALENDAR.get(target_month)
    if not seasonal_win:
        # Pick the nearest available month
        available_months = sorted(SEASONAL_CALENDAR.keys())
        nearest_month = min(available_months, key=lambda m: abs(m - target_month))
        seasonal_win = SEASONAL_CALENDAR[nearest_month]

    return {
        "current_date": now.strftime("%Y-%m-%d"),
        "target_procurement_date": target_date.strftime("%Y-%m-%d"),
        "target_month": seasonal_win.month_target,
        "target_quarter": seasonal_win.quarter_target,
        "macro_theme": seasonal_win.macro_theme,
        "lead_time_days": seasonal_win.lead_time_days,
        "recommended_niches": [
            {
                "name": n.name,
                "query": n.query,
                "target_buyers": n.target_buyers,
                "rationale": n.rationale,
                "recommended_tags": n.recommended_tags,
                "suggested_layout": n.suggested_layout,
            }
            for n in seasonal_win.niches
        ],
    }
