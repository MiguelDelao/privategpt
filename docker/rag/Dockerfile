# syntax=docker/dockerfile:1.4
FROM privategpt/base:latest
WORKDIR /app

# Install additional dependencies for RAG service
RUN pip install --no-cache-dir asyncpg psycopg2-binary

COPY . /app
CMD ["uvicorn", "privategpt.services.rag.main:app", "--host", "0.0.0.0", "--port", "8000"] 