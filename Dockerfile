# Multi-stage Dockerfile for YouTube Transcription Service
# Supports both CPU and GPU deployment via COMPUTE_TYPE build argument
#
# Build commands:
#   CPU: docker build --build-arg COMPUTE_TYPE=cpu -t youtube-transcription:cpu .
#   GPU: docker build --build-arg COMPUTE_TYPE=gpu -t youtube-transcription:gpu .

ARG COMPUTE_TYPE=cpu

# =============================================================================
# Base images for each compute type
# =============================================================================
FROM python:3.10-slim AS base-cpu
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 AS base-gpu

# =============================================================================
# Select base image based on COMPUTE_TYPE
# =============================================================================
FROM base-${COMPUTE_TYPE} AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# Note: python3.10 is needed for CUDA base image which doesn't include Python
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

# Set working directory
WORKDIR /app

# =============================================================================
# Install Python dependencies based on compute type
# =============================================================================
ARG COMPUTE_TYPE=cpu
COPY requirements-base.txt requirements-cpu.txt requirements-gpu.txt ./

RUN pip install --upgrade pip && \
    if [ "$COMPUTE_TYPE" = "gpu" ]; then \
        echo "Installing GPU dependencies..." && \
        pip install -r requirements-gpu.txt; \
    else \
        echo "Installing CPU dependencies..." && \
        pip install -r requirements-cpu.txt; \
    fi

# =============================================================================
# Copy application code
# =============================================================================
COPY app/ ./app/
COPY static/ ./static/

# Create necessary directories
RUN mkdir -p temp models

# Store compute type for runtime logging
ENV DOCKER_COMPUTE_TYPE=${COMPUTE_TYPE}

# Expose port
EXPOSE 8000

# Health check with longer start period for model loading
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
