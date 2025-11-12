# Multi-stage secure Dockerfile for QNWIS
FROM python:3.11-slim AS base

# Security & Performance: Set secure and optimized environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONOPTIMIZE=2 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Security: Create non-root user
RUN adduser --disabled-password --gecos "" --uid 1000 app && \
    mkdir -p /app && \
    chown -R app:app /app

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY --chown=app:app pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Copy application code
COPY --chown=app:app src ./src
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app data ./data
COPY --chown=app:app .chainlit ./.chainlit

# Security: Switch to non-root user
USER app

# Security: Set umask for restrictive file permissions
RUN umask 0027

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "src.qnwis.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
