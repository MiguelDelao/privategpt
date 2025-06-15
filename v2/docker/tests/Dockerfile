FROM python:3.11-slim
WORKDIR /app

# Copy project source first for editable install
COPY ./v2 /app/v2

# Install project (prod extras) and testing deps
RUN pip install --no-cache-dir -e /app/v2 pytest httpx

# Copy remaining repository (tests etc.)
COPY . /app

CMD ["pytest", "-q", "v2/tests"] 