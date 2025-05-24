import json
import pytest
from pathlib import Path
from swagcli.plugins.metrics import plugin, MetricsCollector, on_response
from unittest.mock import patch


@pytest.fixture
def metrics_collector(tmp_path):
    collector = MetricsCollector()
    collector.metrics_dir = tmp_path / "metrics"
    collector.metrics_dir.mkdir(parents=True, exist_ok=True)
    return collector


def test_metrics_collector_creation(metrics_collector):
    assert metrics_collector.metrics_dir.exists()
    assert isinstance(metrics_collector.current_metrics, dict)
    assert len(metrics_collector.current_metrics) == 0


def test_add_metric(metrics_collector):
    metrics_collector.add_metric("/test", "GET", 200, 0.5)

    assert "/test" in metrics_collector.current_metrics
    assert len(metrics_collector.current_metrics["/test"]) == 1

    metric = metrics_collector.current_metrics["/test"][0]
    assert metric["method"] == "GET"
    assert metric["status_code"] == 200
    assert metric["elapsed"] == 0.5
    assert "timestamp" in metric


def test_save_metrics(metrics_collector):
    metrics_collector.add_metric("/test", "GET", 200, 0.5)
    metrics_collector.save_metrics()

    # Check that metrics file was created
    metrics_files = list(metrics_collector.metrics_dir.glob("metrics_*.json"))
    assert len(metrics_files) == 1

    # Check file contents
    with open(metrics_files[0]) as f:
        saved_metrics = json.load(f)

    assert "/test" in saved_metrics
    assert len(saved_metrics["/test"]) == 1
    assert saved_metrics["/test"][0]["method"] == "GET"
    assert saved_metrics["/test"][0]["status_code"] == 200
    assert saved_metrics["/test"][0]["elapsed"] == 0.5


def test_on_response_hook(metrics_collector):
    response = {
        "url": "/test",
        "method": "GET",
        "status_code": 200,
        "elapsed": 0.5,
        "data": {"key": "value"},
    }

    # Clear existing metrics
    metrics_collector.current_metrics.clear()

    # Patch the global metrics_collector in the metrics module
    with patch("swagcli.plugins.metrics.metrics_collector", metrics_collector):
        on_response(response)

    # Verify metrics were collected
    assert "/test" in metrics_collector.current_metrics
    assert len(metrics_collector.current_metrics["/test"]) == 1
    metric = metrics_collector.current_metrics["/test"][0]
    assert metric["method"] == "GET"
    assert metric["status_code"] == 200
    assert metric["elapsed"] == 0.5


def test_plugin_metadata():
    assert plugin.name == "metrics"
    assert plugin.description == "Collects API metrics and statistics"
    assert plugin.version == "1.0.0"
    assert plugin.author == "SwagCli Team"
