// ClearFrame - YouTube Transcription & Fact-Check Service

// DOM Elements
const form = document.getElementById('transcribeForm');
const submitBtn = document.getElementById('submitBtn');
const loadingIndicator = document.getElementById('loadingIndicator');
const loadingStep = document.getElementById('loadingStep');
const errorDisplay = document.getElementById('errorDisplay');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('resultsSection');
const videoTitle = document.getElementById('videoTitle');
const videoDuration = document.getElementById('videoDuration');
const videoLanguage = document.getElementById('videoLanguage');
const totalSpeakers = document.getElementById('totalSpeakers');
const videoPlayer = document.getElementById('videoPlayer');
const transcript = document.getElementById('transcript');
const copyTranscriptBtn = document.getElementById('copyTranscript');

// Fact-check elements
const factCheckSection = document.getElementById('factCheckSection');
const totalClaims = document.getElementById('totalClaims');
const supportedClaims = document.getElementById('supportedClaims');
const refutedClaims = document.getElementById('refutedClaims');
const inconclusiveClaims = document.getElementById('inconclusiveClaims');
const claimsList = document.getElementById('claimsList');
const claimsFilter = document.getElementById('claimsFilter');
const enableFactCheck = document.getElementById('enableFactCheck');

// State
let currentVideoId = null;
let currentTranscript = [];
let currentFactCheckData = null;

// Form submission handler
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const youtubeUrl = document.getElementById('youtubeUrl').value.trim();
    const language = document.getElementById('language').value || null;
    const factCheckEnabled = enableFactCheck.checked;

    if (!youtubeUrl) {
        showError('Please enter a YouTube URL');
        return;
    }

    await transcribeVideo(youtubeUrl, language, factCheckEnabled);
});

// Copy transcript button handler
copyTranscriptBtn.addEventListener('click', () => {
    copyTranscriptToClipboard();
});

// Claims filter handler
claimsFilter.addEventListener('change', () => {
    if (currentFactCheckData) {
        renderClaims(currentFactCheckData.verifications, claimsFilter.value);
    }
});

// Main transcription function
async function transcribeVideo(youtubeUrl, language, factCheckEnabled) {
    // Hide previous results and errors
    hideError();
    hideResults();
    showLoading('Submitting job...');

    // Disable submit button
    submitBtn.disabled = true;

    try {
        // Extract video ID for player
        currentVideoId = extractVideoId(youtubeUrl);

        // Prepare request payload
        const payload = {
            youtube_url: youtubeUrl
        };

        if (language) {
            payload.language = language;
        }

        // Choose endpoint based on fact-check checkbox
        const endpoint = factCheckEnabled ? '/api/transcribe-and-fact-check' : '/api/transcribe';

        // Submit job
        const submitResponse = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!submitResponse.ok) {
            const errorData = await submitResponse.json();
            throw new Error(errorData.detail || 'Failed to submit job');
        }

        const submitData = await submitResponse.json();
        const jobId = submitData.job_id;
        console.log(`Job submitted: ${jobId} (fact-check: ${factCheckEnabled})`);

        // Start polling for results
        updateLoadingStep('Processing... Please wait.');
        await pollForResults(jobId, factCheckEnabled);

    } catch (error) {
        console.error('Processing error:', error);
        showError(error.message || 'An unexpected error occurred');
        hideLoading();
        submitBtn.disabled = false;
    }
}

// Poll for job results
async function pollForResults(jobId, factCheckEnabled) {
    const pollIntervalMs = 2000; // Poll every 2 seconds
    const maxAttempts = 600; // Max 20 minutes for fact-checking
    let attempts = 0;

    while (attempts < maxAttempts) {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);

            if (!response.ok) {
                throw new Error('Failed to get job status');
            }

            const job = await response.json();
            console.log(`Job ${jobId} status: ${job.status}, progress: ${job.progress}`);

            // Update loading message with progress
            updateLoadingStep(job.progress || 'Processing...');

            if (job.status === 'completed') {
                // Success! Display results
                currentTranscript = job.result.segments;
                displayResults(job.result, factCheckEnabled);
                hideLoading();
                submitBtn.disabled = false;
                return;
            } else if (job.status === 'failed') {
                // Job failed
                throw new Error(job.error || 'Processing failed');
            }

            // Still processing, wait and poll again
            await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
            attempts++;

        } catch (error) {
            console.error('Polling error:', error);
            showError(error.message || 'Error checking job status');
            hideLoading();
            submitBtn.disabled = false;
            return;
        }
    }

    // Timeout
    showError('Processing timed out. Please try again with a shorter video.');
    hideLoading();
    submitBtn.disabled = false;
}

// Display results
function displayResults(data, factCheckEnabled) {
    // Set video info
    videoTitle.textContent = data.video_title;
    videoDuration.textContent = formatDuration(data.duration);
    videoLanguage.textContent = getLanguageName(data.language);
    totalSpeakers.textContent = data.total_speakers;

    // Embed YouTube player
    if (currentVideoId) {
        videoPlayer.innerHTML = `
            <iframe
                src="https://www.youtube.com/embed/${currentVideoId}"
                frameborder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen
            ></iframe>
        `;
    }

    // Display fact-check results if available
    if (factCheckEnabled && data.fact_check) {
        displayFactCheckResults(data.fact_check);
        factCheckSection.style.display = 'block';
    } else {
        factCheckSection.style.display = 'none';
    }

    // Render transcript
    renderTranscript(data.segments);

    // Show results section
    showResults();
}

// Display fact-check results
function displayFactCheckResults(factCheck) {
    currentFactCheckData = factCheck;

    const summary = factCheck.summary || {};

    // Update summary stats
    totalClaims.textContent = summary.total || 0;
    supportedClaims.textContent = summary.supported || 0;
    refutedClaims.textContent = summary.refuted || 0;
    inconclusiveClaims.textContent = summary.inconclusive || 0;

    // Render claims
    renderClaims(factCheck.verifications || [], 'all');
}

// Render claims list
function renderClaims(verifications, filter) {
    claimsList.innerHTML = '';

    if (!verifications || verifications.length === 0) {
        claimsList.innerHTML = '<p class="no-claims">No factual claims were found in this video.</p>';
        return;
    }

    const filteredClaims = filter === 'all'
        ? verifications
        : verifications.filter(v => v.verdict === filter);

    if (filteredClaims.length === 0) {
        claimsList.innerHTML = `<p class="no-claims">No ${filter} claims found.</p>`;
        return;
    }

    filteredClaims.forEach((verification, index) => {
        const claimCard = createClaimCard(verification, index);
        claimsList.appendChild(claimCard);
    });
}

// Create a claim card element
function createClaimCard(verification, index) {
    const claim = verification.claim || {};
    const verdict = verification.verdict || 'inconclusive';
    const confidence = verification.confidence || 0;

    const card = document.createElement('div');
    card.className = `claim-card verdict-${verdict}`;

    // Header with verdict badge
    const header = document.createElement('div');
    header.className = 'claim-header';
    header.innerHTML = `
        <span class="verdict-badge ${verdict}">${verdict.toUpperCase()}</span>
        <span class="confidence-score">Confidence: ${Math.round(confidence * 100)}%</span>
    `;

    // Claim text
    const claimText = document.createElement('div');
    claimText.className = 'claim-text';
    claimText.textContent = `"${claim.claim_text || 'No claim text'}"`;

    // Claim metadata
    const meta = document.createElement('div');
    meta.className = 'claim-meta';
    const timestamp = formatTimestamp(claim.start_time || 0);
    const speaker = formatSpeakerLabel(claim.speaker || 'UNKNOWN');
    meta.innerHTML = `<span>${speaker}</span> <span class="claim-timestamp">@ ${timestamp}</span>`;

    // Explanation
    const explanation = document.createElement('div');
    explanation.className = 'claim-explanation';
    explanation.textContent = verification.explanation || '';

    // Evidence section (collapsible)
    const evidenceSection = createEvidenceSection(verification);

    // Assemble card
    card.appendChild(header);
    card.appendChild(claimText);
    card.appendChild(meta);
    card.appendChild(explanation);
    if (evidenceSection) {
        card.appendChild(evidenceSection);
    }

    return card;
}

// Create evidence section
function createEvidenceSection(verification) {
    const supporting = verification.supporting_evidence || [];
    const counter = verification.counter_evidence || [];

    if (supporting.length === 0 && counter.length === 0) {
        return null;
    }

    const section = document.createElement('div');
    section.className = 'evidence-section';

    // Toggle button
    const toggle = document.createElement('button');
    toggle.className = 'evidence-toggle';
    toggle.textContent = `Show Evidence (${supporting.length + counter.length} sources)`;
    toggle.onclick = () => {
        const content = section.querySelector('.evidence-content');
        const isHidden = content.style.display === 'none';
        content.style.display = isHidden ? 'block' : 'none';
        toggle.textContent = isHidden
            ? `Hide Evidence (${supporting.length + counter.length} sources)`
            : `Show Evidence (${supporting.length + counter.length} sources)`;
    };

    // Evidence content (hidden by default)
    const content = document.createElement('div');
    content.className = 'evidence-content';
    content.style.display = 'none';

    // Supporting evidence
    if (supporting.length > 0) {
        const supportingDiv = document.createElement('div');
        supportingDiv.className = 'evidence-group supporting';
        supportingDiv.innerHTML = `<h5>Supporting Evidence</h5>`;
        supporting.forEach(e => {
            supportingDiv.appendChild(createEvidenceItem(e, 'supporting'));
        });
        content.appendChild(supportingDiv);
    }

    // Counter evidence
    if (counter.length > 0) {
        const counterDiv = document.createElement('div');
        counterDiv.className = 'evidence-group counter';
        counterDiv.innerHTML = `<h5>Counter Evidence</h5>`;
        counter.forEach(e => {
            counterDiv.appendChild(createEvidenceItem(e, 'counter'));
        });
        content.appendChild(counterDiv);
    }

    section.appendChild(toggle);
    section.appendChild(content);

    return section;
}

// Sanitize string for safe HTML insertion
function sanitizeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Create evidence item
function createEvidenceItem(evidence, type) {
    const item = document.createElement('div');
    item.className = `evidence-item ${type}`;

    const url = evidence.source_url || '#';
    const title = evidence.source_title || extractDomain(url);
    const quote = evidence.quote || 'No quote available';

    item.innerHTML = `
        <a href="${sanitizeHTML(url)}" target="_blank" rel="noopener noreferrer" class="evidence-source">${sanitizeHTML(title)}</a>
        <p class="evidence-quote">"${sanitizeHTML(quote)}"</p>
    `;

    return item;
}

// Extract domain from URL
function extractDomain(url) {
    try {
        const domain = new URL(url).hostname;
        return domain.replace('www.', '');
    } catch {
        return url;
    }
}

// Render transcript segments
function renderTranscript(segments) {
    transcript.innerHTML = '';

    segments.forEach((segment, index) => {
        const segmentDiv = document.createElement('div');
        segmentDiv.className = `segment speaker-${segment.speaker}`;

        const header = document.createElement('div');
        header.className = 'segment-header';

        const speakerLabel = document.createElement('span');
        speakerLabel.className = 'speaker-label';
        speakerLabel.textContent = formatSpeakerLabel(segment.speaker);

        const timestamp = document.createElement('span');
        timestamp.className = 'timestamp';
        timestamp.textContent = `${formatTimestamp(segment.start)} - ${formatTimestamp(segment.end)}`;

        header.appendChild(speakerLabel);
        header.appendChild(timestamp);

        const text = document.createElement('div');
        text.className = 'segment-text';
        text.textContent = segment.text;

        segmentDiv.appendChild(header);
        segmentDiv.appendChild(text);

        transcript.appendChild(segmentDiv);
    });
}

// Copy transcript to clipboard
function copyTranscriptToClipboard() {
    let text = '';

    currentTranscript.forEach(segment => {
        const speaker = formatSpeakerLabel(segment.speaker);
        const time = `[${formatTimestamp(segment.start)}]`;
        text += `${speaker} ${time}: ${segment.text}\n\n`;
    });

    navigator.clipboard.writeText(text).then(() => {
        // Temporary success feedback
        const originalText = copyTranscriptBtn.textContent;
        copyTranscriptBtn.textContent = 'Copied!';
        setTimeout(() => {
            copyTranscriptBtn.textContent = originalText;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        showError('Failed to copy transcript');
    });
}

// Utility Functions

function extractVideoId(url) {
    // Extract video ID from various YouTube URL formats
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/,
        /youtube\.com\/embed\/([^&\n?#]+)/,
        /youtube\.com\/v\/([^&\n?#]+)/
    ];

    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }

    return null;
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatTimestamp(seconds) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatSpeakerLabel(speaker) {
    if (speaker === 'UNKNOWN') {
        return 'Unknown Speaker';
    }
    // Convert SPEAKER_00 to Speaker 1, SPEAKER_01 to Speaker 2, etc.
    const match = speaker.match(/SPEAKER_(\d+)/);
    if (match) {
        const num = parseInt(match[1]) + 1;
        return `Speaker ${num}`;
    }
    return speaker;
}

function getLanguageName(code) {
    const languages = {
        'en': 'English',
        'th': 'Thai',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'ja': 'Japanese',
        'ko': 'Korean',
        'zh': 'Chinese',
        'ar': 'Arabic',
        'hi': 'Hindi'
    };
    return languages[code] || code.toUpperCase();
}

// UI State Management

function showLoading(message) {
    loadingStep.textContent = message;
    loadingIndicator.style.display = 'block';
}

function hideLoading() {
    loadingIndicator.style.display = 'none';
}

function updateLoadingStep(message) {
    loadingStep.textContent = message;
}

function showError(message) {
    errorMessage.textContent = message;
    errorDisplay.style.display = 'block';
    // Scroll to error
    errorDisplay.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
    errorDisplay.style.display = 'none';
}

function showResults() {
    resultsSection.style.display = 'block';
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function hideResults() {
    resultsSection.style.display = 'none';
    factCheckSection.style.display = 'none';
}

// Initialize
console.log('ClearFrame - YouTube Transcription & Fact-Check Service initialized');
