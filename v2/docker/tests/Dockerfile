FROM python:3.11-slim
WORKDIR /app
# Copy project metadata and install prod + test deps
COPY ./v2/pyproject.toml /app/
RUN pip install --no-cache-dir -e ./v2[prod] pytest httpx
# Copy source and tests last (so that reinstall happens only on code change)
COPY . /app
CMD ["pytest", "-q", "v2/tests"] 