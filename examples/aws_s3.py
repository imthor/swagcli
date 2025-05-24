"""
Example of using SwagCli with AWS S3
Demonstrates AWS Signature authentication and file operations
"""

import os
from swagcli import Swagcli, Config, AuthConfig
from swagcli.plugins.file_handler import plugin as file_handler
from swagcli.plugins.metrics import plugin as metrics


def main():
    """
    AWS S3 runner with AWS Signature authentication
    """
    # Configure AWS authentication
    auth = AuthConfig(
        auth_type="aws",
        access_key=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region=os.getenv("AWS_REGION", "us-west-2"),
        service="s3",
    )

    # Configure file handler for S3 operations
    file_handler.configure(
        chunk_size=8 * 1024 * 1024,  # 8MB chunks for multipart upload
        max_retries=3,
    )

    # Configure metrics collection
    metrics.configure(
        enabled=True,
        storage="prometheus",
        labels=["operation", "bucket", "status_code"],
    )

    # Configure the client
    config = Config(
        auth=auth,
        timeout=60,  # Longer timeout for file operations
        output_format="json",
    )

    # Initialize SwagCli with S3 OpenAPI spec
    swag = Swagcli(
        "https://raw.githubusercontent.com/aws/aws-sdk-js/main/apis/s3-2006-03-01.normal.json",
        config=config,
    )

    # Add custom hooks for S3 operations
    def upload_hook(request):
        """Add content type for uploads"""
        if request.method == "PUT" and "file" in request.files:
            file_path = request.files["file"]
            content_type = file_handler.get_content_type(file_path)
            request.headers["Content-Type"] = content_type
        return request

    swag.add_hook("request", upload_hook)

    # Run the CLI
    swag.run()


if __name__ == "__main__":
    main()
