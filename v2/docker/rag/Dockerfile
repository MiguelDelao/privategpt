# syntax=docker/dockerfile:1.4
FROM privategpt/base:latest
WORKDIR /app
COPY ./v2 /app/v2
WORKDIR /app
CMD ["uvicorn", "privategpt.services.rag.main:app", "--host", "0.0.0.0", "--port", "8000"] 