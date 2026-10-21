"""Niche Saturation & Opportunity Scoring Index.

Calculates the ratio between commercial demand (average downloads from top sellers)
and indexed asset competition (total search results) to distinguish between:
  - 🟢 Blue Ocean: High demand, sparse competition (Prioritize production).
  - 🟡 Moderate: Healthy commercial velocity, requires strong visual differentiation.
  - 🔴 Red Ocean: Severe oversaturation, high risk of low asset visibility.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class MarketZone(str, Enum):
    BLUE_OCEAN = "blue_ocean"
    MODERATE = "moderate"
    RED_OCEAN = "red_ocean"


@dataclass
class SaturationReport:
    """Detailed market saturation assessment for a search keyword or niche."""
    query: str
    average_downloads: float
    total_indexed_assets: int
    saturation_score: float
    market_zone: MarketZone
    verdict: str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "average_downloads": round(self.average_downloads, 1),
            "total_indexed_assets": self.total_indexed_assets,
            "saturation_score": round(self.saturation_score, 5),
            "market_zone": self.market_zone.value,
            "verdict": self.verdict,
            "recommendation": self.recommendation,
        }


def calculate_saturation_index(
    query: str,
    average_downloads: float,
    total_indexed_assets: int,
) -> SaturationReport:
    """Calculate the Niche Saturation Index (Downloads / Total Assets).
    
    Args:
        query: Search term or niche name.
        average_downloads: Average lifetime downloads of the top-performing assets.
        total_indexed_assets: Total number of assets returned by the agency search engine.
        
    Returns:
        SaturationReport with numerical score and actionable recommendation.
    """
    safe_indexed = max(1, total_indexed_assets)
    # The saturation score measures downloads per competing asset
    score = average_downloads / safe_indexed

    # Benchmarks tuned for commercial microstock platforms:
    if score >= 0.025 or (average_downloads >= 500 and total_indexed_assets <= 25000):
        zone = MarketZone.BLUE_OCEAN
        verdict = "🟢 Blue Ocean (Mina de Ouro Comercial)"
        recommendation = (
            "Alta velocidade de vendas com concorrência moderada ou baixa. "
            "Prioridade máxima de produção com prompts focados em copy-space."
        )
    elif score >= 0.005 or (average_downloads >= 200 and total_indexed_assets <= 80000):
        zone = MarketZone.MODERATE
        verdict = "🟡 Competição Moderada (Mercado Ativo)"
        recommendation = (
            "Mercado com demanda saudável. Exige forte diferenciação estética, "
            "ângulos cinematográficos e enquadramentos concebidos para anúncios B2B."
        )
    else:
        zone = MarketZone.RED_OCEAN
        verdict = "🔴 Red Ocean (Mercado Saturado)"
        recommendation = (
            "Excesso massivo de ativos concorrentes para o volume de downloads. "
            "Recomenda-se refinar a busca para um micro-nicho mais específico ou sazonal."
        )

    return SaturationReport(
        query=query,
        average_downloads=average_downloads,
        total_indexed_assets=total_indexed_assets,
        saturation_score=score,
        market_zone=zone,
        verdict=verdict,
        recommendation=recommendation,
    )
