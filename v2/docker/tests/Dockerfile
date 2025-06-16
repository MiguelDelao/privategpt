# syntax=docker/dockerfile:1.4
FROM privategpt/base:latest
WORKDIR /app

# install only test deps (project already in image)
RUN --mount=type=cache,target=/root/.cache/pip pip install pytest httpx

COPY ./v2/tests /app/v2/tests

CMD ["pytest", "-q", "v2/tests"] 