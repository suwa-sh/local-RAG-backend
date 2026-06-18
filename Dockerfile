# checkov:skip=CKV_DOCKER_2:Using official Unstructured.io image - user management handled by base image
# checkov:skip=CKV_DOCKER_3:One-off container for document processing - healthcheck not required
# Use official Unstructured.io Docker image as base (latest stable version)
FROM quay.io/unstructured-io/unstructured:0.23.1

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .
COPY requirements.lock .

# base image (unstructured 0.23.x) は uv ベース構成で、
# pip は同梱されず venv は /app/.venv に存在する
ENV VIRTUAL_ENV=/app/.venv

# Install dependencies with CPU-only PyTorch for multi-arch
# numpy 2.x は unstructured 0.23 / graphiti-core 0.29 とも互換のため固定しない
#
# requirements.lock は plain な torch==2.10.0 を指す（rye が macOS arm64 で
# 解決したため nvidia 依存は無い）。しかし uv は PyPI の torch==2.10.0 を
# +cu128 wheel として解決し、4GB 超の CUDA 依存（nvidia-*）を引き込む。
# これを避けるため 2 パスで導入する:
#   1) +cpu を明示して torch/torchvision を導入。+cpu wheel は PyTorch CPU
#      index にしか存在しないため確実に CPU 版が入り、CUDA 依存は入らない。
#   2) 残りの依存を PyPI から導入。constraint で torch を +cpu に固定するため、
#      導入済みの CPU 版で充足され、再解決による +cu128 への置換が起きない。
RUN sed '/-e/d' requirements.lock > requirements.txt && \
    printf 'torch==2.10.0+cpu\ntorchvision==0.25.0+cpu\n' > torch-cpu.constraints && \
    uv pip install --python "$VIRTUAL_ENV/bin/python" --no-cache \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.10.0+cpu torchvision==0.25.0+cpu && \
    uv pip install --python "$VIRTUAL_ENV/bin/python" --no-cache \
        -c torch-cpu.constraints \
        -r requirements.txt

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