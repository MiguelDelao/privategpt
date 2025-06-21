FROM privategpt/base:latest

# Set working directory
WORKDIR /app

# Copy source code and configuration
COPY src/ src/
COPY config.json .

# Install the package in development mode
RUN pip install -e .

# Add required dependencies for gateway
RUN pip install python-jose[cryptography] httpx asyncpg

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the gateway service
CMD ["python", "-m", "privategpt.services.gateway.main"]