# Base image pinned to the multi-arch index digest for reproducible builds (amd64 + arm64).
# Dependabot (docker ecosystem, weekly) refreshes the tag and digest together.
# This is python:3.12-slim. (A comment cannot follow FROM on the same line: Docker would read it as arguments.)
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

WORKDIR /app

# Install dependencies first for optimized layer caching
COPY app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./

# Run as non-root user for security best practices
RUN useradd -u 1000 -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Production WSGI server with Gunicorn.
# One worker process keeps prometheus_client counters in a single process, so every scrape sees
# consistent values. Threads provide concurrency for the sleeping /store handler.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "30", "--access-logfile", "-", "app:app"]
