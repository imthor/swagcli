import json
from pathlib import Path

import pytest

from swagcli.plugins.validator import SchemaValidator


@pytest.fixture
def schema_dir(tmp_path):
    return tmp_path / "schemas"


@pytest.fixture
def validator():
    return SchemaValidator()


@pytest.fixture
def test_schema():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
        },
        "required": ["name"],
    }
    return schema


def test_register_and_validate_schema(validator, test_schema):
    validator.register_schema("users", test_schema)
    # Valid data
    assert validator.validate_schema("users", {"name": "John", "age": 30}) is None
    # Invalid data (missing required field)
    result = validator.validate_schema("users", {"age": 30})
    assert result is not None and "error" in result
    # Invalid data (wrong type)
    result = validator.validate_schema("users", {"name": "John", "age": "30"})
    assert result is not None and "error" in result


def test_on_request_and_on_response(validator, test_schema):
    validator.register_schema("users", test_schema)
    # on_request with valid data
    assert (
        validator.on_request("POST", "/users", None, {"name": "John", "age": 30})
        is None
    )
    # on_request with invalid data
    result = validator.on_request("POST", "/users", None, {"age": 30})
    assert result is not None and "error" in result
    # on_response with valid data
    response = {"url": "/users", "data": {"name": "John", "age": 30}}
    assert validator.on_response(response) is None
    # on_response with invalid data
    response = {"url": "/users", "data": {"age": 30}}
    result = validator.on_response(response)
    assert result is not None and "error" in result


def test_plugin_metadata():
    validator = SchemaValidator()
    assert validator.name == "validator"
    assert validator.description == "Validates requests and responses using JSON Schema"
    assert validator.version == "1.0.0"
    assert validator.author == "SwagCli Team"


def test_custom_validator(validator):
    # Register a custom validator
    validator.register_custom_validator(
        "age",
        lambda x: isinstance(x, (int, float)) and x > 0,
        "Value must be a positive number",
    )

    # Test valid data
    validator.validate_request("users", "post", {"age": 30})

    # Test invalid data
    with pytest.raises(ValueError, match="Request validation failed"):
        validator.validate_request("users", "post", {"age": -1})


def test_openapi_schema_generation(validator):
    openapi_spec = {
        "paths": {
            "/users": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "age": {"type": "integer"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    },
                }
            }
        }
    }

    schemas = validator.generate_schema_from_openapi(openapi_spec)
    assert "users" in schemas
    assert "post" in schemas["users"]["request"]
    assert "post" in schemas["users"]["response"]


def test_schema_saving(validator, tmp_path):
    schemas = {
        "users": {
            "request": {
                "post": {"type": "object", "properties": {"name": {"type": "string"}}}
            }
        }
    }

    validator.schema_dir = tmp_path
    validator.save_schemas(schemas)

    schema_file = tmp_path / "users.json"
    assert schema_file.exists()

    with open(schema_file) as f:
        saved_schema = json.load(f)
        assert saved_schema == schemas["users"]


def test_multiple_custom_validators(validator):
    # Register multiple validators
    validator.register_custom_validator(
        "email",
        lambda x: isinstance(x, str) and "@" in x,
        "Value must be a valid email",
    )
    validator.register_custom_validator(
        "password",
        lambda x: isinstance(x, str) and len(x) >= 8,
        "Password must be at least 8 characters",
    )

    # Test valid data
    validator.validate_request(
        "users", "post", {"email": "test@example.com", "password": "secure123"}
    )

    # Test invalid data
    with pytest.raises(ValueError, match="Request validation failed"):
        validator.validate_request(
            "users", "post", {"email": "invalid-email", "password": "short"}
        )


def test_openapi_schema_with_multiple_methods(validator):
    openapi_spec = {
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"name": {"type": "string"}},
                                }
                            }
                        }
                    }
                },
            }
        }
    }

    schemas = validator.generate_schema_from_openapi(openapi_spec)
    assert "users" in schemas
    assert "get" in schemas["users"]["response"]
    assert "post" in schemas["users"]["request"]
