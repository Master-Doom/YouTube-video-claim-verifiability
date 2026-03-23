# Multi-stage Dockerfile for YouTube Transcription Service
# Supports both CPU and GPU deployment via COMPUTE_TYPE build argument
#
# Build commands:
#   CPU: docker build --build-arg COMPUTE_TYPE=cpu -t youtube-transcription:cpu .
#   GPU: docker build --build-arg COMPUTE_TYPE=gpu -t youtube-transcription:gpu .

# Global ARG - must be declared before any FROM to use in FROM instructions
ARG COMPUTE_TYPE=cpu

# =============================================================================
# CPU Stage - Uses python:3.10-slim (Python already included)
# =============================================================================
FROM python:3.10-slim AS build-cpu

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (NO python3.10 - already included in base image)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    wget \
    pkg-config \
    build-essential \
    python3-dev \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-base.txt requirements-cpu.txt requirements-gpu.txt ./
RUN pip install --upgrade pip && pip install -r requirements-cpu.txt

COPY app/ ./app/
COPY static/ ./static/
RUN mkdir -p temp models

# =============================================================================
# GPU Stage - Uses NVIDIA CUDA base (needs Python installed)
# =============================================================================
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 AS build-gpu

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    ffmpeg \
    git \
    wget \
    pkg-config \
    build-essential \
    python3-dev \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app
COPY requirements-base.txt requirements-cpu.txt requirements-gpu.txt ./
RUN pip install --upgrade pip && pip install -r requirements-gpu.txt

COPY app/ ./app/
COPY static/ ./static/
RUN mkdir -p temp models

# =============================================================================
# Final Stage - Select based on COMPUTE_TYPE build arg
# =============================================================================
# Re-declare ARG after FROM to make it available in this stage
ARG COMPUTE_TYPE
FROM build-${COMPUTE_TYPE} AS final

# Re-declare ARG again to use it in ENV (ARGs don't persist across FROM)
ARG COMPUTE_TYPE
ENV DOCKER_COMPUTE_TYPE=${COMPUTE_TYPE}

# IMPORTANT: Add non-root user for Hugging Face Spaces
RUN useradd -m -u 1000 user
RUN chown -R user:user /app
USER user

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]