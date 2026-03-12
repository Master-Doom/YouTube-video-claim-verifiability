"""
Pipeline for retrieving evidence from web sources to verify claims.
"""
import asyncio
from typing import List, Dict, Any

from app.services.web_search_service import web_search_service
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)


def generate_search_queries(claim: Dict) -> List[str]:
    """
    Generate effective search queries for a scientific claim.

    Args:
        claim: Claim dictionary with claim_text, claim_type, key_entities

    Returns:
        List of search queries to try
    """
    queries = []
    claim_text = claim.get('claim_text', '')
    search_query = claim.get('search_query', '')
    entities = claim.get('key_entities', [])

    # Use the LLM-generated search query if available
    if search_query and search_query != claim_text:
        queries.append(search_query)

    # Scientific-specific query
    queries.append(f"{claim_text} scientific research study")

    # Entity-focused academic query if entities exist
    if entities:
        entity_str = " ".join(entities[:3])
        queries.append(f"{entity_str} peer-reviewed research")

    # Always add the plain claim as a fallback
    if claim_text not in queries:
        queries.append(claim_text)

    return queries[:3]  # Limit to 3 queries


async def retrieve_evidence_for_claim(
    claim: Dict,
    num_sources: int = None
) -> List[Dict[str, Any]]:
    """
    Retrieve evidence for a single claim.

    Args:
        claim: Claim dictionary with claim_text and metadata
        num_sources: Number of sources to retrieve (defaults to settings)

    Returns:
        List of evidence sources with url, title, snippet, content, reliability
    """
    if num_sources is None:
        num_sources = settings.EVIDENCE_SOURCES_PER_CLAIM

    if not web_search_service.is_configured():
        logger.warning("⚠️ Web search not configured, returning empty evidence")
        return []

    claim_text = claim.get('claim_text', '')
    if not claim_text:
        return []

    # Generate search queries
    queries = generate_search_queries(claim)

    all_evidence = []
    seen_urls = set()

    for query in queries:
        if len(all_evidence) >= num_sources:
            break

        # Search and fetch content
        results = await web_search_service.search_and_fetch(
            query=query,
            num_results=num_sources - len(all_evidence),
            max_content_chars=3000
        )

        # Add new results (avoid duplicates)
        for result in results:
            url = result.get('url', '')
            if url not in seen_urls:
                seen_urls.add(url)
                all_evidence.append(result)

                if len(all_evidence) >= num_sources:
                    break

    logger.debug(f"📚 Retrieved {len(all_evidence)} evidence sources for claim: {claim_text[:50]}...")
    return all_evidence


async def retrieve_evidence_batch(
    claims: List[Dict],
    num_sources_per_claim: int = None
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Retrieve evidence for multiple claims in parallel.

    Args:
        claims: List of claim dictionaries
        num_sources_per_claim: Sources to retrieve per claim

    Returns:
        Dictionary mapping claim index to evidence list
    """
    if not claims:
        return {}

    if num_sources_per_claim is None:
        num_sources_per_claim = settings.EVIDENCE_SOURCES_PER_CLAIM

    logger.info(f"🔍 Retrieving evidence for {len(claims)} claims in parallel")

    # Create tasks for parallel execution
    tasks = [
        retrieve_evidence_for_claim(claim, num_sources_per_claim)
        for claim in claims
    ]

    # Execute all searches in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build result dictionary
    evidence_map = {}
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"❌ Evidence retrieval failed for claim {i}: {result}")
            evidence_map[i] = []
        else:
            evidence_map[i] = result

    total_sources = sum(len(v) for v in evidence_map.values())
    logger.info(f"✅ Retrieved {total_sources} total evidence sources for {len(claims)} claims")

    return evidence_map


def filter_evidence_by_reliability(
    evidence: List[Dict],
    min_reliability: float = 0.4
) -> List[Dict]:
    """
    Filter evidence to keep only sufficiently reliable sources.

    Args:
        evidence: List of evidence sources
        min_reliability: Minimum reliability score (0-1)

    Returns:
        Filtered list of evidence sources
    """
    return [
        e for e in evidence
        if e.get('reliability_score', 0) >= min_reliability
    ]


def rank_evidence_by_reliability(evidence: List[Dict]) -> List[Dict]:
    """
    Sort evidence by reliability score (highest first).

    Args:
        evidence: List of evidence sources

    Returns:
        Sorted list of evidence sources
    """
    return sorted(
        evidence,
        key=lambda x: x.get('reliability_score', 0),
        reverse=True
    )
