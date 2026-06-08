# OLPA - Predictive Maintenance ML Environment
# Multi-stage Docker build for development and production

# Base stage with Python and uv
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Development stage
FROM base AS development

# Sync all dependencies (creates .venv)
RUN uv sync

# Copy project files
COPY . .

# Add .venv to PATH so all commands use the venv Python
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Expose ports for Jupyter and MLflow
EXPOSE 8888 5000

# Default command for development (token disabled for local dev convenience)
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ServerApp.token=''"]

# Production stage for ML training
FROM base AS training

# Sync only production dependencies
RUN uv sync --no-dev

# Copy only necessary files
COPY src/ src/
COPY config/ config/
COPY data/ data/

# Add .venv to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Default command for training
CMD ["python", "src/ml_models/train.py"]

# Production stage for API serving
FROM base AS api

# Sync only production dependencies
RUN uv sync --no-dev

# Copy API code
COPY src/api/ src/api/
COPY config/ config/

# Add .venv to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Expose API port
EXPOSE 8000

# Default command for API
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
