# Multi-stage build for efficient image size and caching
FROM python:3.11-slim AS base

# Install system dependencies required by unstructured.io
RUN apt-get update && apt-get install -y \
    # Build dependencies
    g++ \
    gcc \
    # PDF processing
    poppler-utils \
    # OCR support
    tesseract-ocr \
    tesseract-ocr-jpn \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Stage 1: Dependencies
FROM base AS dependencies

# Install pip and setuptools first
RUN pip install --upgrade pip setuptools wheel

# Copy dependency files
COPY pyproject.toml .
COPY requirements.lock .

# Install dependencies directly from requirements.lock
RUN sed '/-e/d' requirements.lock > requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM base AS production

# Copy dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy source code
COPY src/ /app/src/

# Set environment variables
ENV PYTHONPATH="/app"

# Create data directories
RUN mkdir -p /data/input /data/logs

# Set up logging with timestamp
ENV LOG_DIR="/data/logs"

# Default command with logging
CMD ["sh", "-c", "python -m src.main.ingest /data/input 2>&1 | tee /data/logs/ingest-$(date +%Y-%m-%d_%H%M%S).log"]