"""
Example of using SwagCli with GitHub API
Demonstrates OAuth2 authentication and rate limiting
"""

import json
from swagcli import Swagcli, Config, AuthConfig
from swagcli.plugins.rate_limiter import plugin as rate_limiter


def main():
    """
    GitHub API runner with OAuth2 authentication
    """
    # Configure OAuth2 authentication
    auth = AuthConfig(
        auth_type="oauth2",
        client_id="your-github-client-id",
        client_secret="your-github-client-secret",
        token_url="https://github.com/login/oauth/access_token",
    )

    # Configure rate limiting for GitHub API
    rate_limiter.configure(
        requests_per_second=30,  # GitHub's authenticated rate limit
        burst_size=50,
        retry_after_header="X-RateLimit-Reset",
    )

    # Configure the client
    config = Config(auth=auth, timeout=30, output_format="json")

    # Initialize SwagCli with GitHub's OpenAPI spec
    swag = Swagcli(
        "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
        config=config,
    )

    # Add custom hooks
    def response_hook(response):
        """Format response data"""
        if isinstance(response, dict):
            return json.dumps(response, indent=2)
        return response

    swag.add_hook("response", response_hook)

    # Run the CLI
    swag.run()


if __name__ == "__main__":
    main()
