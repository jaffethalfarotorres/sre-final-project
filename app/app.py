import random
import time

from flask import Flask, jsonify, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REQUESTS = Counter(
    "http_requests_total",
    "Number of HTTP requests handled by the demo application.",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Time spent handling HTTP requests.",
    ["method", "endpoint"],
)


@app.get("/")
def index():
    REQUESTS.labels("GET", "/", "200").inc()
    return "SRE metrics demo is running. Visit /store or /metrics.\n"


@app.get("/store")
def store():
    started_at = time.perf_counter()
    # A small, variable response time makes the Grafana latency panel useful.
    time.sleep(random.uniform(0.05, 0.35))
    REQUEST_DURATION.labels("GET", "/store").observe(time.perf_counter() - started_at)
    REQUESTS.labels("GET", "/store", "200").inc()
    return jsonify({"stores": [{"name": "SRE Demo Store", "items": 1}]})


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
