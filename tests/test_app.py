"""Unit tests for the SRE metrics demo Flask app."""

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


def test_metrics_exposes_counters_and_histogram(client, monkeypatch):
    monkeypatch.setattr(app_module.random, "random", lambda: 0.99)
    client.get("/store")
    client.get("/error")
    body = client.get("/metrics").get_data(as_text=True)
    assert 'http_requests_total{endpoint="/store",method="GET",status="200"}' in body
    assert 'http_requests_total{endpoint="/error",method="GET",status="500"}' in body
    assert "http_request_duration_seconds_bucket" in body
