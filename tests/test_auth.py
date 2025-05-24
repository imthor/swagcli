import pytest
from datetime import datetime, timedelta
from swagcli.auth import JWTAuth, AWSAuth, OAuth2PKCEAuth, AzureADAuth
import aiohttp


@pytest.fixture
def jwt_auth():
    return JWTAuth(
        secret="test-secret",
        algorithm="HS256",
        expires_in=3600,
        issuer="test-issuer",
        audience="test-audience",
    )


@pytest.fixture
def aws_auth():
    return AWSAuth(
        access_key="test-access-key",
        secret_key="test-secret-key",
        region="us-west-2",
        service="s3",
    )


@pytest.fixture
def oauth2_pkce_auth():
    return OAuth2PKCEAuth(
        client_id="test-client",
        redirect_uri="http://localhost:8080/callback",
        scope="read write",
    )


@pytest.fixture
def azure_ad_auth():
    return AzureADAuth(
        client_id="test-client", client_secret="test-secret", tenant_id="test-tenant"
    )


def test_jwt_token_generation(jwt_auth):
    token = jwt_auth.generate_token({"sub": "test-user"})
    assert token is not None

    # Verify token
    claims = jwt_auth.verify_token(token)
    assert claims["sub"] == "test-user"
    assert claims["iss"] == "test-issuer"
    assert claims["aud"] == "test-audience"

    # Check expiration
    exp = datetime.fromtimestamp(claims["exp"])
    iat = datetime.fromtimestamp(claims["iat"])
    assert exp - iat == timedelta(seconds=3600)


def test_jwt_token_verification_failure(jwt_auth):
    # Generate token with different secret
    wrong_auth = JWTAuth(secret="wrong-secret")
    token = wrong_auth.generate_token()

    # Should fail verification
    with pytest.raises(Exception):
        jwt_auth.verify_token(token)


def test_aws_auth_headers(aws_auth):
    headers = aws_auth.get_auth_headers(
        method="GET",
        path="/test",
        query_params={"param": "value"},
        headers={"Content-Type": "application/json"},
        body=b'{"key": "value"}',
    )

    assert "Authorization" in headers
    assert headers["Authorization"].startswith("AWS4-HMAC-SHA256")
    assert "X-Amz-Date" in headers
    assert "host" in headers
    assert headers["host"] == "s3.us-west-2.amazonaws.com"


def test_aws_auth_different_methods(aws_auth):
    # Test different HTTP methods
    methods = ["GET", "POST", "PUT", "DELETE"]
    for method in methods:
        headers = aws_auth.get_auth_headers(method, "/test")
        assert headers["Authorization"].startswith("AWS4-HMAC-SHA256")


def test_aws_auth_different_regions(aws_auth):
    # Test different regions
    regions = ["us-east-1", "eu-west-1", "ap-southeast-1"]
    for region in regions:
        aws_auth.region = region
        headers = aws_auth.get_auth_headers("GET", "/test")
        assert headers["host"] == f"s3.{region}.amazonaws.com"


def test_oauth2_pkce_authorization_url(oauth2_pkce_auth):
    auth_url = oauth2_pkce_auth.get_authorization_url(
        "https://auth.example.com/authorize"
    )

    assert "client_id=test-client" in auth_url
    assert "redirect_uri=http://localhost:8080/callback" in auth_url
    assert "scope=read+write" in auth_url
    assert "response_type=code" in auth_url
    assert "code_challenge=" in auth_url
    assert "code_challenge_method=S256" in auth_url
    assert "state=" in auth_url


def test_oauth2_pkce_token_request(oauth2_pkce_auth):
    data = oauth2_pkce_auth.get_token_request_data("test-code")

    assert data["client_id"] == "test-client"
    assert data["code"] == "test-code"
    assert data["code_verifier"] == oauth2_pkce_auth.code_verifier
    assert data["redirect_uri"] == "http://localhost:8080/callback"
    assert data["grant_type"] == "authorization_code"


def test_azure_ad_token_request(azure_ad_auth):
    data = azure_ad_auth.get_token_request_data()

    assert data["client_id"] == "test-client"
    assert data["client_secret"] == "test-secret"
    assert data["scope"] == "https://graph.microsoft.com/.default"
    assert data["grant_type"] == "client_credentials"


@pytest.mark.asyncio
async def test_azure_ad_get_token(azure_ad_auth):
    async with aiohttp.ClientSession() as session:
        with pytest.raises(Exception):  # Should fail without mock
            await azure_ad_auth.get_token(session)


def test_azure_ad_auth_headers(azure_ad_auth):
    headers = azure_ad_auth.get_auth_headers("test-token")

    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Content-Type"] == "application/json"
