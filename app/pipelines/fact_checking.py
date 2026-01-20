"""
Fact-checking orchestrator that coordinates the full pipeline.
"""
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from app.pipelines.claim_extraction import extract_claims
from app.pipelines.evidence_retrieval import retrieve_evidence_batch
from app.pipelines.claim_verification import verify_claims_batch
from app.services.gemini_service import gemini_service
from app.services.web_search_service import web_search_service
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)


FACT_CHECK_DISCLAIMER = """
⚠️ IMPORTANT DISCLAIMER:
This fact-checking tool analyzes claim VERIFIABILITY using web sources. It does not determine absolute truth.

• "Supported" = Found confirming evidence in multiple reliable sources
• "Refuted" = Found contradicting evidence in reliable sources
• "Inconclusive" = Insufficient or conflicting evidence

This is an AI-powered research tool. Always:
✓ Verify important claims through authoritative sources
✓ Consider context and nuance
✓ Understand that sources may be incomplete or biased
✓ Use this as a starting point, not a final verdict
"""


class FactCheckingOrchestrator:
    """
    Orchestrates the complete fact-checking pipeline.

    Pipeline steps:
    1. Extract factual claims from transcript
    2. Search for evidence (parallel)
    3. Verify each claim against evidence (sequential due to rate limits)
    4. Generate summary statistics
    """

    def __init__(self):
        self.start_time: Optional[datetime] = None

    def _check_prerequisites(self) -> Dict[str, bool]:
        """Check if required services are configured."""
        return {
            'gemini': gemini_service.is_configured(),
            'web_search': web_search_service.is_configured()
        }

    async def run_fact_check(
        self,
        segments: List[Dict],
        progress_callback: Optional[Callable[[str], None]] = None,
        max_claims: int = None
    ) -> Dict[str, Any]:
        """
        Run the complete fact-checking pipeline.

        Args:
            segments: Transcript segments from transcription (speaker, start, end, text)
            progress_callback: Optional callback for progress updates
            max_claims: Maximum claims to verify (defaults to settings)

        Returns:
            Fact-checking results dictionary with:
            - claims_found: Number of claims extracted
            - claims_verified: Number of claims verified
            - verifications: List of verification results
            - summary: Statistics summary
            - disclaimer: Legal/ethical disclaimer
            - processing_time_seconds: Total processing time
        """
        self.start_time = datetime.utcnow()

        if max_claims is None:
            max_claims = settings.MAX_CLAIMS_TO_VERIFY

        def update_progress(msg: str):
            logger.info(f"📊 {msg}")
            if progress_callback:
                progress_callback(msg)

        # Check prerequisites
        prereqs = self._check_prerequisites()
        if not prereqs['gemini']:
            logger.error("❌ Gemini API not configured")
            return self._create_error_response("Gemini API key not configured. Please set GEMINI_API_KEY.")

        # Step 1: Extract claims
        update_progress("Step 1/3: Extracting factual claims from transcript...")

        try:
            claims = await extract_claims(segments, max_claims)
        except Exception as e:
            logger.error(f"❌ Claim extraction failed: {e}")
            return self._create_error_response(f"Failed to extract claims: {str(e)}")

        if not claims:
            logger.info("ℹ️ No verifiable claims found in transcript")
            return self._create_empty_response("No verifiable factual claims were found in the transcript.")

        update_progress(f"Found {len(claims)} claims. Step 2/3: Searching for evidence...")

        # Step 2: Retrieve evidence (parallel)
        if prereqs['web_search']:
            try:
                evidence_map = await retrieve_evidence_batch(claims)
            except Exception as e:
                logger.error(f"❌ Evidence retrieval failed: {e}")
                evidence_map = {i: [] for i in range(len(claims))}
        else:
            logger.warning("⚠️ Web search not configured, proceeding without evidence")
            evidence_map = {i: [] for i in range(len(claims))}

        update_progress(f"Evidence gathered. Step 3/3: Verifying {len(claims)} claims...")

        # Step 3: Verify claims (sequential due to rate limits)
        def verification_progress(msg: str):
            update_progress(f"Step 3/3: {msg}")

        try:
            verifications = await verify_claims_batch(claims, evidence_map, verification_progress)
        except Exception as e:
            logger.error(f"❌ Claim verification failed: {e}")
            return self._create_error_response(f"Failed to verify claims: {str(e)}")

        # Calculate statistics
        summary = self._calculate_summary(verifications)

        # Calculate processing time
        processing_time = (datetime.utcnow() - self.start_time).total_seconds()

        update_progress("Fact-checking complete!")

        return {
            'claims_found': len(claims),
            'claims_verified': len(verifications),
            'verifications': verifications,
            'summary': summary,
            'disclaimer': FACT_CHECK_DISCLAIMER.strip(),
            'processing_time_seconds': round(processing_time, 1),
            'services_status': prereqs
        }

    def _calculate_summary(self, verifications: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics from verification results."""
        summary = {
            'supported': 0,
            'refuted': 0,
            'inconclusive': 0,
            'error': 0,
            'total': len(verifications),
            'average_confidence': 0.0
        }

        total_confidence = 0.0

        for v in verifications:
            verdict = v.get('verdict', 'error')
            if verdict in summary:
                summary[verdict] += 1
            else:
                summary['error'] += 1

            total_confidence += v.get('confidence', 0.0)

        if verifications:
            summary['average_confidence'] = round(total_confidence / len(verifications), 2)

        # Add percentages
        if summary['total'] > 0:
            summary['supported_pct'] = round(100 * summary['supported'] / summary['total'], 1)
            summary['refuted_pct'] = round(100 * summary['refuted'] / summary['total'], 1)
            summary['inconclusive_pct'] = round(100 * summary['inconclusive'] / summary['total'], 1)
        else:
            summary['supported_pct'] = 0
            summary['refuted_pct'] = 0
            summary['inconclusive_pct'] = 0

        return summary

    def _create_empty_response(self, message: str) -> Dict[str, Any]:
        """Create a response when no claims are found."""
        processing_time = 0
        if self.start_time:
            processing_time = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            'claims_found': 0,
            'claims_verified': 0,
            'verifications': [],
            'summary': {
                'supported': 0,
                'refuted': 0,
                'inconclusive': 0,
                'error': 0,
                'total': 0,
                'average_confidence': 0.0,
                'supported_pct': 0,
                'refuted_pct': 0,
                'inconclusive_pct': 0
            },
            'message': message,
            'disclaimer': FACT_CHECK_DISCLAIMER.strip(),
            'processing_time_seconds': round(processing_time, 1),
            'services_status': self._check_prerequisites()
        }

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create a response when an error occurs."""
        processing_time = 0
        if self.start_time:
            processing_time = (datetime.utcnow() - self.start_time).total_seconds()

        return {
            'claims_found': 0,
            'claims_verified': 0,
            'verifications': [],
            'summary': {
                'supported': 0,
                'refuted': 0,
                'inconclusive': 0,
                'error': 0,
                'total': 0,
                'average_confidence': 0.0,
                'supported_pct': 0,
                'refuted_pct': 0,
                'inconclusive_pct': 0
            },
            'error': error_message,
            'disclaimer': FACT_CHECK_DISCLAIMER.strip(),
            'processing_time_seconds': round(processing_time, 1),
            'services_status': self._check_prerequisites()
        }


# Global instance
fact_checker = FactCheckingOrchestrator()


async def fact_check_transcript(
    segments: List[Dict],
    progress_callback: Optional[Callable[[str], None]] = None,
    max_claims: int = None
) -> Dict[str, Any]:
    """
    Convenience function to run fact-checking on transcript segments.

    Args:
        segments: Transcript segments
        progress_callback: Progress update callback
        max_claims: Maximum claims to verify

    Returns:
        Fact-checking results
    """
    return await fact_checker.run_fact_check(segments, progress_callback, max_claims)
