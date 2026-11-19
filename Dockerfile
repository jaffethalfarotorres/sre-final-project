FROM python:3.12-slim

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
