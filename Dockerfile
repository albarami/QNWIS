# Multi-stage hardened Dockerfile for QNWIS production deployment
FROM python:3.11-slim AS builder

# Security & Performance: Set secure and optimized environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files and build wheels
COPY pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --wheel-dir /wheels .

# Runtime stage
FROM python:3.11-slim AS runtime

# Security & Performance: Set secure and optimized environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Security: Create non-root user
RUN adduser --disabled-password --gecos "" --uid 1000 qnwis && \
    mkdir -p /app && \
    chown -R qnwis:qnwis /app

WORKDIR /app

# Install Python packages from wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* && \
    rm -rf /wheels

# Copy application code
COPY --chown=qnwis:qnwis src ./src
COPY --chown=qnwis:qnwis scripts ./scripts
COPY --chown=qnwis:qnwis data ./data
COPY --chown=qnwis:qnwis configs ./configs

# Security: Switch to non-root user
USER qnwis

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=5 \
    CMD curl -sf http://127.0.0.1:8000/health/ready || exit 1

# Run application with gunicorn
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-c", "configs/gunicorn.conf.py", "src.qnwis.api.server:create_app()"]
