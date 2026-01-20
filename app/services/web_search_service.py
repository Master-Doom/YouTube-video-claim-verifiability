"""
Web search service for evidence retrieval using Google Custom Search API.
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)


# Source reliability scores based on domain type
SOURCE_RELIABILITY = {
    # Government sources
    'gov': 0.9,
    'go.th': 0.9,
    'go.kr': 0.9,
    'gov.uk': 0.9,
    # Educational sources
    'edu': 0.85,
    'ac.th': 0.85,
    'ac.uk': 0.85,
    # Highly reliable news
    'reuters.com': 0.9,
    'apnews.com': 0.9,
    'bbc.com': 0.85,
    'bbc.co.uk': 0.85,
    'npr.org': 0.85,
    # Major newspapers
    'nytimes.com': 0.8,
    'washingtonpost.com': 0.8,
    'theguardian.com': 0.8,
    'economist.com': 0.8,
    # Reference sources
    'wikipedia.org': 0.7,
    'britannica.com': 0.85,
    'who.int': 0.9,
    'un.org': 0.9,
    'cdc.gov': 0.9,
    # Fact-checking sites
    'snopes.com': 0.8,
    'factcheck.org': 0.85,
    'politifact.com': 0.8,
    # Academic/Scientific
    'nature.com': 0.9,
    'science.org': 0.9,
    'pubmed.ncbi.nlm.nih.gov': 0.9,
    'scholar.google.com': 0.8,
    # Default for unknown sources
    'default': 0.5
}

# Low reliability sources (social media, forums, etc.)
LOW_RELIABILITY_DOMAINS = [
    'twitter.com', 'x.com', 'facebook.com', 'instagram.com',
    'tiktok.com', 'reddit.com', 'quora.com', 'yahoo.com/answers',
    'medium.com', 'substack.com'
]


class WebSearchService:
    """Service for Google Custom Search API and content fetching."""

    def __init__(self):
        self.api_key = settings.GOOGLE_SEARCH_API_KEY
        self.cx = settings.GOOGLE_SEARCH_CX
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def is_configured(self) -> bool:
        """Check if Google Search API is configured."""
        return bool(self.api_key and self.cx)

    async def search(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict]:
        """
        Search using Google Custom Search API.

        Args:
            query: Search query string
            num_results: Number of results to return (max 10)

        Returns:
            List of search results with url, title, snippet, reliability_score
        """
        if not self.is_configured():
            logger.warning("⚠️ Google Search API not configured, skipping search")
            return []

        params = {
            'key': self.api_key,
            'cx': self.cx,
            'q': query,
            'num': min(num_results, 10)
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Search API error {response.status}: {error_text[:200]}")
                        return []

                    data = await response.json()

            results = []
            for item in data.get('items', []):
                url = item.get('link', '')
                reliability = self._get_reliability_score(url)

                results.append({
                    'url': url,
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'reliability_score': reliability,
                    'reliability_label': self._get_reliability_label(reliability)
                })

            logger.debug(f"🔍 Search returned {len(results)} results for: {query[:50]}...")
            return results

        except asyncio.TimeoutError:
            logger.error(f"Search timeout for query: {query[:50]}...")
            return []
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def _get_reliability_score(self, url: str) -> float:
        """
        Calculate reliability score based on domain.

        Args:
            url: The URL to score

        Returns:
            Reliability score between 0 and 1
        """
        try:
            domain = urlparse(url).netloc.lower()

            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            # Check for low reliability domains
            for low_rel in LOW_RELIABILITY_DOMAINS:
                if low_rel in domain:
                    return 0.3

            # Check TLD and specific domains
            for key, score in SOURCE_RELIABILITY.items():
                if key == 'default':
                    continue
                # Check if it's a TLD match or domain match
                if domain.endswith(f'.{key}') or domain == key or key in domain:
                    return score

            return SOURCE_RELIABILITY['default']

        except Exception:
            return SOURCE_RELIABILITY['default']

    def _get_reliability_label(self, score: float) -> str:
        """Convert reliability score to human-readable label."""
        if score >= 0.85:
            return "high"
        elif score >= 0.7:
            return "medium-high"
        elif score >= 0.5:
            return "medium"
        else:
            return "low"

    async def fetch_content(
        self,
        url: str,
        max_chars: int = 5000
    ) -> Optional[str]:
        """
        Fetch and extract text content from URL.

        Args:
            url: URL to fetch
            max_chars: Maximum characters to return

        Returns:
            Extracted text content or None if failed
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True,
                    ssl=False  # Some sites have SSL issues
                ) as response:
                    if response.status != 200:
                        logger.debug(f"Failed to fetch {url}: HTTP {response.status}")
                        return None

                    # Check content type
                    content_type = response.headers.get('Content-Type', '')
                    if 'html' not in content_type.lower() and 'text' not in content_type.lower():
                        logger.debug(f"Skipping non-text content: {content_type}")
                        return None

                    html = await response.text()

            # Parse HTML and extract text
            soup = BeautifulSoup(html, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']):
                element.decompose()

            # Try to find main content
            main_content = None
            for selector in ['article', 'main', '[role="main"]', '.content', '.article-body', '#content']:
                main_content = soup.select_one(selector)
                if main_content:
                    break

            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                # Fallback to body
                body = soup.find('body')
                text = body.get_text(separator=' ', strip=True) if body else soup.get_text(separator=' ', strip=True)

            # Clean up whitespace
            text = ' '.join(text.split())

            logger.debug(f"📄 Fetched {len(text)} chars from {url[:50]}...")
            return text[:max_chars]

        except asyncio.TimeoutError:
            logger.debug(f"Timeout fetching {url}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            return None

    async def search_and_fetch(
        self,
        query: str,
        num_results: int = 5,
        max_content_chars: int = 3000
    ) -> List[Dict]:
        """
        Search for results and fetch content from each URL.

        Args:
            query: Search query
            num_results: Number of results to search for
            max_content_chars: Max chars to fetch per URL

        Returns:
            List of results with content included
        """
        # First, search for results
        results = await self.search(query, num_results)

        if not results:
            return []

        # Fetch content from all URLs in parallel
        async def fetch_with_metadata(result: Dict) -> Dict:
            content = await self.fetch_content(result['url'], max_content_chars)
            return {
                **result,
                'content': content
            }

        results_with_content = await asyncio.gather(*[
            fetch_with_metadata(r) for r in results
        ])

        # Filter out results where content fetch failed
        results_with_content = [
            r for r in results_with_content
            if r.get('content')
        ]

        logger.info(f"🔍 Retrieved {len(results_with_content)} sources with content for: {query[:40]}...")
        return results_with_content


# Global singleton instance
web_search_service = WebSearchService()
