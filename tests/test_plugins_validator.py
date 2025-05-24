import json
import pytest
from pathlib import Path
from swagcli.plugins.validator import plugin, SchemaValidator, on_request, on_response


@pytest.fixture
def schema_dir(tmp_path):
    return tmp_path / "schemas"


@pytest.fixture
def validator(schema_dir):
    return SchemaValidator(schema_dir)


@pytest.fixture
def test_schema(schema_dir):
    schema = {
        "request": {
            "post": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer", "minimum": 0},
                },
                "required": ["name"],
            }
        },
        "response": {
            "get": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                "required": ["id", "name"],
            }
        },
    }

    schema_file = schema_dir / "users.json"
    schema_file.parent.mkdir(parents=True, exist_ok=True)
    with open(schema_file, "w") as f:
        json.dump(schema, f)

    return schema


def test_schema_loading(validator, test_schema):
    schema = validator.load_schema("users")
    assert schema == test_schema


def test_request_validation(validator, test_schema):
    # Valid request
    validator.validate_request("users", "post", {"name": "John", "age": 30})

    # Invalid request - missing required field
    with pytest.raises(ValueError):
        validator.validate_request("users", "post", {"age": 30})

    # Invalid request - wrong type
    with pytest.raises(ValueError):
        validator.validate_request("users", "post", {"name": "John", "age": "30"})


def test_response_validation(validator, test_schema):
    # Valid response
    validator.validate_response("users", "get", {"id": 1, "name": "John"})

    # Invalid response - missing required field
    with pytest.raises(ValueError):
        validator.validate_response("users", "get", {"id": 1})

    # Invalid response - wrong type
    with pytest.raises(ValueError):
        validator.validate_response("users", "get", {"id": "1", "name": "John"})


def test_on_request_hook(validator, test_schema):
    # Valid request
    on_request(
        "POST", "https://api.example.com/users", data={"name": "John", "age": 30}
    )

    # Invalid request - should print warning
    on_request("POST", "https://api.example.com/users", data={"age": 30})


def test_on_response_hook(validator, test_schema):
    # Valid response
    on_response(
        {
            "url": "https://api.example.com/users",
            "method": "GET",
            "data": {"id": 1, "name": "John"},
        }
    )

    # Invalid response - should print warning
    on_response(
        {"url": "https://api.example.com/users", "method": "GET", "data": {"id": 1}}
    )


def test_plugin_metadata():
    assert plugin.name == "validator"
    assert plugin.description == "Validates requests and responses using JSON Schema"
    assert plugin.version == "1.0.0"
    assert plugin.author == "SwagCli Team"


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
