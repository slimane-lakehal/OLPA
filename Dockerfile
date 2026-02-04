# OLPA - Predictive Maintenance ML Environment
# Multi-stage Docker build for development and production

# Base stage with Python and dependencies
FROM python:3.12-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files for `uv` package manager
COPY pyproject.toml uv.lock .

# Install the `uv` package manager, then use it to sync pinned deps
# Note: `pyproject.toml` / `uv.lock` require Python >= 3.12.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir uv && \
    uv sync --no-dev

# Development stage
FROM base as development

# Install additional dev dependencies
RUN pip install --no-cache-dir \
    ipython \
    jupyterlab \
    black \
    flake8 \
    pytest

# Copy project files
COPY . .

# Expose ports for Jupyter and MLflow
EXPOSE 8888 5000

# Default command for development
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]

# Production stage for ML training
FROM base as training

# Copy only necessary files
COPY src/ src/
COPY config/ config/
COPY data/ data/

# Set Python path
ENV PYTHONPATH=/app

# Default command for training
CMD ["python", "src/ml_models/train.py"]

# Production stage for API serving
FROM base as api

# Copy API code
COPY src/api/ src/api/
COPY config/ config/

# Install additional API dependencies
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn==0.25.0

# Expose API port
EXPOSE 8000

# Default command for API
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
