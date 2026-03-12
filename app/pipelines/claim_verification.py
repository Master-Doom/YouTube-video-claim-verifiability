"""
Pipeline for verifying claims against evidence using Gemini.
"""
from typing import Dict, List, Any

from app.services.gemini_service import gemini_service
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


VERIFICATION_PROMPT = """
You are an expert scientific fact-checker with expertise in evaluating scientific claims against research evidence.
Your task is to verify the following scientific claim using the provided evidence sources.

CLAIM TO VERIFY:
"{claim_text}"

Speaker: {speaker}
Timestamp: {timestamp}
Claim Type: {claim_type}

EVIDENCE SOURCES:
{evidence_text}

VERIFICATION INSTRUCTIONS:
1. Carefully analyze ALL evidence sources
2. Look for information that SUPPORTS the claim
3. Look for information that CONTRADICTS the claim
4. Consider the reliability of each source (score shown)
5. Determine if there is consensus or conflicting information
6. Prioritize evidence from peer-reviewed journals, institutional sources (.edu, .gov), and established scientific organizations
7. Consider the scientific consensus, not just individual studies
8. Be conservative - if uncertain, mark as "inconclusive"

VERDICT DEFINITIONS:
- "supported": Scientific evidence from reliable sources confirms the claim's accuracy
- "refuted": Reliable scientific sources contradict or disprove the claim
- "inconclusive": Insufficient scientific evidence, conflicting sources, or claim cannot be verified

CONFIDENCE SCORING:
- 0.9-1.0: Very strong evidence with multiple high-reliability scientific sources agreeing
- 0.7-0.9: Good evidence from reliable scientific sources
- 0.5-0.7: Some evidence but limited sources or mixed reliability
- 0.3-0.5: Weak evidence or conflicting sources
- 0.0-0.3: Very limited evidence available

OUTPUT FORMAT (JSON):
{{
    "verdict": "supported|refuted|inconclusive",
    "confidence": 0.75,
    "explanation": "Clear explanation of the verdict in 2-3 sentences. What scientific evidence supports or refutes the claim?",
    "supporting_evidence": [
        {{
            "source_url": "URL of the supporting source",
            "source_title": "Title of the source",
            "quote": "Relevant quote or summary from this source that supports the claim",
            "reliability": 0.8
        }}
    ],
    "counter_evidence": [
        {{
            "source_url": "URL of the contradicting source",
            "source_title": "Title of the source",
            "quote": "Relevant quote or summary that contradicts the claim",
            "reliability": 0.8
        }}
    ],
    "key_finding": "The single most important finding from the analysis",
    "caveats": "Important limitations, context, or nuances (if any)"
}}

Be objective and fair. If the evidence is mixed, acknowledge both sides.
"""


NO_EVIDENCE_RESPONSE = {
    "verdict": "inconclusive",
    "confidence": 0.0,
    "explanation": "No evidence sources were found to verify this claim. The claim cannot be evaluated without supporting or contradicting evidence.",
    "supporting_evidence": [],
    "counter_evidence": [],
    "key_finding": "Unable to find relevant evidence for verification",
    "caveats": "This claim requires manual verification as automated evidence retrieval did not return results."
}


def format_evidence_for_prompt(evidence: List[Dict]) -> str:
    """
    Format evidence sources into text for the verification prompt.

    Args:
        evidence: List of evidence dictionaries

    Returns:
        Formatted evidence text
    """
    if not evidence:
        return "No evidence sources available."

    lines = []
    for i, e in enumerate(evidence, 1):
        url = e.get('url', 'Unknown URL')
        title = e.get('title', 'Untitled')
        reliability = e.get('reliability_score', 0.5)
        reliability_label = e.get('reliability_label', 'medium')
        content = e.get('content', e.get('snippet', 'No content available'))

        # Truncate content if too long
        if len(content) > 2000:
            content = content[:2000] + "..."

        lines.append(f"""
--- Source {i} ---
Title: {title}
URL: {url}
Reliability: {reliability:.2f} ({reliability_label})
Content:
{content}
""")

    return "\n".join(lines)


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


async def verify_claim(
    claim: Dict,
    evidence: List[Dict]
) -> Dict[str, Any]:
    """
    Verify a single claim against its evidence.

    Args:
        claim: Claim dictionary with claim_text, speaker, start_time, etc.
        evidence: List of evidence sources

    Returns:
        Verification result with verdict, confidence, explanation, and evidence references
    """
    claim_text = claim.get('claim_text', '')
    speaker = claim.get('speaker', 'Unknown')
    start_time = claim.get('start_time', 0)
    claim_type = claim.get('claim_type', 'unknown')

    # Handle case with no evidence
    if not evidence:
        logger.warning(f"⚠️ No evidence for claim: {claim_text[:50]}...")
        result = NO_EVIDENCE_RESPONSE.copy()
        result['claim'] = claim
        return result

    # Format evidence for prompt
    evidence_text = format_evidence_for_prompt(evidence)
    timestamp = format_timestamp(start_time)

    # Build verification prompt
    prompt = VERIFICATION_PROMPT.format(
        claim_text=claim_text,
        speaker=speaker,
        timestamp=timestamp,
        claim_type=claim_type,
        evidence_text=evidence_text
    )

    try:
        # Call Gemini for verification
        result = await gemini_service.generate_json(prompt)

        if 'error' in result:
            logger.error(f"❌ Gemini error during verification: {result['error']}")
            return {
                'claim': claim,
                'verdict': 'error',
                'confidence': 0.0,
                'explanation': f"Verification failed: {result['error']}",
                'supporting_evidence': [],
                'counter_evidence': [],
                'key_finding': 'Verification could not be completed',
                'caveats': 'Technical error during verification'
            }

        # Validate and normalize the response
        verdict = result.get('verdict', 'inconclusive').lower()
        if verdict not in ['supported', 'refuted', 'inconclusive']:
            verdict = 'inconclusive'

        confidence = result.get('confidence', 0.5)
        if isinstance(confidence, (int, float)):
            confidence = min(1.0, max(0.0, float(confidence)))
        else:
            confidence = 0.5

        verification_result = {
            'claim': claim,
            'verdict': verdict,
            'confidence': confidence,
            'explanation': str(result.get('explanation', 'No explanation provided')),
            'supporting_evidence': result.get('supporting_evidence', []),
            'counter_evidence': result.get('counter_evidence', []),
            'key_finding': str(result.get('key_finding', '')),
            'caveats': str(result.get('caveats', ''))
        }

        logger.info(f"✅ Verified claim: {verdict} ({confidence:.0%}) - {claim_text[:40]}...")
        return verification_result

    except Exception as e:
        logger.error(f"❌ Verification failed for claim: {e}")
        return {
            'claim': claim,
            'verdict': 'error',
            'confidence': 0.0,
            'explanation': f"Verification error: {str(e)}",
            'supporting_evidence': [],
            'counter_evidence': [],
            'key_finding': 'Verification could not be completed',
            'caveats': 'Technical error during verification'
        }


async def verify_claims_batch(
    claims: List[Dict],
    evidence_map: Dict[int, List[Dict]],
    progress_callback=None
) -> List[Dict[str, Any]]:
    """
    Verify multiple claims sequentially (due to rate limits).

    Args:
        claims: List of claims to verify
        evidence_map: Dictionary mapping claim index to evidence list
        progress_callback: Optional callback for progress updates

    Returns:
        List of verification results
    """
    results = []

    for i, claim in enumerate(claims):
        if progress_callback:
            progress_callback(f"Verifying claim {i + 1} of {len(claims)}...")

        evidence = evidence_map.get(i, [])
        result = await verify_claim(claim, evidence)
        results.append(result)

    return results
