# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils tesseract-ocr libmagic-dev libgl1 libglib2.0-0 build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and install project
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Stage 2: Final Stage
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils tesseract-ocr libmagic-dev libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src ./src/

ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
