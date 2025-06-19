FROM privategpt/base:latest

WORKDIR /app

# Copy source code
COPY src/ src/

# Install in development mode
RUN pip install -e .

# Install Ollama client
RUN pip install ollama>=0.3.0

# Expose port
EXPOSE 8000

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run LLM service
CMD ["python", "-m", "uvicorn", "privategpt.services.llm.api.main:app", "--host", "0.0.0.0", "--port", "8000"]