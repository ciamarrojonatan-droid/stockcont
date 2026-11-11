"""DarkFactory Public-Domain Research & Grounded Citation Engine.

Consulta fontes públicas verificáveis e de domínio público (Wikipedia REST,
Wikimedia Commons com filtro rígido de licença PD/CC0/PD-USGov, Internet Archive
e NASA Open APIs), gravando cache local de API e dossiês JSON atômicos com
fallback offline para `data/raw/dossiers/`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

import httpx

logger = logging.getLogger("research_engine")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_CACHE_DIR = BASE_DIR / "data" / "raw" / "research_cache"
DEFAULT_DOSSIERS_OUT_DIR = BASE_DIR / "data" / "processed" / "research_dossiers"
DEFAULT_LOCAL_DOSSIERS_DIR = BASE_DIR / "data" / "raw" / "dossiers"

ALLOWED_PUBLIC_DOMAIN_TOKENS = (
    "public domain",
    "publicdomain/zero",
    "publicdomain/mark",
    "cc0",
    "cc-zero",
    "pd-usgov",
    "pd-us",
    "pd-old",
    "pd-self",
    "no known copyright",
)
DENIED_LICENSE_TOKENS = (
    "all rights reserved",
    "non-commercial",
    "noncommercial",
    "fair use",
    "copyrighted",
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip().lower()).strip("_")
    return slug[:80] or "topic"


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    tmp_path.replace(path)


def is_public_domain_license(license_text: str) -> bool:
    """Strictly allow verifiable Public Domain / CC0 / US-Gov media licenses."""
    norm = re.sub(r"\s+", " ", (license_text or "").strip().lower())
    if not norm:
        return False
    if any(token in norm for token in DENIED_LICENSE_TOKENS):
        return False
    if re.search(r"\bcc[-_ ]by.*[-_ ]nc\b", norm):
        return False
    return any(token in norm for token in ALLOWED_PUBLIC_DOMAIN_TOKENS)


@dataclass
class FactCitation:
    statement: str
    source: str
    url: str


@dataclass
class MediaAssetRef:
    title: str
    url: str
    license_name: str
    source: str


@dataclass
class DossierFactPack:
    topic: str
    slug: str
    facts: List[FactCitation] = field(default_factory=list)
    media_assets: List[MediaAssetRef] = field(default_factory=list)
    cache_files: List[str] = field(default_factory=list)
    output_file: Optional[str] = None
    used_local_fallback: bool = False
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PublicDomainResearchEngine:
    """Multi-source factual & public-domain media aggregator for DarkFactory scripts."""

    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        output_dir: Path = DEFAULT_DOSSIERS_OUT_DIR,
        local_dossiers_dir: Path = DEFAULT_LOCAL_DOSSIERS_DIR,
        timeout_sec: float = 12.0,
    ):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.local_dossiers_dir = Path(local_dossiers_dir)
        self.timeout_sec = timeout_sec

    def _headers(self) -> Dict[str, str]:
        return {"User-Agent": "StockCont-DarkFactory/3.0 (public-domain-research)"}

    def _fetch_and_cache_json(self, url: str, params: Optional[Dict[str, Any]], cache_file: Path) -> Optional[Dict[str, Any]]:
        try:
            resp = httpx.get(url, params=params, headers=self._headers(), timeout=self.timeout_sec)
            if resp.status_code != 200:
                return None
            data = resp.json()
            _atomic_write_json(cache_file, data)
            return data if isinstance(data, dict) else None
        except Exception as exc:
            logger.warning("Research HTTP fetch failed (%s): %s", url, exc)
            return None

    def _query_wikipedia(self, topic: str, slug: str) -> Tuple[List[FactCitation], Optional[Path]]:
        encoded = quote(topic.strip().replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        cache_file = self.cache_dir / f"{slug}_wikipedia.json"
        data = self._fetch_and_cache_json(url, None, cache_file)
        if not data:
            return [], None
        extract = str(data.get("extract") or "").strip()
        page_url = str((data.get("content_urls") or {}).get("desktop", {}).get("page") or url)
        facts = [FactCitation(statement=extract, source="wikipedia", url=page_url)] if extract else []
        return facts, cache_file

    def _query_wikimedia_commons(self, topic: str, slug: str) -> Tuple[List[MediaAssetRef], Optional[Path]]:
        url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrnamespace": 6,
            "gsrsearch": topic,
            "gsrlimit": 10,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
        }
        cache_file = self.cache_dir / f"{slug}_wikimedia.json"
        data = self._fetch_and_cache_json(url, params, cache_file)
        if not data:
            return [], None

        assets: List[MediaAssetRef] = []
        pages = (data.get("query") or {}).get("pages") or {}
        for page in pages.values():
            info_list = page.get("imageinfo") or []
            if not info_list:
                continue
            info = info_list[0]
            ext = info.get("extmetadata") or {}
            lic_name = str((ext.get("LicenseShortName") or {}).get("value") or "")
            media_url = str(info.get("url") or "").strip()
            if media_url and is_public_domain_license(lic_name):
                assets.append(
                    MediaAssetRef(
                        title=str(page.get("title") or "Wikimedia PD Asset"),
                        url=media_url,
                        license_name=lic_name,
                        source="wikimedia_commons",
                    )
                )
        return assets, cache_file

    def _query_internet_archive(self, topic: str, slug: str) -> Tuple[List[MediaAssetRef], Optional[Path]]:
        url = "https://archive.org/advancedsearch.php"
        params = {
            "q": f'({topic}) AND (mediatype:movies OR mediatype:image OR mediatype:texts)',
            "fl[]": ["identifier", "title", "licenseurl"],
            "rows": 8,
            "output": "json",
        }
        cache_file = self.cache_dir / f"{slug}_internet_archive.json"
        data = self._fetch_and_cache_json(url, params, cache_file)
        if not data:
            return [], None

        assets: List[MediaAssetRef] = []
        docs = (data.get("response") or {}).get("docs") or []
        for doc in docs:
            identifier = str(doc.get("identifier") or "").strip()
            lic = str(doc.get("licenseurl") or "publicdomain")
            if identifier and (is_public_domain_license(lic) or "publicdomain" in lic.lower()):
                assets.append(
                    MediaAssetRef(
                        title=str(doc.get("title") or identifier),
                        url=f"https://archive.org/details/{identifier}",
                        license_name=lic,
                        source="internet_archive",
                    )
                )
        return assets, cache_file

    def _query_nasa_archive(self, topic: str, slug: str) -> Tuple[List[FactCitation], List[MediaAssetRef], Optional[Path]]:
        url = "https://images-api.nasa.gov/search"
        nasa_key = os.getenv("NASA_API_KEY") or "DEMO_KEY"
        params = {"q": topic, "media_type": "image,video", "page_size": 6}
        if nasa_key != "DEMO_KEY":
            params["api_key"] = nasa_key
        cache_file = self.cache_dir / f"{slug}_nasa.json"
        data = self._fetch_and_cache_json(url, params, cache_file)
        if not data:
            return [], [], None

        facts: List[FactCitation] = []
        assets: List[MediaAssetRef] = []
        items = ((data.get("collection") or {}).get("items") or [])
        for item in items:
            meta = (item.get("data") or [{}])[0]
            links = item.get("links") or []
            title = str(meta.get("title") or "NASA Archive Item")
            desc = str(meta.get("description") or "").strip()
            if desc:
                facts.append(FactCitation(statement=desc[:420], source="nasa_open_archive", url="https://images.nasa.gov"))
            for link in links:
                href = str(link.get("href") or "").strip()
                if href:
                    assets.append(
                        MediaAssetRef(
                            title=title,
                            url=href,
                            license_name="PD-USGov-NASA",
                            source="nasa",
                        )
                    )
                    break
        return facts, assets, cache_file

    def _load_local_fallback(self, topic: str, slug: str) -> List[FactCitation]:
        if not self.local_dossiers_dir.exists():
            return []
        facts: List[FactCitation] = []
        candidates = [
            self.local_dossiers_dir / f"{slug}.txt",
            self.local_dossiers_dir / f"{slug}.md",
        ]
        for path in candidates:
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    facts.append(FactCitation(statement=text[:1500], source="local_dossier", url=path.as_posix()))
        return facts

    def build_dossier(
        self,
        topic: str,
        sources: Iterable[str] = ("wikipedia", "wikimedia", "internet_archive", "nasa"),
    ) -> DossierFactPack:
        """Collect grounded facts + PD media assets and write an atomic research dossier JSON."""
        slug = _slugify(topic)
        selected = {s.strip().lower() for s in sources}
        facts: List[FactCitation] = []
        media_assets: List[MediaAssetRef] = []
        cache_files: List[str] = []

        if "wikipedia" in selected:
            wiki_facts, cache_path = self._query_wikipedia(topic, slug)
            facts.extend(wiki_facts)
            if cache_path:
                cache_files.append(cache_path.as_posix())

        if "wikimedia" in selected:
            wm_assets, cache_path = self._query_wikimedia_commons(topic, slug)
            media_assets.extend(wm_assets)
            if cache_path:
                cache_files.append(cache_path.as_posix())

        if "internet_archive" in selected:
            ia_assets, cache_path = self._query_internet_archive(topic, slug)
            media_assets.extend(ia_assets)
            if cache_path:
                cache_files.append(cache_path.as_posix())

        if "nasa" in selected:
            nasa_facts, nasa_assets, cache_path = self._query_nasa_archive(topic, slug)
            facts.extend(nasa_facts)
            media_assets.extend(nasa_assets)
            if cache_path:
                cache_files.append(cache_path.as_posix())

        used_fallback = False
        if not facts:
            local_facts = self._load_local_fallback(topic, slug)
            if local_facts:
                facts.extend(local_facts)
                used_fallback = True

        out_path = self.output_dir / f"{slug}.json"
        pack = DossierFactPack(
            topic=topic,
            slug=slug,
            facts=facts,
            media_assets=media_assets,
            cache_files=cache_files,
            output_file=out_path.as_posix(),
            used_local_fallback=used_fallback,
        )
        _atomic_write_json(out_path, pack.to_dict())
        return pack
