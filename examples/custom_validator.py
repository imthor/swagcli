"""
Example of using SwagCli with custom validation
Demonstrates custom validators and schema handling
"""

import json
from swagcli import Swagcli, Config
from swagcli.plugins.validator import SchemaValidator


def main():
    """
    Custom validation runner
    """
    # Initialize validator
    validator = SchemaValidator()

    # Register custom validators
    validator.register_custom_validator(
        "email",
        lambda x: isinstance(x, str) and "@" in x and "." in x.split("@")[1],
        "Value must be a valid email address",
    )

    validator.register_custom_validator(
        "phone",
        lambda x: isinstance(x, str) and x.replace("+", "").replace("-", "").isdigit(),
        "Value must be a valid phone number",
    )

    validator.register_custom_validator(
        "password",
        lambda x: isinstance(x, str)
        and len(x) >= 8
        and any(c.isupper() for c in x)
        and any(c.islower() for c in x)
        and any(c.isdigit() for c in x),
        "Password must be at least 8 characters and contain uppercase, lowercase, and numbers",
    )

    # Define custom schema
    user_schema = {
        "type": "object",
        "required": ["email", "password", "phone"],
        "properties": {
            "email": {"type": "string", "format": "email"},
            "password": {"type": "string", "format": "password"},
            "phone": {"type": "string", "format": "phone"},
        },
    }

    # Register schema
    validator.register_schema("user", user_schema)

    # Configure the client
    config = Config(validator=validator, output_format="json")

    # Initialize SwagCli with custom OpenAPI spec
    swag = Swagcli("https://api.example.com/openapi.json", config=config)

    # Add validation hooks
    def request_hook(request):
        """Validate request data"""
        if request.method in ["POST", "PUT"]:
            validator.validate_request("user", request.method.lower(), request.json)
        return request

    def response_hook(response):
        """Validate response data"""
        if response.status_code == 200:
            validator.validate_response("user", "get", response.json)
        return response

    swag.add_hook("request", request_hook)
    swag.add_hook("response", response_hook)

    # Run the CLI
    swag.run()


if __name__ == "__main__":
    main()
