# syntax=docker/dockerfile:1.4
FROM privategpt/base:latest
WORKDIR /app
COPY ./v2 /app/v2

# Expose the Auth service
CMD ["uvicorn", "privategpt.services.auth.main:app", "--host", "0.0.0.0", "--port", "8000"]
