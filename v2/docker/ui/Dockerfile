# syntax=docker/dockerfile:1.4
FROM privategpt/base:latest
WORKDIR /app
COPY ./v2 /app/v2

RUN --mount=type=cache,target=/root/.cache/pip pip install streamlit requests

ENV STREAMLIT_SERVER_PORT=8501

CMD ["streamlit", "run", "/app/v2/src/privategpt/services/ui/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
