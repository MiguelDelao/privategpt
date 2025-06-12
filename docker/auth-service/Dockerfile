# Auth Service - Database-backed authentication
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user for security first
RUN useradd --create-home --shell /bin/bash appuser

# Create necessary directories with proper ownership
RUN mkdir -p /app/logs /app/data /app/data/migration_backup && \
    chown -R appuser:appuser /app

# Copy application code
COPY . .

# Make migration script executable and set ownership
RUN chmod +x migrate_data.py && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Start command - directly start the service (no migration needed)
CMD ["python", "auth_service.py"] 