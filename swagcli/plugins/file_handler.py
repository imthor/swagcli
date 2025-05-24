import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional
import aiofiles
from ..plugins import Plugin

plugin = Plugin(
    name="file_handler",
    description="Handles file uploads and downloads",
    version="1.0.0",
    author="SwagCli Team",
)


async def on_request(
    method: str, url: str, params: Dict[str, Any] = None, data: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """Hook called before making a request to handle file uploads."""
    if method not in ["POST", "PUT"] or not data:
        return None

    # Check for file upload fields
    files = {}
    for key, value in data.items():
        if isinstance(value, (str, Path)) and os.path.isfile(value):
            file_path = Path(value)
            mime_type, _ = mimetypes.guess_type(str(file_path))

            async with aiofiles.open(file_path, "rb") as f:
                content = await f.read()
                files[key] = (
                    file_path.name,
                    content,
                    mime_type or "application/octet-stream",
                )

    if files:
        return {"files": files}
    return None


async def on_response(response: Dict[str, Any]) -> None:
    """Hook called after receiving a response to handle file downloads."""
    if not isinstance(response.get("data"), dict):
        return

    data = response["data"]
    if "file_content" in data and "file_name" in data:
        download_dir = Path.home() / ".swagcli" / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        file_path = download_dir / data["file_name"]
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data["file_content"])

        # Remove file content from response to avoid memory issues
        data.pop("file_content", None)
        data["file_path"] = str(file_path)
