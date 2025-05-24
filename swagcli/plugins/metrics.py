import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from ..plugins import Plugin

plugin = Plugin(
    name="metrics",
    description="Collects API metrics and statistics",
    version="1.0.0",
    author="SwagCli Team",
)


class MetricsCollector:
    def __init__(self):
        self.metrics_dir = Path.home() / ".swagcli" / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.current_metrics: Dict[str, List[Dict[str, Any]]] = {}

    def add_metric(
        self, endpoint: str, method: str, status_code: int, elapsed: float
    ) -> None:
        if endpoint not in self.current_metrics:
            self.current_metrics[endpoint] = []

        self.current_metrics[endpoint].append(
            {
                "timestamp": datetime.now().isoformat(),
                "method": method,
                "status_code": status_code,
                "elapsed": elapsed,
            }
        )

    def save_metrics(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = self.metrics_dir / f"metrics_{timestamp}.json"

        with open(metrics_file, "w") as f:
            json.dump(self.current_metrics, f, indent=2)


# Create a global metrics collector instance
metrics_collector = MetricsCollector()


def on_response(response: Dict) -> None:
    """Hook function to collect metrics after receiving a response."""
    global metrics_collector
    if not isinstance(response.get("data"), (dict, list)):
        return

    metrics_collector.add_metric(
        response["url"],
        response["method"],
        response["status_code"],
        response["elapsed"],
    )
    metrics_collector.save_metrics()
