# Task: Implement Fact-Checking Module (Part 2 of YouTube Transcription Project)

Read PROJECT_CONTEXT.md for full project context.

## Project Overview

This is the SECOND HALF of the YouTube transcription project. Part 1 (already complete) handles:
- Video transcription with faster-whisper
- Speaker diarization with pyannote.audio
- Output: Speaker-labeled transcript

Part 2 (THIS TASK) adds fact-checking capabilities:
- Extract factual claims from transcripts
- Verify claims using web search + Gemini LLM
- Show confidence scores, evidence, and reasoning

## Requirements

### Core Functionality

The fact-checking system should:

1. **Extract Claims** (using Gemini API)
   - Identify factual statements that can be verified
   - Support all claim types: historical events, statistics, scientific facts, current facts
   - Exclude opinions, predictions, subjective statements
   - Link each claim to timestamp and speaker

2. **Search for Evidence** (using existing web_search tool)
   - Generate effective search queries from claims
   - Retrieve top 5-10 relevant sources
   - Prioritize reliable sources (gov, edu, news organizations)
   - Fetch content from URLs for analysis

3. **Verify Claims** (using Gemini API)
   - Analyze evidence (both supporting AND counter-evidence)
   - Generate confidence scores (0-100%)
   - Provide clear reasoning for verdicts
   - Classify as: Supported / Refuted / Inconclusive

4. **Present Results**
   - Show claims with verdicts and confidence
   - Display supporting/refuting sources
   - Include explanations and caveats
   - User-friendly interface for general public

### Technical Architecture

Follow the existing project structure in `app/`:
```
app/
├── pipelines/
│   ├── claim_extraction.py      # NEW: Extract claims using Gemini
│   ├── evidence_retrieval.py    # NEW: Search and fetch evidence
│   ├── claim_verification.py    # NEW: Verify claims using Gemini
│   └── fact_checking.py         # NEW: Orchestrate full pipeline
│
├── services/
│   └── gemini_service.py        # NEW: Gemini API integration
│
├── api/routes/
│   └── fact_check.py            # NEW: POST /api/fact-check endpoint
│
├── models/
│   └── schemas.py               # UPDATE: Add fact-checking schemas
│
└── core/
    └── config.py                # UPDATE: Add GEMINI_API_KEY

static/
└── index.html                   # UPDATE: Add fact-check results UI
```

## Implementation Details

### 1. Gemini Service (`app/services/gemini_service.py`)

Create a service to interact with Gemini API:
```python
import google.generativeai as genai
import json
from typing import Dict, List
import logging

class GeminiService:
    """Service for interacting with Google Gemini API"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.logger = logging.getLogger(__name__)
    
    async def generate_json(
        self, 
        prompt: str, 
        temperature: float = 0.0
    ) -> Dict:
        """Generate JSON response from Gemini"""
        # Use async generation
        # Set response_mime_type to "application/json"
        # Parse and return JSON
        pass
    
    async def extract_claims(self, transcript: str) -> List[Dict]:
        """Extract factual claims from transcript"""
        pass
    
    async def verify_claim(
        self, 
        claim: str, 
        evidence: List[Dict]
    ) -> Dict:
        """Verify claim against evidence"""
        pass
```

**Important:**
- Use `google-generativeai` library (add to requirements.txt)
- Handle API errors gracefully
- Log all API calls
- Use JSON mode for structured outputs

### 2. Claim Extraction (`app/pipelines/claim_extraction.py`)

Extract verifiable claims from transcript:

**Claim Extraction Prompt Template:**
```python
CLAIM_EXTRACTION_PROMPT = """
You are a fact-checking assistant. Extract FACTUAL CLAIMS from this transcript.

RULES:
1. Extract ONLY verifiable factual statements
2. Include claims about:
   - Historical events (with dates/years)
   - Statistics and numbers
   - Scientific facts
   - Current events and facts
3. EXCLUDE:
   - Opinions ("I think", "I believe")
   - Predictions ("will happen", "going to")
   - Subjective statements ("beautiful", "good", "bad")
   - Questions
   - Personal anecdotes without verifiable facts
4. Make claims self-contained and specific

TRANSCRIPT:
{transcript}

OUTPUT (JSON):
{{
  "claims": [
    {{
      "claim": "Exact factual statement",
      "timestamp": "MM:SS or seconds",
      "speaker": "SPEAKER_XX",
      "type": "historical_event|statistic|scientific_fact|current_fact",
      "key_entities": ["entity1", "entity2"],
      "contains_number": true/false
    }}
  ]
}}
"""
```

**Function signature:**
```python
async def extract_claims(
    transcript_segments: List[Dict],
    gemini_service: GeminiService
) -> List[Dict]:
    """
    Extract factual claims from speaker-labeled transcript
    
    Args:
        transcript_segments: List of {speaker, start, end, text}
        gemini_service: Initialized Gemini service
    
    Returns:
        List of extracted claims with metadata
    """
```

**Implementation notes:**
- Combine transcript segments into formatted text
- Include speaker labels and timestamps
- Call Gemini with extraction prompt
- Parse JSON response
- Validate claim structure
- Handle extraction errors gracefully

### 3. Evidence Retrieval (`app/pipelines/evidence_retrieval.py`)

Search for evidence using web search:
```python
async def search_evidence_for_claim(
    claim: Dict,
    web_search_tool: callable
) -> List[Dict]:
    """
    Search for evidence supporting or refuting a claim
    
    Args:
        claim: Claim dict with 'claim' text and metadata
        web_search_tool: Web search function
    
    Returns:
        List of evidence documents with content
    """
```

**Implementation:**
- Generate effective search query from claim
- Use existing web_search tool (already available in project)
- Retrieve top 5-10 results
- Fetch content using web_fetch tool
- Extract source reliability (gov/edu/news/social media)
- Limit content length (max 2000 chars per source)
- Return structured evidence documents

**Search query generation:**
```python
def generate_search_query(claim: Dict) -> str:
    """Generate effective search query"""
    # For statistics: Add "official statistics" or "data"
    # For historical events: Add key entities + dates
    # For scientific facts: Add "scientific consensus"
    # For current facts: Add "verification" or "fact check"
```

**Source reliability scoring:**
```python
def assess_source_reliability(url: str, title: str) -> str:
    """Classify source reliability"""
    # high_reliability: .gov, .edu, wikipedia, WHO, UN, etc.
    # news_reliable: BBC, Reuters, AP, major newspapers
    # news_general: Other news sites
    # social_media: Twitter, Facebook, Reddit (low reliability)
    # unknown: Other sources
```

### 4. Claim Verification (`app/pipelines/claim_verification.py`)

Verify claims using Gemini and evidence:

**Verification Prompt Template:**
```python
VERIFICATION_PROMPT = """
You are an expert fact-checker. Verify this claim using the provided evidence.

CLAIM:
{claim}

EVIDENCE:
{evidence}

INSTRUCTIONS:
1. Analyze if evidence SUPPORTS, REFUTES, or is INCONCLUSIVE
2. Consider BOTH supporting AND counter-evidence
3. Evaluate source reliability
4. Look for consensus across multiple sources
5. Note contradictions or uncertainties
6. Be conservative - if uncertain, mark "inconclusive"

DEFINITIONS:
- "supported": Multiple reliable sources confirm this claim
- "refuted": Reliable sources contradict this claim
- "inconclusive": Insufficient/conflicting evidence or claim too vague

OUTPUT (JSON):
{{
  "verdict": "supported|refuted|inconclusive",
  "confidence": 0-100,
  "reasoning": "Clear explanation of verdict (2-3 sentences)",
  "supporting_evidence": [
    {{"source": "URL", "excerpt": "relevant quote"}}
  ],
  "counter_evidence": [
    {{"source": "URL", "excerpt": "contradicting quote"}}
  ],
  "key_finding": "Most important finding from analysis",
  "caveats": "Important limitations or context (if any)"
}}
"""
```

**Function signature:**
```python
async def verify_claim(
    claim: Dict,
    evidence: List[Dict],
    gemini_service: GeminiService
) -> Dict:
    """
    Verify claim using evidence and Gemini
    
    Args:
        claim: Claim to verify
        evidence: List of evidence documents
        gemini_service: Gemini service instance
    
    Returns:
        Verification result with verdict, confidence, reasoning
    """
```

**Implementation:**
- Format evidence for Gemini (include URLs, reliability, content)
- Call Gemini with verification prompt
- Parse structured response
- Add claim metadata to result
- Handle cases with no evidence found
- Log verification decisions

### 5. Fact-Checking Orchestrator (`app/pipelines/fact_checking.py`)

Coordinate the full fact-checking pipeline:
```python
async def fact_check_transcript(
    transcript_segments: List[Dict],
    video_title: str,
    gemini_service: GeminiService,
    web_search_tool: callable,
    web_fetch_tool: callable
) -> Dict:
    """
    Complete fact-checking pipeline
    
    Steps:
    1. Extract claims from transcript
    2. For each claim:
       a. Search for evidence
       b. Verify claim
    3. Generate summary statistics
    4. Return complete results
    
    Returns:
        FactCheckResponse with all claims and verdicts
    """
```

**Include:**
- Progress logging for each step
- Error handling (continue if one claim fails)
- Summary statistics (total, supported, refuted, inconclusive)
- Overall assessment/summary
- Performance timing

### 6. Pydantic Schemas (`app/models/schemas.py`)

Add these schemas:
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class EvidenceSource(BaseModel):
    url: str
    title: str
    excerpt: str
    reliability: str

class ClaimVerification(BaseModel):
    claim: str
    timestamp: str
    speaker: str
    claim_type: str
    verdict: Literal["supported", "refuted", "inconclusive"]
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    supporting_evidence: List[EvidenceSource]
    counter_evidence: List[EvidenceSource]
    key_finding: str
    caveats: Optional[str]

class FactCheckRequest(BaseModel):
    youtube_url: str
    language: Optional[str] = None
    enable_fact_check: bool = True

class FactCheckResponse(BaseModel):
    video_title: str
    duration: float
    language: str
    
    # Transcript results
    transcript_segments: List[Dict]
    
    # Fact-check results
    total_claims: int
    supported_claims: int
    refuted_claims: int
    inconclusive_claims: int
    claims: List[ClaimVerification]
    
    # Overall assessment
    summary: str
    disclaimer: str
```

### 7. API Endpoint (`app/api/routes/fact_check.py`)

Create endpoint for complete pipeline:
```python
from fastapi import APIRouter, HTTPException
from app.models.schemas import FactCheckRequest, FactCheckResponse

router = APIRouter()

@router.post("/api/transcribe-and-fact-check", response_model=FactCheckResponse)
async def transcribe_and_fact_check(request: FactCheckRequest):
    """
    Complete pipeline: Transcribe + Diarize + Fact-Check
    
    Steps:
    1. Download and extract audio (existing pipeline)
    2. Transcribe with speaker diarization (existing pipeline)
    3. Extract and verify claims (NEW)
    4. Return combined results
    """
```

**Include:**
- Input validation
- Call existing transcription pipeline
- Call new fact-checking pipeline
- Combine results
- Error handling with helpful messages
- Request timeout handling (long processing)

### 8. Configuration (`app/core/config.py`)

Update settings:
```python
class Settings(BaseSettings):
    # Existing settings...
    HUGGINGFACE_TOKEN: str
    
    # NEW: Gemini API
    GEMINI_API_KEY: str
    
    # NEW: Fact-checking settings
    ENABLE_FACT_CHECKING: bool = True
    MAX_CLAIMS_TO_VERIFY: int = 50  # Limit for performance
    EVIDENCE_SOURCES_PER_CLAIM: int = 5
    
    # NEW: Disclaimer
    FACT_CHECK_DISCLAIMER: str = """
    ⚠️ IMPORTANT DISCLAIMER:
    This tool checks claim VERIFIABILITY using web sources, not absolute truth.
    
    - "Supported" = Found confirming evidence in multiple reliable sources
    - "Refuted" = Found contradicting evidence in reliable sources  
    - "Inconclusive" = Insufficient or conflicting evidence
    
    This is an educational/research tool. Always:
    ✓ Check sources yourself
    ✓ Consider context and nuance
    ✓ Understand limitations
    ✓ Don't rely solely on automated fact-checking
    """
```

### 9. Frontend Updates (`static/index.html` and `static/js/app.js`)

Update the web interface to show fact-check results:

**HTML additions:**
```html
<!-- Add checkbox to enable fact-checking -->
<label>
  <input type="checkbox" id="enableFactCheck" checked>
  Enable Fact-Checking
</label>

<!-- Results section -->
<div id="factCheckResults" style="display: none;">
  <h2>Fact-Check Results</h2>
  
  <!-- Summary stats -->
  <div class="fact-check-summary">
    <div class="stat">Total Claims: <span id="totalClaims"></span></div>
    <div class="stat supported">Supported: <span id="supportedClaims"></span></div>
    <div class="stat refuted">Refuted: <span id="refutedClaims"></span></div>
    <div class="stat inconclusive">Inconclusive: <span id="inconclusiveClaims"></span></div>
  </div>
  
  <!-- Disclaimer -->
  <div class="disclaimer"></div>
  
  <!-- Claims list -->
  <div id="claimsList"></div>
</div>
```

**JavaScript updates:**
- Call `/api/transcribe-and-fact-check` endpoint
- Display summary statistics
- Render each claim with:
  - Claim text with timestamp
  - Verdict badge (green/red/yellow)
  - Confidence score as progress bar
  - Reasoning
  - Expandable evidence section (supporting + counter)
  - Links to sources
- Add filtering (show all / only verified / only refuted)
- Color-code by verdict

**CSS styling:**
- Green for supported claims
- Red for refuted claims
- Yellow/orange for inconclusive
- Confidence meter/bar
- Source links styled as badges
- Responsive design

### 10. Dependencies (`requirements.txt`)

Add:
```txt
# NEW: Google Gemini
google-generativeai==0.8.3
```

### 11. Environment Variables (`.env.example`)

Add:
```bash
# NEW: Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Fact-checking settings
ENABLE_FACT_CHECKING=true
MAX_CLAIMS_TO_VERIFY=50
```

## Important Implementation Notes

### Error Handling

1. **Gemini API Errors:**
   - Rate limits: Implement retry with backoff
   - Invalid API key: Clear error message
   - JSON parsing errors: Fallback gracefully

2. **Web Search Errors:**
   - No results found: Mark as inconclusive
   - Fetch timeout: Skip source, continue with others
   - Invalid URLs: Log and skip

3. **Pipeline Errors:**
   - If claim extraction fails: Return transcript only
   - If one claim verification fails: Continue with others
   - If entire fact-check fails: Return transcript with error message

### Performance Considerations

1. **API Call Optimization:**
   - Batch claims where possible
   - Cache search results
   - Limit number of claims verified (MAX_CLAIMS_TO_VERIFY)
   - Show progress to user

2. **Async Processing:**
   - Use asyncio for parallel claim verification
   - Don't block on slow searches
   - Implement timeout per claim (30 seconds max)

### Quality Assurance

1. **Prompt Engineering:**
   - Test prompts with edge cases
   - Handle ambiguous claims
   - Ensure JSON output is valid

2. **Source Reliability:**
   - Prioritize high-quality sources
   - Require multiple sources for "supported"
   - Flag low-reliability sources

3. **User Experience:**
   - Clear, non-technical language
   - Prominent disclaimer
   - Easy-to-understand verdicts
   - Links to original sources

## Testing Requirements

Create tests for:

1. **Unit Tests:**
   - Claim extraction with sample transcripts
   - Search query generation
   - Source reliability scoring
   - Verification logic

2. **Integration Tests:**
   - Full pipeline with mock Gemini responses
   - API endpoint with sample video

3. **Edge Cases:**
   - Transcript with no factual claims
   - Claims with no search results
   - Contradictory evidence
   - Very short/long claims

## Documentation

Update `README.md` with:

1. **Fact-Checking Feature:**
   - How it works
   - What claims it can verify
   - Limitations and disclaimers

2. **Setup Instructions:**
   - How to get Gemini API key
   - Environment variable configuration

3. **Usage Examples:**
   - Sample API requests
   - Interpretation of results

## Ethical Considerations

**CRITICAL:**

1. **Never claim absolute truth:**
   - Always say "verifiable" not "true"
   - Show confidence scores, not binary true/false
   - Emphasize this checks sources, not truth

2. **Transparent limitations:**
   - Cannot verify everything
   - Subject to source bias
   - Context matters
   - Nuance may be lost

3. **User responsibility:**
   - Tool assists research, doesn't replace judgment
   - Users should check sources themselves
   - Understand this is educational/research tool

## Success Criteria

The implementation is successful if:

1. ✅ Extracts relevant factual claims from transcripts
2. ✅ Finds appropriate evidence sources
3. ✅ Provides reasonable verdicts with justification
4. ✅ Shows confidence scores and sources
5. ✅ Handles errors gracefully
6. ✅ UI is clear and user-friendly for general public
7. ✅ Includes prominent disclaimers
8. ✅ Works with both English and Thai content
9. ✅ Performance is acceptable (<2 min total for 10-min video)
10. ✅ Code follows project structure and style

## Implementation Order

Suggest implementing in this order:

1. Gemini service (basic API integration)
2. Claim extraction pipeline + test
3. Evidence retrieval + test
4. Claim verification + test
5. Fact-checking orchestrator
6. API endpoint
7. Frontend updates
8. Error handling improvements
9. Documentation
10. Final testing

## Additional Notes

- Follow existing code style and patterns in the project
- Use emoji logging indicators as in existing code
- Add comprehensive docstrings
- Handle both English and Thai content
- Consider rate limits (Gemini free tier: 15 requests/minute)
- Log all important operations for debugging
- Keep prompts modular and easy to update

---

Implement the complete fact-checking system following these specifications. Ensure it integrates seamlessly with the existing transcription pipeline and provides accurate, transparent, and ethically responsible fact-checking capabilities for general public use.