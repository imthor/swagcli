from typing import Dict, Optional
from pathlib import Path
import json
from pydantic import BaseModel, Field, SecretStr
from rich.console import Console

console = Console()


class AuthConfig(BaseModel):
    type: str = Field(..., description="Authentication type (oauth2, api_key, basic)")
    token: Optional[SecretStr] = None
    client_id: Optional[str] = None
    client_secret: Optional[SecretStr] = None
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    api_key: Optional[SecretStr] = None
    api_key_header: Optional[str] = None


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl: int = 300  # 5 minutes
    max_size: int = 1000
    storage_path: Path = Path.home() / ".swagcli" / "cache"


class Config(BaseModel):
    base_url: str
    auth: Optional[AuthConfig] = None
    cache: CacheConfig = CacheConfig()
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    output_format: str = "table"  # table, json, yaml
    debug: bool = False

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        if config_path is None:
            config_path = Path.home() / ".swagcli" / "config.json"

        if not config_path.exists():
            return cls(base_url="")

        try:
            with open(config_path) as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            return cls(base_url="")

    def save(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            config_path = Path.home() / ".swagcli" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        def default(obj):
            from pydantic import SecretStr
            from pathlib import Path

            if isinstance(obj, SecretStr):
                return obj.get_secret_value()
            if isinstance(obj, Path):
                return str(obj)
            raise TypeError(
                f"Object of type {obj.__class__.__name__} is not JSON serializable"
            )

        with open(config_path, "w") as f:
            json.dump(self.model_dump(), f, indent=2, default=default)
