# YouTube Transcription Service

A production-ready FastAPI-based service that performs speaker-diarized transcription of YouTube videos using state-of-the-art AI models.

## Features

- **YouTube Audio Extraction**: Download and extract audio from any YouTube video using `yt-dlp` and `ffmpeg`
- **Speaker Diarization**: Identify and label different speakers using `pyannote.audio`
- **Multi-language Transcription**: Transcribe audio with automatic language detection using `faster-whisper`
- **Supported Languages**: English, Thai (easily extensible to other languages)
- **Smart Alignment**: Align speaker labels with transcript segments based on time overlap
- **Web Interface**: Clean, responsive UI for easy interaction
- **RESTful API**: Well-documented API endpoints for integration
- **Docker Support**: Containerized deployment with Docker Compose
- **CPU-Optimized Design**: Optimized for CPU-only deployment with small Docker images

## Technology Stack

- **Backend**: FastAPI (Python 3.10+)
- **ASR**: faster-whisper
- **Diarization**: pyannote.audio
- **Audio Extraction**: yt-dlp + ffmpeg
- **Frontend**: HTML + vanilla JavaScript (no frameworks)
- **Containerization**: Docker + docker-compose

## Project Structure

```
youtube-transcription-service/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── transcribe.py      # Transcription endpoint
│   │   │   └── health.py          # Health check endpoint
│   │   └── dependencies.py         # FastAPI dependencies
│   ├── core/
│   │   ├── config.py              # Configuration management
│   │   └── constants.py           # Application constants
│   ├── models/
│   │   └── schemas.py             # Pydantic models
│   ├── pipelines/
│   │   ├── audio_extraction.py    # YouTube download & extraction
│   │   ├── diarization.py         # Speaker diarization
│   │   ├── transcription.py       # Audio transcription
│   │   ├── alignment.py           # Speaker-transcript alignment
│   │   └── orchestrator.py        # Pipeline coordination
│   ├── services/
│   │   └── model_loader.py        # Model loading & caching
│   ├── utils/
│   │   ├── logger.py              # Logging configuration
│   │   ├── file_utils.py          # File operations
│   │   └── audio_utils.py         # Audio processing utilities
│   └── main.py                     # FastAPI application
├── static/
│   ├── index.html                  # Web interface
│   ├── css/
│   │   └── styles.css             # Styling
│   └── js/
│       └── app.js                 # Frontend logic
├── temp/                           # Temporary audio files
├── models/                         # Cached ML models
├── Dockerfile                      # Docker configuration
├── docker-compose.yml              # Docker Compose configuration
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
└── README.md                       # This file
```

## Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.10+ with pip
- HuggingFace account and API token
- ffmpeg (automatically installed in Docker)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd youtube-transcription-service
```

### 2. Get HuggingFace Token

1. Create a HuggingFace account at https://huggingface.co/
2. Generate an API token at https://huggingface.co/settings/tokens
3. Accept the terms for the following models:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your HuggingFace token:

```env
HUGGINGFACE_TOKEN=your_actual_token_here
WHISPER_MODEL_SIZE=base
MAX_VIDEO_LENGTH_MINUTES=120
```

### 4. Run with Docker (Recommended)

```bash
# Build and start the service
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

The service will be available at:
- Web Interface: http://localhost:8000/index.html
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 5. Alternative: Run without Docker

```bash
# Install system dependencies
sudo apt-get install ffmpeg  # On Ubuntu/Debian
brew install ffmpeg           # On macOS

# Create virtual environment
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Usage

### Web Interface

1. Open http://localhost:8000/index.html in your browser
2. Enter a YouTube URL
3. Select language (or leave as "Auto-detect")
4. Click "Transcribe Video"
5. Wait for processing (may take a few minutes depending on video length)
6. View the speaker-labeled transcript

### API Usage

#### Transcribe a Video

```bash
curl -X POST "http://localhost:8000/api/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "language": "en"
  }'
```

Response:

```json
{
  "video_title": "Sample Video Title",
  "duration": 300.5,
  "language": "en",
  "total_speakers": 2,
  "segments": [
    {
      "speaker": "SPEAKER_00",
      "start": 0.0,
      "end": 5.5,
      "text": "Hello, welcome to this video."
    },
    {
      "speaker": "SPEAKER_01",
      "start": 5.6,
      "end": 10.2,
      "text": "Thank you for having me."
    }
  ]
}
```

#### Health Check

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy",
  "models_loaded": true,
  "whisper_model": "base",
  "diarization_available": true
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HUGGINGFACE_TOKEN` | HuggingFace API token (required) | - |
| `TEMP_DIR` | Directory for temporary audio files | `./temp` |
| `MODELS_DIR` | Directory for cached models | `./models` |
| `WHISPER_MODEL_SIZE` | Whisper model size | `base` |
| `MAX_VIDEO_LENGTH_MINUTES` | Maximum video length in minutes | `120` |
| `SUPPORTED_LANGUAGES` | Comma-separated language codes | `en,th` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Whisper Model Sizes

Available model sizes (trade-off between speed and accuracy):

**CPU Performance (4 vCPU, 1-hour video):**

| Model | Parameters | Processing Time | Accuracy | RAM Usage | Recommendation |
|-------|-----------|-----------------|----------|-----------|----------------|
| `tiny` | 39M | 3-5 minutes | Acceptable | ~2GB | Fast processing |
| `base` | 74M | 5-10 minutes | Good | ~3GB | **Recommended** |
| `small` | 244M | 15-30 minutes | Better | ~4GB | High accuracy needs |
| `medium` | 769M | 45-90 minutes | High | ~6GB | Not recommended for CPU |
| `large-v2` | 1550M | 90+ minutes | Very high | ~8GB | Not recommended for CPU |
| `large-v3` | 1550M | 90+ minutes | Highest | ~8GB | Not recommended for CPU |

**Note**: This service uses CPU-only PyTorch (~200MB) instead of the full CUDA version (~900MB) for faster builds and smaller Docker images.

## Docker Commands

```bash
# Start the service
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Rebuild after code changes
docker-compose up --build

# Remove everything including volumes
docker-compose down -v
```

## API Documentation

Once the service is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### Code Structure

The application follows a modular architecture:

1. **Pipelines**: Independent processing steps (extraction, diarization, transcription, alignment)
2. **Services**: Model loading and caching
3. **API Routes**: FastAPI endpoints
4. **Utils**: Shared utility functions
5. **Core**: Configuration and constants

### Adding New Languages

1. Update `SUPPORTED_LANGUAGES` in `.env`
2. Whisper supports 99+ languages out of the box
3. Add language option to frontend if needed

## Performance Optimization

### CPU-Only Deployment (Current Configuration)

This service is optimized for CPU-only deployment using PyTorch CPU builds:

**Benefits:**
- ✅ Smaller downloads: ~200MB vs ~900MB for CUDA version
- ✅ Faster Docker builds: 5-10 min vs 15-30+ min
- ✅ Smaller images: ~3.5GB vs ~4.5GB
- ✅ Works on any server without GPU requirements

**Optimization Tips:**
1. **Model Selection**: Use `base` model for best speed/accuracy balance
2. **Video Length**: Consider splitting videos > 2 hours for better performance
3. **Server Resources**: Recommended minimum 4 vCPU / 8GB RAM
4. **Concurrent Requests**: For production, consider adding a job queue (Celery + Redis)

### Switching to GPU Support (If Needed Later)

If you need GPU support in the future:

1. Change `requirements.txt`:
   ```python
   # Remove CPU-only versions
   torch==2.5.1      # Instead of torch==2.5.1+cpu
   torchaudio==2.5.1 # Instead of torchaudio==2.5.1+cpu
   ```

2. Uncomment GPU section in `docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
   ```

**Note**: GPU deployment requires NVIDIA GPU with CUDA support and nvidia-docker.

## Troubleshooting

### Models Not Loading
- Verify HuggingFace token is correct
- Check you've accepted terms for pyannote models
- Ensure internet connection for initial model download

### Download Failures
- Check YouTube URL is valid and accessible
- Video may be region-restricted or age-restricted
- Try a different video to verify service is working

### Out of Memory
- Use a smaller Whisper model (`tiny` or `base`)
- Process shorter videos
- Increase Docker memory limits
- Add swap space

### Slow Processing
- First run downloads models (one-time, can take several minutes)
- CPU processing is slower than GPU
- Consider using smaller Whisper model
- Video length directly affects processing time

## Production Considerations

1. **Security**:
   - Use environment variables for secrets
   - Enable HTTPS with reverse proxy (nginx, Caddy)
   - Restrict CORS origins in production
   - Implement rate limiting

2. **Scaling**:
   - Add task queue (Celery, RQ) for long-running jobs
   - Use Redis for caching
   - Deploy multiple instances behind load balancer
   - Consider cloud GPU instances for faster processing

3. **Monitoring**:
   - Add application metrics (Prometheus)
   - Set up logging aggregation
   - Monitor disk space (temp files)
   - Track API response times

## License

This project is provided as-is for educational and commercial use.

## Acknowledgments

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Fast Whisper implementation
- [pyannote.audio](https://github.com/pyannote/pyannote-audio) - Speaker diarization
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloader
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs`
3. Check application logs
4. Open an issue on the repository

## Roadmap

- [ ] Add support for more video platforms
- [ ] Implement job queue for async processing
- [ ] Add user authentication
- [ ] Export transcripts to SRT/VTT formats
- [ ] Support for video file uploads
- [ ] Speaker identification (custom labels)
- [ ] Multi-language support in UI
- [ ] Real-time processing status updates via WebSocket
