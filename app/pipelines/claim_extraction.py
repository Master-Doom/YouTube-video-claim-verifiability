"""
Pipeline for extracting factual claims from transcripts using Gemini.
"""
from typing import List, Dict, Any

from app.services.gemini_service import gemini_service
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)


CLAIM_EXTRACTION_PROMPT = """
You are a fact-checking assistant. Analyze this transcript and extract FACTUAL CLAIMS that can be verified.

TRANSCRIPT:
{transcript}

RULES FOR EXTRACTION:
1. Extract ONLY factual claims that can be objectively verified
2. Include claims about:
   - Historical events (with dates, years, or time periods)
   - Statistics, numbers, and quantities
   - Scientific facts and research findings
   - Current events and factual statements
   - Quotes attributed to specific people
   - Geographic or demographic facts

3. EXCLUDE (do not extract):
   - Opinions ("I think", "I believe", "in my opinion")
   - Predictions ("will happen", "going to", "might")
   - Subjective statements ("beautiful", "good", "bad", "amazing")
   - Questions
   - Personal anecdotes without verifiable facts
   - Vague statements without specific details
   - Rhetorical statements

4. Make each claim:
   - Self-contained (understandable without context)
   - Specific with verifiable details
   - In the same language as the original statement

5. Generate a search query that would help verify each claim

OUTPUT FORMAT (JSON):
{{
    "claims": [
        {{
            "claim_text": "The exact factual claim as stated or slightly paraphrased for clarity",
            "speaker": "SPEAKER_XX",
            "start_time": 0.0,
            "end_time": 5.0,
            "claim_type": "statistic|historical|scientific|current_event|quote|geographic",
            "confidence": 0.85,
            "search_query": "Effective search query to verify this claim",
            "key_entities": ["entity1", "entity2"]
        }}
    ]
}}

Return at most {max_claims} of the most significant and verifiable claims.
Prioritize claims with specific numbers, dates, or names that are easier to verify.
"""


def format_transcript_for_extraction(segments: List[Dict]) -> str:
    """
    Format transcript segments into a readable format for the LLM.

    Args:
        segments: List of transcript segments with speaker, start, end, text

    Returns:
        Formatted transcript string
    """
    lines = []
    for seg in segments:
        speaker = seg.get('speaker', 'UNKNOWN')
        start = seg.get('start', 0)
        text = seg.get('text', '').strip()

        # Format timestamp as MM:SS
        minutes = int(start // 60)
        seconds = int(start % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"

        lines.append(f"[{timestamp}] {speaker}: {text}")

    return "\n".join(lines)


async def extract_claims(
    segments: List[Dict],
    max_claims: int = None
) -> List[Dict[str, Any]]:
    """
    Extract factual claims from transcript segments.

    Args:
        segments: List of transcript segments with speaker, start, end, text
        max_claims: Maximum number of claims to extract (defaults to settings)

    Returns:
        List of claim dictionaries with:
        - claim_text: The factual claim
        - speaker: Speaker identifier
        - start_time: Start timestamp in seconds
        - end_time: End timestamp in seconds
        - claim_type: Type of claim
        - confidence: Extraction confidence (0-1)
        - search_query: Suggested search query
        - key_entities: Key entities in the claim
    """
    if max_claims is None:
        max_claims = settings.MAX_CLAIMS_TO_VERIFY

    if not segments:
        logger.warning("⚠️ No segments provided for claim extraction")
        return []

    if not gemini_service.is_configured():
        logger.error("❌ Gemini API not configured for claim extraction")
        return []

    logger.info(f"📝 Extracting claims from {len(segments)} transcript segments")

    # Format transcript
    transcript_text = format_transcript_for_extraction(segments)

    # Limit transcript length to avoid token limits
    max_transcript_chars = 15000
    if len(transcript_text) > max_transcript_chars:
        logger.warning(f"⚠️ Transcript too long ({len(transcript_text)} chars), truncating")
        transcript_text = transcript_text[:max_transcript_chars] + "\n\n[TRANSCRIPT TRUNCATED]"

    # Build prompt
    prompt = CLAIM_EXTRACTION_PROMPT.format(
        transcript=transcript_text,
        max_claims=max_claims
    )

    try:
        # Call Gemini
        result = await gemini_service.generate_json(prompt)

        if 'error' in result:
            logger.error(f"❌ Gemini error during claim extraction: {result['error']}")
            return []

        claims = result.get('claims', [])

        # Validate and clean claims
        valid_claims = []
        for claim in claims:
            if not isinstance(claim, dict):
                continue

            # Ensure required fields exist
            if not claim.get('claim_text'):
                continue

            # Normalize fields
            cleaned_claim = {
                'claim_text': str(claim.get('claim_text', '')).strip(),
                'speaker': str(claim.get('speaker', 'UNKNOWN')),
                'start_time': float(claim.get('start_time', 0)),
                'end_time': float(claim.get('end_time', claim.get('start_time', 0) + 5)),
                'claim_type': str(claim.get('claim_type', 'unknown')),
                'confidence': min(1.0, max(0.0, float(claim.get('confidence', 0.5)))),
                'search_query': str(claim.get('search_query', claim.get('claim_text', ''))),
                'key_entities': claim.get('key_entities', [])
            }

            valid_claims.append(cleaned_claim)

        # Sort by confidence and limit
        valid_claims.sort(key=lambda x: x['confidence'], reverse=True)
        valid_claims = valid_claims[:max_claims]

        logger.info(f"✅ Extracted {len(valid_claims)} verifiable claims")
        return valid_claims

    except Exception as e:
        logger.error(f"❌ Claim extraction failed: {e}")
        return []


async def extract_claims_batch(
    segments: List[Dict],
    batch_size: int = 50,
    max_claims: int = None
) -> List[Dict[str, Any]]:
    """
    Extract claims from long transcripts by processing in batches.

    Args:
        segments: All transcript segments
        batch_size: Number of segments per batch
        max_claims: Maximum total claims to extract

    Returns:
        Combined list of claims from all batches
    """
    if max_claims is None:
        max_claims = settings.MAX_CLAIMS_TO_VERIFY

    if len(segments) <= batch_size:
        return await extract_claims(segments, max_claims)

    logger.info(f"📚 Processing {len(segments)} segments in batches of {batch_size}")

    all_claims = []

    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        claims_per_batch = max(3, max_claims // ((len(segments) // batch_size) + 1))

        batch_claims = await extract_claims(batch, claims_per_batch)
        all_claims.extend(batch_claims)

        if len(all_claims) >= max_claims:
            break

    # Sort by confidence and limit to max_claims
    all_claims.sort(key=lambda x: x['confidence'], reverse=True)
    return all_claims[:max_claims]
