FROM privategpt/base:latest

# Install additional dependencies for MCP service
RUN pip install --no-cache-dir \
    "mcp[cli]" \
    psutil \
    httpx-sse

# Copy source code
COPY src/ /app/src/

# Set working directory
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the MCP server
CMD ["python", "-m", "privategpt.services.mcp.main"]