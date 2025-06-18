# syntax=docker/dockerfile:1.4
FROM python:3.11-slim

# Install system build deps (only once)
RUN apt-get update && apt-get install -y gcc build-essential libffi-dev git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency descriptors to leverage cache
COPY pyproject.toml README.md /app/

# Copy full source tree (current context) into /app/v2
COPY . /app/v2

# Install v2 project with BuildKit wheel cache
RUN --mount=type=cache,target=/root/.cache/pip pip install -e /app/v2

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# The source code will be overlaid by child images
CMD ["python", "-c", "import privategpt, sys, os; print('Base image ready:', privategpt.__version__)"] 