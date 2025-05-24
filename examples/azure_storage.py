"""
Example of using SwagCli with Azure Storage
Demonstrates Azure AD authentication and blob storage operations
"""

import os
import asyncio
from swagcli import Swagcli, Config, AuthConfig
from swagcli.plugins.cache import plugin as cache
from swagcli.plugins.request_logger import plugin as request_logger


async def main():
    """
    Azure Storage runner with Azure AD authentication
    """
    # Configure Azure AD authentication
    auth = AuthConfig(
        auth_type="azure_ad",
        client_id=os.getenv("AZURE_CLIENT_ID"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET"),
        tenant_id=os.getenv("AZURE_TENANT_ID"),
        resource="https://storage.azure.com",
        scope=["https://storage.azure.com/.default"],
    )

    # Configure caching for blob operations
    cache.configure(storage="redis", ttl=300, max_size=1000, exclude_paths=["/auth/*"])

    # Configure request logging
    request_logger.configure(
        log_level="INFO",
        log_format="json",
        include_headers=True,
        sensitive_fields=["Authorization", "x-ms-date"],
    )

    # Configure the client
    config = Config(auth=auth, timeout=30, output_format="json")

    # Initialize SwagCli with Azure Storage OpenAPI spec
    swag = Swagcli(
        "https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/specification/storage/data-plane/Microsoft.Storage/stable/2021-04-10/blob.json",
        config=config,
    )

    # Add custom hooks for Azure Storage operations
    def request_hook(request):
        """Add required Azure Storage headers"""
        request.headers.update(
            {
                "x-ms-version": "2021-04-10",
                "x-ms-date": request.headers.get("x-ms-date", ""),
            }
        )
        return request

    swag.add_hook("request", request_hook)

    # Run the CLI
    await swag.run_async()


if __name__ == "__main__":
    asyncio.run(main())
