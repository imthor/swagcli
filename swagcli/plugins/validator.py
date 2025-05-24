import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from jsonschema import ValidationError, validate
from pydantic import PrivateAttr

from .base import Plugin

plugin = Plugin(
    name="validator",
    description="Validates requests and responses using JSON Schema",
    version="1.0.0",
    author="SwagCli Team",
)


class CustomValidator:
    def __init__(
        self, field: str, validator_func: Callable[[Any], bool], error_message: str
    ):
        self.field = field
        self.validator_func = validator_func
        self.error_message = error_message

    def validate(self, data: Dict) -> None:
        value = data.get(self.field)
        if value is not None and not self.validator_func(value):
            raise ValueError(f"Field '{self.field}': {self.error_message}")


class SchemaValidator(Plugin):
    _schema_dir: Path = PrivateAttr()
    _schemas: Dict[str, Dict[str, Any]] = PrivateAttr(default_factory=dict)
    _custom_validators: Dict[str, Any] = PrivateAttr(default_factory=dict)

    def __init__(self) -> None:
        super().__init__(
            name="validator",
            description="Validates requests and responses using JSON Schema",
            version="1.0.0",
            author="SwagCli Team",
        )
        self._schema_dir = Path.home() / ".swagcli" / "schemas"
        self._schema_dir.mkdir(parents=True, exist_ok=True)
        self._schemas = {}
        self._custom_validators = {}

    def register_custom_validator(
        self, field: str, validator_func: Callable[[Any], bool], error_message: str
    ) -> None:
        """Register a custom validator function for a specific field."""
        self._custom_validators[field] = CustomValidator(
            field, validator_func, error_message
        )

    def register_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """Register a JSON schema for validation."""
        self._schemas[name] = schema

    def validate_schema(
        self, name: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Validate data against a registered schema."""
        if name not in self._schemas:
            return None

        schema = self._schemas[name]
        try:
            validate(instance=data, schema=schema)
            return None
        except Exception as e:
            return {"error": str(e)}

    def on_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Validate request data against registered schemas."""
        if not data:
            return None

        # Extract schema name from URL or use default
        schema_name = url.split("/")[-1]
        if schema_name not in self._schemas:
            return None

        return self.validate_schema(schema_name, data)

    def on_response(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate response data against registered schemas."""
        if not isinstance(response.get("data"), dict):
            return None

        # Extract schema name from URL or use default
        schema_name = response.get("url", "").split("/")[-1]
        if schema_name not in self._schemas:
            return None

        return self.validate_schema(schema_name, response["data"])


# Create a global validator instance
validator = SchemaValidator()


def on_request(
    method: str, url: str, params: Dict[str, Any] = None, data: Dict[str, Any] = None
) -> None:
    """Hook called before making a request to validate the request data."""
    # Extract endpoint from URL
    endpoint = url.split("?")[0].rstrip("/")

    try:
        validator.validate_request(endpoint, method, data)
    except ValueError as e:
        raise ValueError(f"Request validation failed: {str(e)}")


def on_response(response: Dict[str, Any]) -> None:
    """Hook called after receiving a response to validate the response data."""
    if not isinstance(response.get("data"), (dict, list)):
        return

    endpoint = response.get("url", "").split("?")[0].rstrip("/")
    method = response.get("method", "GET")

    try:
        validator.validate_response(endpoint, method, response["data"])
    except ValueError as e:
        raise ValueError(f"Response validation failed: {str(e)}")
