FROM python:3.11-slim

WORKDIR /app

# Install uv for package management
RUN apt-get update && apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

ENV MCP_SERVER_HOST="0.0.0.0" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Install dependencies (lock 固定・dev除外・プロジェクト自体はビルドしない)
# upstream(mcp-v1.0.2)はマルチモジュール構成だが main.py で src/ を
# sys.path に追加して直接起動するため、パッケージとしてのビルドは不要。
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-group dev

# Copy application code (新レイアウト)
COPY main.py ./
COPY src/ ./src/
COPY config/ ./config/

EXPOSE 8000

# Command to run the application
# main.py が --config 既定で config/config.yaml を読み込む（SSE transport）
CMD ["uv", "run", "--no-sync", "main.py"]
