# SwagCli

A powerful command-line interface generator for Swagger/OpenAPI specifications.

## Features

- Generate CLI commands from Swagger/OpenAPI specifications
- Support for multiple authentication methods:
  - API Key
  - Basic Auth
  - OAuth2
  - OAuth2 with PKCE
  - JWT
  - AWS Signature
  - Azure AD
- Request/response validation using JSON Schema
- Extensible plugin system
- Request/response caching
- File upload/download support
- Rate limiting
- Metrics collection
- Custom validators
- OpenAPI schema generation

## When to Use SwagCli

SwagCli is particularly useful in the following scenarios:

1. **API Development and Testing**
   - When you need to quickly test and validate API endpoints
   - During API development to ensure endpoints work as expected
   - For automated testing of API responses and schemas

2. **DevOps and Automation**
   - When automating API interactions in CI/CD pipelines
   - For monitoring and metrics collection of API usage
   - When implementing rate limiting and caching strategies

3. **API Integration**
   - When integrating with third-party APIs that use Swagger/OpenAPI specs
   - For handling complex authentication flows (OAuth2, JWT, etc.)
   - When working with cloud services (AWS, Azure, etc.)

4. **API Documentation and Testing**
   - When generating and validating OpenAPI schemas
   - For testing API documentation against actual implementations
   - When implementing custom validation rules

5. **Enterprise Applications**
   - When dealing with multiple authentication methods
   - For implementing secure file upload/download operations
   - When requiring detailed request/response logging
   - For implementing caching strategies in distributed systems

6. **Microservices Architecture**
   - When working with multiple microservices
   - For implementing service-to-service communication
   - When requiring consistent API interaction patterns

7. **Security and Compliance**
   - When implementing secure authentication flows
   - For logging and auditing API interactions
   - When requiring request/response validation

## Benefits of Using SwagCli

SwagCli provides significant advantages in these scenarios:

1. **Time and Resource Savings**
   - Automatically generates CLI commands from OpenAPI specs, eliminating manual implementation
   - Reduces development time for API integration and testing
   - Streamlines the process of implementing complex authentication flows

2. **Consistency and Reliability**
   - Ensures consistent API interaction patterns across your application
   - Validates requests and responses against schemas automatically
   - Maintains standardized error handling and response processing

3. **Enhanced Security**
   - Built-in support for industry-standard authentication methods
   - Automatic token refresh and management
   - Secure handling of sensitive credentials and tokens

4. **Improved Developer Experience**
   - Simple, intuitive interface for API interactions
   - Comprehensive logging and debugging capabilities
   - Built-in support for common development workflows

5. **Scalability and Performance**
   - Efficient request/response caching
   - Built-in rate limiting to prevent API abuse
   - Optimized file handling for uploads and downloads

6. **Monitoring and Observability**
   - Detailed metrics collection for API usage
   - Comprehensive request/response logging
   - Easy integration with monitoring systems

7. **Flexibility and Extensibility**
   - Plugin system for custom functionality
   - Support for custom validators and schemas
   - Easy integration with existing tools and workflows

## Installation

```bash
pip install swagcli
```

## Quick Start

```python
from swagcli import APIClient, Config, AuthConfig

# Configure authentication
auth = AuthConfig(
    auth_type="api_key",
    api_key="your-api-key"
)

# Create client
client = APIClient(
    base_url="https://api.example.com",
    config=Config(auth=auth)
)

# Make requests
response = client.get("/users")
print(response)
```

## Authentication Methods

### API Key
```python
auth = AuthConfig(
    auth_type="api_key",
    api_key="your-api-key"
)
```

### Basic Auth
```python
auth = AuthConfig(
    auth_type="basic",
    username="user",
    password="pass"
)
```

### OAuth2
```python
auth = AuthConfig(
    auth_type="oauth2",
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://auth.example.com/token"
)
```

### OAuth2 with PKCE
```python
from swagcli.auth import OAuth2PKCEAuth

auth = OAuth2PKCEAuth(
    client_id="your-client-id",
    redirect_uri="http://localhost:8080/callback",
    scope="read write"
)

# Get authorization URL
auth_url = auth.get_authorization_url("https://auth.example.com/authorize")

# After user authorization, get token
token_data = auth.get_token_request_data("authorization-code")

# Configure client with PKCE auth
client = APIClient(
    base_url="https://api.example.com",
    config=Config(auth=auth)
)

# Token will be automatically refreshed when expired
response = client.get("/protected-resource")
```

### JWT
```python
from swagcli.auth import JWTAuth

auth = JWTAuth(
    secret="your-secret",
    algorithm="HS256",
    expires_in=3600,
    audience="api.example.com",
    issuer="auth.example.com"
)

# Generate token with custom claims
token = auth.generate_token({
    "sub": "user123",
    "roles": ["admin", "user"],
    "permissions": ["read", "write"]
})

# Configure client with JWT auth
client = APIClient(
    base_url="https://api.example.com",
    config=Config(auth=auth)
)

# Token will be automatically included in requests
response = client.get("/protected-resource")
```

### AWS Signature
```python
from swagcli.auth import AWSAuth

auth = AWSAuth(
    access_key="your-access-key",
    secret_key="your-secret-key",
    region="us-west-2",
    service="s3",
    session_token="optional-session-token"  # For temporary credentials
)

# Configure client with AWS auth
client = APIClient(
    base_url="https://s3.us-west-2.amazonaws.com",
    config=Config(auth=auth)
)

# Requests will be automatically signed
response = client.get("/bucket-name/object-key")
```

### Azure AD
```python
from swagcli.auth import AzureADAuth

auth = AzureADAuth(
    client_id="your-client-id",
    client_secret="your-client-secret",
    tenant_id="your-tenant-id",
    resource="https://management.azure.com",  # Optional resource URL
    scope=["https://graph.microsoft.com/.default"]  # Optional scopes
)

# Get token with specific scopes
token = await auth.get_token(session, scopes=["https://graph.microsoft.com/User.Read"])

# Configure client with Azure AD auth
client = APIClient(
    base_url="https://graph.microsoft.com/v1.0",
    config=Config(auth=auth)
)

# Token will be automatically refreshed when expired
response = client.get("/me")
```

## Validation

### JSON Schema Validation
```python
from swagcli.plugins.validator import SchemaValidator

validator = SchemaValidator()

# Load schema
schema = validator.load_schema("users")

# Validate request
validator.validate_request("users", "post", {
    "name": "John",
    "age": 30
})
```

### Custom Validators
```python
validator = SchemaValidator()

# Register custom validator
validator.register_custom_validator(
    "email",
    lambda x: isinstance(x, str) and "@" in x,
    "Value must be a valid email"
)

# Validate with custom validator
validator.validate_request("users", "post", {
    "email": "test@example.com"
})
```

### OpenAPI Schema Generation
```python
validator = SchemaValidator()

# Generate schemas from OpenAPI spec
schemas = validator.generate_schema_from_openapi(openapi_spec)

# Save schemas
validator.save_schemas(schemas)
```

## Plugins

### File Handler
```python
from swagcli.plugins.file_handler import plugin as file_handler

# Upload multiple files
response = client.post("/upload", files={
    "document": "path/to/document.pdf",
    "image": "path/to/image.jpg"
})

# Upload with custom metadata
response = client.post("/upload", files={
    "file": "path/to/file.txt"
}, data={
    "description": "Important document",
    "tags": ["confidential", "draft"]
})

# Download file with progress tracking
response = client.get("/download", stream=True)
response.save_to_file(
    "downloaded.txt",
    progress_callback=lambda current, total: print(f"Downloaded {current}/{total} bytes")
)

# Download multiple files
response = client.get("/download-multiple", stream=True)
response.save_to_directory("downloads/")
```

### Rate Limiter
```python
from swagcli.plugins.rate_limiter import plugin as rate_limiter

# Configure rate limits with custom strategies
rate_limiter.configure(
    requests_per_second=10,
    burst_size=20,
    strategy="token-bucket",  # or "leaky-bucket"
    retry_after_header="X-RateLimit-Reset"
)

# Add custom rate limit rules
rate_limiter.add_rule(
    endpoint="/api/v1/users",
    requests_per_second=5,
    burst_size=10
)

# Get current rate limit status
status = rate_limiter.get_status()
print(f"Remaining requests: {status.remaining}")
print(f"Reset time: {status.reset_time}")
```

### Metrics Collector
```python
from swagcli.plugins.metrics import plugin as metrics

# Configure metrics collection
metrics.configure(
    enabled=True,
    storage="prometheus",  # or "influxdb", "statsd"
    labels=["endpoint", "method", "status_code"]
)

# Get detailed metrics
metrics_data = metrics.get_metrics()
print("Request counts:", metrics_data.request_counts)
print("Response times:", metrics_data.response_times)
print("Error rates:", metrics_data.error_rates)

# Export metrics to Prometheus
metrics.export_prometheus(port=9090)

# Get custom metrics
custom_metrics = metrics.get_custom_metrics(
    time_range="1h",
    group_by=["endpoint", "status_code"]
)
```

### Request Logger
```python
from swagcli.plugins.request_logger import plugin as request_logger

# Configure logging
request_logger.configure(
    log_level="DEBUG",
    log_format="json",
    include_headers=True,
    include_body=True,
    sensitive_fields=["password", "token"]
)

# Custom log handler
def custom_log_handler(request, response):
    print(f"Custom logging: {request.method} {request.url}")

request_logger.add_handler(custom_log_handler)

# Get recent logs
recent_logs = request_logger.get_recent_logs(
    count=10,
    filter_by={"status_code": 200}
)
```

### Cache Plugin
```python
from swagcli.plugins.cache import plugin as cache

# Configure caching
cache.configure(
    storage="redis",  # or "memory", "file"
    ttl=300,
    max_size=1000,
    exclude_paths=["/auth/*", "/metrics/*"]
)

# Custom cache key generator
def custom_cache_key(request):
    return f"{request.method}:{request.url}:{request.headers.get('X-Custom-Header')}"

cache.set_key_generator(custom_cache_key)

# Manual cache operations
cache.set("key", "value", ttl=60)
value = cache.get("key")
cache.delete("key")
cache.clear()
```

## Configuration

The API client can be configured with various options:

```python
from swagcli import Config, CacheConfig

config = Config(
    cache=CacheConfig(
        enabled=True,
        ttl=300,  # 5 minutes
        max_size=1000
    ),
    timeout=30,
    output_format="json"
)
```

## Development

### Setup
```bash
git clone https://github.com/yourusername/swagcli.git
cd swagcli
pip install -e ".[dev]"
```

### Running Tests
```bash
pytest
```

### Code Style
```bash
black .
isort .
mypy .
ruff check .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License
