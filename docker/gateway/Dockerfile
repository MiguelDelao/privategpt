FROM privategpt/base:latest

# Set working directory
WORKDIR /app

# Copy source code
COPY src/ src/

# Install the package in development mode
RUN pip install -e .

# Add required dependencies for gateway
RUN pip install python-jose[cryptography] httpx psycopg2-binary pyjwt asyncpg celery redis

# Install curl for health check
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the gateway service
CMD ["python", "-m", "privategpt.services.gateway.main"]