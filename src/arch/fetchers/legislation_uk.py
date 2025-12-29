"""Fetcher for UK legislation from legislation.gov.uk.

Downloads legislation in CLML XML format via the REST API.

API Documentation: https://legislation.github.io/data-documentation/
Rate Limit: 3,000 requests per 5 minutes per IP
"""

import asyncio
from pathlib import Path
from typing import Iterator, Optional

import httpx

from arch.models_uk import UKAct, UKCitation, UKSection
from arch.parsers.clml import parse_act_metadata, parse_section


# Priority Acts for PolicyEngine UK
UK_PRIORITY_ACTS = [
    "ukpga/2003/1",   # Income Tax (Earnings and Pensions) Act 2003
    "ukpga/2007/3",   # Income Tax Act 2007
    "ukpga/2009/4",   # Corporation Tax Act 2009
    "ukpga/1992/4",   # Social Security Contributions and Benefits Act 1992
    "ukpga/2012/5",   # Welfare Reform Act 2012
    "ukpga/2002/21",  # Tax Credits Act 2002
    "ukpga/1992/12",  # Taxation of Chargeable Gains Act 1992
    "ukpga/1994/23",  # Value Added Tax Act 1994
    "ukpga/1984/51",  # Inheritance Tax Act 1984
    "ukpga/2017/32",  # Finance Act 2017
]


class UKLegislationFetcher:
    """Fetcher for UK legislation from legislation.gov.uk.

    Downloads legislation XML and parses into UKSection/UKAct objects.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        base_url: str = "https://www.legislation.gov.uk",
        rate_limit_delay: float = 0.2,
    ):
        """Initialize the fetcher.

        Args:
            data_dir: Directory to cache downloaded files.
                     Defaults to ~/.arch/uk/
            base_url: Base URL for legislation.gov.uk API.
            rate_limit_delay: Seconds between requests (default 0.2 = 5/sec).
        """
        self.base_url = base_url
        self.data_dir = data_dir or Path.home() / ".arch" / "uk"
        self.rate_limit_delay = rate_limit_delay
        self._last_request_time = 0.0

    def build_url(self, citation: UKCitation, version: str = "") -> str:
        """Build the XML data URL for a citation.

        Args:
            citation: UK legislation citation
            version: Version specifier (e.g., "enacted", "2020-01-01")

        Returns:
            URL to fetch XML data
        """
        url = f"{self.base_url}/{citation.type}/{citation.year}/{citation.number}"
        if citation.section:
            url += f"/section/{citation.section}"
        if version:
            url += f"/{version}"
        url += "/data.xml"
        return url

    def build_search_url(
        self,
        query: str,
        type: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = 20,
    ) -> str:
        """Build search API URL.

        Args:
            query: Search query text
            type: Legislation type filter (e.g., "ukpga")
            year: Year filter
            limit: Max results (default 20)

        Returns:
            Search URL
        """
        params = [f"text={query}", f"results-count={limit}"]
        if type:
            params.append(f"type={type}")
        if year:
            params.append(f"year={year}")
        return f"{self.base_url}/search?{'&'.join(params)}"

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        import time
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    async def _fetch_xml(self, url: str) -> str:
        """Fetch XML from URL with rate limiting.

        Args:
            url: URL to fetch

        Returns:
            XML string

        Raises:
            httpx.HTTPError: If request fails
        """
        await self._rate_limit()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"User-Agent": "Arch/1.0 (https://github.com/CosilicoAI/arch)"},
                follow_redirects=True,
                timeout=60,
            )
            response.raise_for_status()
            return response.text

    def _cache_path(self, citation: UKCitation) -> Path:
        """Get cache file path for a citation."""
        path = self.data_dir / citation.type / str(citation.year) / str(citation.number)
        if citation.section:
            return path / f"section-{citation.section}.xml"
        return path / "act.xml"

    async def fetch_section(
        self,
        citation: UKCitation,
        cache: bool = True,
        force: bool = False,
    ) -> UKSection:
        """Fetch a single section.

        Args:
            citation: Citation with section number
            cache: Whether to cache the XML
            force: Re-fetch even if cached

        Returns:
            UKSection object
        """
        cache_path = self._cache_path(citation)

        # Check cache
        if not force and cache_path.exists():
            xml_str = cache_path.read_text()
        else:
            url = self.build_url(citation)
            xml_str = await self._fetch_xml(url)

            # Save to cache
            if cache:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(xml_str)

        return parse_section(xml_str)

    async def fetch_act_metadata(
        self,
        citation: UKCitation,
        cache: bool = True,
        force: bool = False,
    ) -> UKAct:
        """Fetch Act-level metadata.

        Args:
            citation: Citation without section
            cache: Whether to cache the XML
            force: Re-fetch even if cached

        Returns:
            UKAct object with metadata
        """
        cache_path = self._cache_path(citation)

        if not force and cache_path.exists():
            xml_str = cache_path.read_text()
        else:
            url = self.build_url(citation)
            xml_str = await self._fetch_xml(url)

            if cache:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(xml_str)

        return parse_act_metadata(xml_str)

    async def fetch_act_sections(
        self,
        citation: UKCitation,
        max_sections: Optional[int] = None,
    ) -> Iterator[UKSection]:
        """Fetch all sections from an Act.

        Args:
            citation: Citation for the Act
            max_sections: Maximum sections to fetch

        Yields:
            UKSection objects
        """
        # First, get the Act metadata to find section count
        act = await self.fetch_act_metadata(citation)
        section_count = act.section_count or 1000  # Default max

        if max_sections:
            section_count = min(section_count, max_sections)

        # Fetch sections (legislation.gov.uk uses numeric sections)
        sections = []
        for i in range(1, section_count + 1):
            try:
                section_citation = UKCitation(
                    type=citation.type,
                    year=citation.year,
                    number=citation.number,
                    section=str(i),
                )
                section = await self.fetch_section(section_citation)
                sections.append(section)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Section doesn't exist, skip
                    continue
                raise

        return iter(sections)


async def download_uk_act(
    act_ref: str,
    data_dir: Optional[Path] = None,
    max_sections: Optional[int] = None,
) -> list[UKSection]:
    """Convenience function to download an entire UK Act.

    Args:
        act_ref: Act reference like "ukpga/2003/1"
        data_dir: Optional data directory
        max_sections: Optional limit on sections

    Returns:
        List of UKSection objects
    """
    citation = UKCitation.from_string(act_ref)
    fetcher = UKLegislationFetcher(data_dir=data_dir)
    sections = await fetcher.fetch_act_sections(citation, max_sections=max_sections)
    return list(sections)
