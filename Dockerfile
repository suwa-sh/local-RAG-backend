# checkov:skip=CKV_DOCKER_2:Using official Unstructured.io image - user management handled by base image
# checkov:skip=CKV_DOCKER_3:One-off container for document processing - healthcheck not required
# Use official Unstructured.io Docker image as base (latest stable version)
FROM quay.io/unstructured-io/unstructured:0.17.9

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY requirements.lock .

# Install dependencies with CPU-only PyTorch
RUN pip install --upgrade pip setuptools wheel && \
    pip install torch==2.2.2+cpu torchvision==0.17.2+cpu -f https://download.pytorch.org/whl/torch_stable.html && \
    pip install "numpy<2.0.0" --force-reinstall && \
    sed '/-e/d' requirements.lock > requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ /app/src/

# Set environment variables
ENV PYTHONPATH="/app"

# Create data directories under /app (writable by default user)
RUN mkdir -p /app/data/input /app/data/logs

# Set up logging with timestamp
ENV LOG_DIR="/app/data/logs"

# Default command with logging
CMD ["sh", "-c", "python -m src.main.ingest /app/data/input 2>&1 | tee /app/data/logs/ingest-$(date +%Y-%m-%d_%H%M%S).log"]