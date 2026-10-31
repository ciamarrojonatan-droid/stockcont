"""StockCont — Commercial Sales Potential Scorer & Portfolio Analytics.

Analisa e quantifica o potencial comercial de venda de imagens de microstock
baseando-se em:
1. Nicho comercial e demanda B2B (E-commerce Mockups, Fintech, Biotech, Tech/AI).
2. Usabilidade visual e Copy-Space (espaço negativo limpo para textos/logos/mockups).
3. Qualidade e completude de metadados SEO (50 tags IPTC, títulos comerciais otimizados).
4. Conformidade estrita com políticas de Inteligência Artificial.
"""

import re
from typing import Any, Dict, List, Optional


# Definição dos Nichos Comerciais e seus multiplicadores de mercado
NICHE_DEFINITIONS = {
    "podium": {
        "name": "Podium & Product Mockup",
        "keywords": [
            "podium", "pedestal", "product presentation", "mockup",
            "product display", "stage", "cosmetic display", "cylinder podium",
            "marble podium", "stone pedestal", "travertine", "minimalist display"
        ],
        "bonus": 26.0,
        "buyer_intent": "E-Commerce, Branding & Packaging Agencies",
        "primary_insight": "Alta demanda contínua em e-commerce, cosméticos e mockups de produto",
    },
    "finance": {
        "name": "Finance & B2B Analytics",
        "keywords": [
            "finance", "trading", "stock market", "investment",
            "financial chart", "growth", "candlestick", "crypto",
            "forex", "wealth", "economy", "banking", "analytics"
        ],
        "bonus": 28.0,
        "buyer_intent": "Fintechs, SaaS Corporativo & Consultorias Financeiras",
        "primary_insight": "Nicho B2B de alto RPM e maior valor médio de licença comercial",
    },
    "biotech": {
        "name": "Biotech & Healthcare",
        "keywords": [
            "biotech", "laboratory", "pipetting", "medical", "dna",
            "cleanroom", "pharma", "microscope", "science", "biology",
            "genetics", "chemistry", "scientific", "researcher"
        ],
        "bonus": 27.0,
        "buyer_intent": "Indústria Farmacêutica, Portais Científicos & Pesquisa",
        "primary_insight": "Nicho técnico de baixa saturação relativa e alta taxa de conversão",
    },
    "tech_space": {
        "name": "Tech, AI & Future",
        "keywords": [
            "astronaut", "space", "robot", "artificial intelligence",
            "cyberpunk", "futuristic", "technology", "quantum",
            "neural network", "deep learning", "automation", "metaverse"
        ],
        "bonus": 22.0,
        "buyer_intent": "Startups de Tecnologia, Conferências & Artigos Tech",
        "primary_insight": "Forte impacto visual para hero banners, keynotes e capas editoriais",
    },
    "abstract": {
        "name": "Abstract & Textures",
        "keywords": [
            "abstract", "texture", "background", "pattern", "geometry",
            "liquid", "wave", "fluid", "crystal", "glass"
        ],
        "bonus": 16.0,
        "buyer_intent": "Web Designers, Mídia Digital & Fundos de Apresentação",
        "primary_insight": "Ativo versátil para fundos corporativos, slides e composições digitais",
    },
}

# Indicadores de Copy-Space / Espaço Negativo
COPY_SPACE_INDICATORS = [
    "copy space", "copyspace", "copy-space", "negative space", "empty space",
    "blank", "isolated", "clean background", "minimalist", "white background",
    "light gray background", "beige background", "plain background",
    "empty backdrop", "spacious", "product placement area"
]


def evaluate_sales_potential(
    item: Dict[str, Any],
    fallback_title: Optional[str] = None
) -> Dict[str, Any]:
    """Calcula a pontuação de potencial de vendas (0.0 a 100.0) de um ativo.

    Args:
        item: Dicionário contendo filename, title, keywords e metadados.
        fallback_title: Título alternativo se não houver no item.

    Returns:
        Dicionário com sales_score, sales_tier, sales_tier_key, badge_color,
        niche, niche_key, buyer_intent, has_copyspace e insights.
    """
    fn = item.get("filename") or item.get("Filename") or ""
    title = item.get("title") or item.get("Title") or fallback_title or ""
    raw_keywords = item.get("keywords") or item.get("Keywords") or ""

    if isinstance(raw_keywords, list):
        keywords = [str(k).strip().lower() for k in raw_keywords if str(k).strip()]
    elif isinstance(raw_keywords, str):
        keywords = [k.strip().lower() for k in raw_keywords.split(",") if k.strip()]
    else:
        keywords = []

    kw_text = " ".join(keywords)
    combined_search_text = f"{title.lower()} {kw_text} {fn.lower().replace('-', ' ').replace('_', ' ')}"

    score = 45.0  # Pontuação base
    insights: List[str] = []

    # 1. Identificação do Nicho Comercial & Demanda de Mercado (Até +28 pts)
    detected_niche_key = "abstract"
    max_matched_terms = 0

    for n_key, n_def in NICHE_DEFINITIONS.items():
        matched = [k for k in n_def["keywords"] if k in combined_search_text]
        if len(matched) > max_matched_terms:
            max_matched_terms = len(matched)
            detected_niche_key = n_key

    # Se não houver correspondência específica de termos mas nicho for padrão
    niche_info = NICHE_DEFINITIONS[detected_niche_key]
    score += niche_info["bonus"]
    niche_name = niche_info["name"]
    buyer_intent = niche_info["buyer_intent"]
    insights.append(niche_info["primary_insight"])

    # 2. Usabilidade Comercial: Copy-Space / Espaço Negativo (Até +20 pts)
    # Ativos com espaço negativo convertem até 3.4x mais em bancos de imagens
    has_copyspace = any(k in combined_search_text for k in COPY_SPACE_INDICATORS)
    
    # Se for da categoria 'podium', quase sempre possui copy-space nativo
    if not has_copyspace and detected_niche_key == "podium":
        has_copyspace = True

    if has_copyspace:
        score += 18.0
        insights.append("Área limpa de Copy-Space identificada (ideal para inserção de texto/logos)")
    else:
        score += 5.0

    # 3. Qualidade de Indexação SEO & Densidade de Tags (Até +14 pts)
    tag_count = len(keywords)
    if tag_count >= 48:
        score += 8.0
        insights.append(f"Indexação SEO excelente com {tag_count} palavras-chave (teto das agências)")
    elif tag_count >= 30:
        score += 5.0
    elif tag_count >= 15:
        score += 2.0

    # Otimização de Título Comercial
    title_len = len(title.strip())
    if 35 <= title_len <= 190:
        score += 4.0
    elif title_len > 0:
        score += 2.0

    # Presença de Tags de Conformidade de IA
    has_ai_compliance = any(k in keywords for k in ["ai generated", "generative ai", "digital art", "illustration"])
    if has_ai_compliance:
        score += 2.0

    # 4. Normalização e Atribuição de Tiers
    final_score = min(round(score, 1), 99.0)

    if final_score >= 88.0:
        tier = "Tier S"
        tier_label = "Tier S (Altíssimo Potencial)"
        tier_key = "tier_s"
        badge_color = "gold"
    elif final_score >= 78.0:
        tier = "Tier A"
        tier_label = "Tier A (Alto Potencial)"
        tier_key = "tier_a"
        badge_color = "emerald"
    elif final_score >= 68.0:
        tier = "Tier B"
        tier_label = "Tier B (Moderado)"
        tier_key = "tier_a" if final_score >= 75 else "tier_b"
        tier_key = "tier_b"
        badge_color = "blue"
    else:
        tier = "Tier C"
        tier_label = "Tier C (Conceitual)"
        tier_key = "tier_c"
        badge_color = "purple"

    return {
        "sales_score": final_score,
        "sales_tier": tier,
        "sales_tier_label": tier_label,
        "sales_tier_key": tier_key,
        "badge_color": badge_color,
        "niche": niche_name,
        "niche_key": detected_niche_key,
        "buyer_intent": buyer_intent,
        "has_copyspace": has_copyspace,
        "insights": insights[:3],
    }


def get_portfolio_sales_analytics(images: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula agregados analíticos e métricas de conversão de toda a carteira.

    Args:
        images: Lista de imagens com campos de pontuação calculados.

    Returns:
        Métricas consolidadas com médias, contagem por tier, nichos e top performers.
    """
    total = len(images)
    if total == 0:
        return {
            "total_images": 0,
            "average_score": 0.0,
            "copyspace_count": 0,
            "copyspace_percentage": 0.0,
            "tiers": {"tier_s": 0, "tier_a": 0, "tier_b": 0, "tier_c": 0},
            "niches": {},
            "top_performers": [],
        }

    scores = [img.get("sales_score", 0.0) for img in images]
    avg_score = round(sum(scores) / total, 1)

    copyspace_count = sum(1 for img in images if img.get("has_copyspace"))
    copyspace_pct = round((copyspace_count / total) * 100, 1)

    tier_counts = {
        "tier_s": sum(1 for img in images if img.get("sales_tier_key") == "tier_s"),
        "tier_a": sum(1 for img in images if img.get("sales_tier_key") == "tier_a"),
        "tier_b": sum(1 for img in images if img.get("sales_tier_key") == "tier_b"),
        "tier_c": sum(1 for img in images if img.get("sales_tier_key") == "tier_c"),
    }

    niche_counts: Dict[str, Dict[str, Any]] = {}
    for n_key, n_def in NICHE_DEFINITIONS.items():
        matched_count = sum(1 for img in images if img.get("niche_key") == n_key)
        niche_counts[n_key] = {
            "name": n_def["name"],
            "count": matched_count,
            "percentage": round((matched_count / total) * 100, 1) if total > 0 else 0.0,
        }

    # Ordenar melhores ativos por score decrescente
    sorted_images = sorted(images, key=lambda x: x.get("sales_score", 0.0), reverse=True)
    top_performers = [
        {
            "filename": img.get("filename"),
            "title": img.get("title") or img.get("filename"),
            "sales_score": img.get("sales_score"),
            "sales_tier": img.get("sales_tier"),
            "niche": img.get("niche"),
            "has_copyspace": img.get("has_copyspace"),
            "insights": img.get("insights", []),
        }
        for img in sorted_images[:10]
    ]

    return {
        "total_images": total,
        "average_score": avg_score,
        "copyspace_count": copyspace_count,
        "copyspace_percentage": copyspace_pct,
        "tiers": tier_counts,
        "niches": niche_counts,
        "top_performers": top_performers,
    }
