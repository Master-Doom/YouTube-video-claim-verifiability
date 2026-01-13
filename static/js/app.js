// YouTube Transcription Service - Frontend JavaScript

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

// State
let currentVideoId = null;
let currentTranscript = [];

// Form submission handler
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const youtubeUrl = document.getElementById('youtubeUrl').value.trim();
    const language = document.getElementById('language').value || null;

    if (!youtubeUrl) {
        showError('Please enter a YouTube URL');
        return;
    }

    await transcribeVideo(youtubeUrl, language);
});

// Copy transcript button handler
copyTranscriptBtn.addEventListener('click', () => {
    copyTranscriptToClipboard();
});

// Main transcription function
async function transcribeVideo(youtubeUrl, language) {
    // Hide previous results and errors
    hideError();
    hideResults();
    showLoading('Initializing...');

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

        // Update loading message
        updateLoadingStep('Downloading and extracting audio...');

        // Make API request
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Transcription failed');
        }

        updateLoadingStep('Processing complete!');

        // Parse response
        const data = await response.json();
        currentTranscript = data.segments;

        // Display results
        displayResults(data);

    } catch (error) {
        console.error('Transcription error:', error);
        showError(error.message || 'An unexpected error occurred');
    } finally {
        hideLoading();
        submitBtn.disabled = false;
    }
}

// Display results
function displayResults(data) {
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

    // Render transcript
    renderTranscript(data.segments);

    // Show results section
    showResults();
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
    const ms = Math.floor((seconds % 1) * 10);
    return `${minutes}:${secs.toString().padStart(2, '0')}.${ms}`;
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
}

// Initialize
console.log('YouTube Transcription Service initialized');
