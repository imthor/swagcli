import os
import pytest
from pathlib import Path
from swagcli.plugins.file_handler import plugin, on_request, on_response


@pytest.fixture
def test_file(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    return file_path


@pytest.mark.asyncio
async def test_file_upload_hook(test_file):
    data = {"file": str(test_file), "other_field": "value"}

    result = await on_request("POST", "https://api.example.com/upload", data=data)
    assert result is not None
    assert "files" in result
    assert "file" in result["files"]

    filename, content, mime_type = result["files"]["file"]
    assert filename == "test.txt"
    assert content == b"test content"
    assert mime_type == "text/plain"


@pytest.mark.asyncio
async def test_file_download_hook(tmp_path):
    response = {
        "data": {"file_name": "downloaded.txt", "file_content": b"test content"}
    }

    await on_response(response)

    download_dir = Path.home() / ".swagcli" / "downloads"
    downloaded_file = download_dir / "downloaded.txt"

    assert downloaded_file.exists()
    assert downloaded_file.read_bytes() == b"test content"

    # Cleanup
    downloaded_file.unlink()
    download_dir.rmdir()


def test_plugin_metadata():
    assert plugin.name == "file_handler"
    assert plugin.description == "Handles file uploads and downloads"
    assert plugin.version == "1.0.0"
    assert plugin.author == "SwagCli Team"
