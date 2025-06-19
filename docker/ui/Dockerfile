# syntax=docker/dockerfile:1.4
FROM privategpt/base:latest
WORKDIR /app
COPY . /app

COPY ./src/privategpt/services/ui/requirements.txt /tmp/req.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r /tmp/req.txt

ENV STREAMLIT_SERVER_PORT=8501

CMD ["streamlit", "run", "/app/src/privategpt/services/ui/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
