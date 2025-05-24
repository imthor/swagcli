import json
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable
from jsonschema import validate, ValidationError
from ..plugins import Plugin

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


class SchemaValidator:
    def __init__(self, schema_dir: Optional[Path] = None):
        self.schema_dir = schema_dir or Path.home() / ".swagcli" / "schemas"
        self.schema_dir.mkdir(parents=True, exist_ok=True)
        self.schemas: Dict[str, Dict] = {}
        self.custom_validators: Dict[str, CustomValidator] = {}

    def register_custom_validator(
        self, field: str, validator_func: Callable[[Any], bool], error_message: str
    ) -> None:
        """Register a custom validator function for a specific field."""
        self.custom_validators[field] = CustomValidator(
            field, validator_func, error_message
        )

    def load_schema(self, endpoint: str) -> Optional[Dict]:
        """Load a schema for an endpoint."""
        if endpoint in self.schemas:
            return self.schemas[endpoint]

        schema_file = self.schema_dir / f"{endpoint}.json"
        if not schema_file.exists():
            return None

        with open(schema_file) as f:
            schema = json.load(f)
            self.schemas[endpoint] = schema
            return schema

    def generate_schema_from_openapi(self, openapi_spec: Dict) -> Dict[str, Dict]:
        """Generate JSON Schema from OpenAPI specification."""
        schemas = {}

        for path, path_item in openapi_spec.get("paths", {}).items():
            endpoint = path.lstrip("/").replace("/", "_")
            schema = {"request": {}, "response": {}}

            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                    continue

                # Request schema
                if "requestBody" in operation:
                    content = operation["requestBody"].get("content", {})
                    if "application/json" in content:
                        schema["request"][method.lower()] = content[
                            "application/json"
                        ].get("schema", {})

                # Response schema
                if "responses" in operation:
                    success_response = operation["responses"].get("200", {})
                    content = success_response.get("content", {})
                    if "application/json" in content:
                        schema["response"][method.lower()] = content[
                            "application/json"
                        ].get("schema", {})

            if schema["request"] or schema["response"]:
                schemas[endpoint] = schema

        return schemas

    def save_schemas(self, schemas: Dict[str, Dict]) -> None:
        """Save generated schemas to files."""
        for endpoint, schema in schemas.items():
            schema_file = self.schema_dir / f"{endpoint}.json"
            with open(schema_file, "w") as f:
                json.dump(schema, f, indent=2)

    def validate_request(
        self, endpoint: str, method: str, data: Optional[Dict] = None
    ) -> None:
        """Validate request data against the schema and custom validators."""
        schema = self.load_schema(endpoint)
        request_schema = None
        if schema and "request" in schema:
            request_schema = schema["request"].get(method.lower(), {})

        try:
            # Validate against JSON Schema if schema is present
            if request_schema:
                validate(instance=data or {}, schema=request_schema)

            # Always run custom validators for fields present in data
            if data:
                for field, validator in self.custom_validators.items():
                    if field in data:
                        validator.validate(data)
        except (ValidationError, ValueError) as e:
            raise ValueError(f"Request validation failed: {str(e)}")

        # If we get here, validation passed
        return None

    def validate_response(
        self, endpoint: str, method: str, data: Optional[Dict] = None
    ) -> None:
        """Validate response data against the schema."""
        schema = self.load_schema(endpoint)
        if not schema or "response" not in schema:
            return

        response_schema = schema["response"].get(method.lower(), {})
        if not response_schema:
            return

        try:
            # Validate against JSON Schema
            validate(instance=data or {}, schema=response_schema)

            # Run custom validators for fields present in data
            if data:
                for field, validator in self.custom_validators.items():
                    if field in data:
                        validator.validate(data)
        except (ValidationError, ValueError) as e:
            raise ValueError(f"Response validation failed: {str(e)}")

        # If we get here, validation passed
        return None


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
