from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from ..plugins import Plugin

plugin = Plugin(
    name="request_logger",
    description="Logs all API requests to a file",
    version="1.0.0",
    author="SwagCli Team",
)


def on_request(
    method: str, url: str, params: Dict[str, Any] = None, data: Dict[str, Any] = None
) -> None:
    """Hook called before making a request."""
    log_dir = Path.home() / ".swagcli" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "requests.log"
    timestamp = datetime.now().isoformat()

    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {method} {url}\n")
        if params:
            f.write(f"Params: {params}\n")
        if data:
            f.write(f"Data: {data}\n")
        f.write("-" * 80 + "\n")


def on_response(response: Dict[str, Any]) -> None:
    """Hook called after receiving a response."""
    log_dir = Path.home() / ".swagcli" / "logs"
    log_file = log_dir / "responses.log"
    timestamp = datetime.now().isoformat()

    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] Status: {response.get('status_code')}\n")
        f.write(f"Data: {response.get('data')}\n")
        f.write("-" * 80 + "\n")
