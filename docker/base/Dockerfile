# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

# Install system build deps (only once)
RUN apt-get update && apt-get install -y gcc build-essential libffi-dev git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency descriptors to leverage cache
COPY pyproject.toml README.md /app/

# Create a temporary setup to extract and install just the dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel toml && \
    python -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); open('requirements.txt', 'w').writelines([dep + '\n' for dep in data['project']['dependencies']])" && \
    pip install -r requirements.txt

# Copy source code AFTER dependencies are installed (better caching)
COPY src/ /app/src/

# Install the package in editable mode (no dependencies since they're already installed)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e . --no-deps

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# The source code will be overlaid by child images
CMD ["python", "-c", "import privategpt, sys, os; print('Base image ready:', privategpt.__version__)"] 