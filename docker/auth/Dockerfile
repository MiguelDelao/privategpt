# syntax=docker/dockerfile:1.4
FROM privategpt/base:latest
WORKDIR /app
COPY . /app

# Install postgres driver for auth service
RUN --mount=type=cache,target=/root/.cache/pip pip install psycopg2-binary

# Expose the Auth service
CMD ["uvicorn", "privategpt.services.auth.main:app", "--host", "0.0.0.0", "--port", "8000"]
