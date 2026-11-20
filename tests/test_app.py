"""Unit tests for the SRE metrics demo Flask app."""

import json
import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import app as app_module  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    # Remove the synthetic latency so tests run fast.
    monkeypatch.setattr(app_module.time, "sleep", lambda _s: None)
    return app_module.app.test_client()


def test_index_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"running" in response.data


def test_store_success(client, monkeypatch):
    monkeypatch.setattr(app_module.random, "random", lambda: 0.99)
    response = client.get("/store")
    assert response.status_code == 200
    assert "stores" in response.get_json()


def test_store_simulated_failure(client, monkeypatch):
    monkeypatch.setattr(app_module.random, "random", lambda: 0.0)
    response = client.get("/store")
    assert response.status_code == 500


def test_error_endpoint_always_fails(client):
    response = client.get("/error")
    assert response.status_code == 500


def test_store_creates_trace_spans(client, monkeypatch):
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    app_module.tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(app_module.random, "random", lambda: 0.0)
    client.get("/store")
    names = [span.name for span in exporter.get_finished_spans()]
    assert "store.load_catalog" in names
    assert "store.process_order" in names
    assert any(name.startswith("GET /store") for name in names)


def test_logs_are_json_with_trace_id(client, monkeypatch):
    lines = []

    class ListHandler(logging.Handler):
        def emit(self, record):
            lines.append(self.format(record))

    handler = ListHandler()
    handler.setFormatter(app_module.JsonFormatter())
    app_module.logger.addHandler(handler)
    try:
        monkeypatch.setattr(app_module.random, "random", lambda: 0.99)
        client.get("/store")
    finally:
        app_module.logger.removeHandler(handler)
    entry = json.loads(lines[-1])
    assert entry["service"] == "sre-metrics-app"
    assert len(entry["trace_id"]) == 32


def test_ask_records_genai_usage(client):
    response = client.get("/ask")
    assert response.status_code == 200
    assert response.get_json()["usage"]["output_tokens"] > 0
    body = client.get("/metrics").get_data(as_text=True)
    assert 'genai_tokens_total{type="input"}' in body


def test_inject_drill_is_off_by_default(client, monkeypatch):
    monkeypatch.delenv("ENABLE_INJECTION_DRILL", raising=False)
    assert client.get("/inject").status_code == 404
    monkeypatch.setenv("ENABLE_INJECTION_DRILL", "true")
    assert client.get("/inject").status_code == 200


def test_metrics_exposes_counters_and_histogram(client, monkeypatch):
    monkeypatch.setattr(app_module.random, "random", lambda: 0.99)
    client.get("/store")
    client.get("/error")
    body = client.get("/metrics").get_data(as_text=True)
    assert 'http_requests_total{endpoint="/store",method="GET",status="200"}' in body
    assert 'http_requests_total{endpoint="/error",method="GET",status="500"}' in body
    assert "http_request_duration_seconds_bucket" in body


def test_every_series_exists_at_zero_before_the_first_event(client):
    """Prometheus can only compute rate() for a series that exists, so the app creates them all at start."""
    text = client.get("/metrics").data.decode()
    for endpoint, status in app_module._INITIAL_SERIES:
        line = 'http_requests_total{{endpoint="{}",method="GET",status="{}"}}'.format(endpoint, status)
        assert line in text, line
