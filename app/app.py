"""
SRE Metrics Demo Application
============================
A lightweight Python Flask web service instrumented with Prometheus client metrics.
Designed for Kubernetes observability demonstrations, emitting request counts,
response latencies, error signals, and health status.

Endpoints:
  - GET /        : Service root & health check (HTTP 200)
  - GET /store   : Business API with realistic latency and ~5% simulated error rate
  - GET /error   : Explicit error trigger for testing alerts and SLO degradation (HTTP 500)
  - GET /metrics : Prometheus scrape endpoint exporting telemetry counters and histograms
"""

import random
import time

from flask import Flask, jsonify, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Prometheus Telemetry Instrumentation
# Counter tracks total HTTP requests partitioned by HTTP method, URI endpoint, and response status code.
REQUESTS = Counter(
    "http_requests_total",
    "Total number of HTTP requests handled by the application.",
    ["method", "endpoint", "status"],
)

# Histogram tracks request latency distribution in seconds across endpoints.
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency distribution in seconds.",
    ["method", "endpoint"],
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.5],
)


@app.get("/")
def index():
    """Health check and landing endpoint for Kubernetes liveness/readiness probes."""
    REQUESTS.labels(method="GET", endpoint="/", status="200").inc()
    return "SRE metrics demo is running. Endpoints: /store, /error, /metrics\n", 200


@app.get("/store")
def store():
    """
    Simulated business transaction endpoint.
    Introduces variable response latency (50ms - 350ms) and an intentional ~5% error rate
    to provide realistic signals for SRE latency and error-budget monitoring.
    """
    started_at = time.perf_counter()

    # Introduce synthetic latency to model backend processing
    time.sleep(random.uniform(0.05, 0.35))
    elapsed = time.perf_counter() - started_at

    # Inject a 5% low-probability failure to produce real 5xx signals for alert evaluation
    if random.random() < 0.05:
        REQUEST_DURATION.labels(method="GET", endpoint="/store").observe(elapsed)
        REQUESTS.labels(method="GET", endpoint="/store", status="500").inc()
        return jsonify({"error": "Internal Server Error in store processing"}), 500

    REQUEST_DURATION.labels(method="GET", endpoint="/store").observe(elapsed)
    REQUESTS.labels(method="GET", endpoint="/store", status="200").inc()
    return jsonify({"stores": [{"name": "SRE Demo Store", "items": 1}]}), 200


@app.get("/error")
def trigger_error():
    """
    Dedicated failure endpoint for on-demand alert verification.
    Always returns HTTP 500 to immediately trigger HighErrorRate alerts.
    """
    started_at = time.perf_counter()
    time.sleep(0.02)
    elapsed = time.perf_counter() - started_at

    REQUEST_DURATION.labels(method="GET", endpoint="/error").observe(elapsed)
    REQUESTS.labels(method="GET", endpoint="/error", status="500").inc()
    return jsonify({"error": "Simulated critical failure for alert testing"}), 500


@app.get("/metrics")
def metrics():
    """Prometheus exposition format endpoint consumed by cluster scrapers."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    # Local development entrypoint; production deployment uses Gunicorn WSGI
    app.run(host="0.0.0.0", port=5000)
