import asyncio
import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import aiohttp
import jwt
from pydantic import BaseModel, SecretStr


class AuthConfig(BaseModel):
    type: str
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    api_key: Optional[SecretStr] = None
    api_key_header: Optional[str] = None
    token: Optional[SecretStr] = None
    token_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[SecretStr] = None
    scope: Optional[str] = None


class BasicAuth:
    def __init__(self, username: str, password: SecretStr) -> None:
        self.username = username
        self.password = password

    def get_headers(self) -> Dict[str, str]:
        auth_str = f"{self.username}:{self.password.get_secret_value()}"
        return {
            "Authorization": f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        }


class ApiKeyAuth:
    def __init__(self, api_key: SecretStr, header_name: str = "X-API-Key") -> None:
        self.api_key = api_key
        self.header_name = header_name

    def get_headers(self) -> Dict[str, str]:
        return {self.header_name: self.api_key.get_secret_value()}


class OAuth2Auth:
    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: SecretStr,
        scope: Optional[str] = None,
    ) -> None:
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def get_headers(self) -> Dict[str, str]:
        if not self._token or (
            self._token_expiry and datetime.now() >= self._token_expiry
        ):
            self._refresh_token()
        return {"Authorization": f"Bearer {self._token}"}

    def _refresh_token(self) -> None:
        async def get_token() -> str:
            async with aiohttp.ClientSession() as session:
                data = {
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret.get_secret_value(),
                }
                if self.scope:
                    data["scope"] = self.scope

                async with session.post(self.token_url, data=data) as response:
                    token_data = await response.json()
                    self._token = token_data["access_token"]
                    if "expires_in" in token_data:
                        self._token_expiry = datetime.now() + timedelta(
                            seconds=token_data["expires_in"]
                        )
                    return self._token

        self._token = asyncio.run(get_token())


class JWTAuth:
    def __init__(
        self,
        secret: Union[str, SecretStr],
        algorithm: str = "HS256",
        expires_in: int = 3600,
        issuer: str = None,
        audience: str = None,
    ) -> None:
        if isinstance(secret, SecretStr):
            self.secret = secret
        else:
            self.secret = SecretStr(secret)
        self.algorithm = algorithm
        self.expires_in = expires_in
        self.issuer = issuer
        self.audience = audience

    def generate_token(self, claims: Optional[Dict[str, Any]] = None) -> str:
        now = datetime.utcnow()
        token_claims = {
            "iat": now,
            "exp": now + timedelta(seconds=self.expires_in),
            **(claims or {}),
        }
        if self.issuer:
            token_claims["iss"] = self.issuer
        if self.audience:
            token_claims["aud"] = self.audience
        return jwt.encode(
            token_claims, self.secret.get_secret_value(), algorithm=self.algorithm
        )

    def verify_token(self, token: str) -> Dict[str, Any]:
        return jwt.decode(
            token,
            self.secret.get_secret_value(),
            algorithms=[self.algorithm],
            issuer=self.issuer,
            audience=self.audience,
        )

    def get_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        token = jwt.encode(
            payload,
            self.secret.get_secret_value(),
            algorithm=self.algorithm,
        )
        return {"Authorization": f"Bearer {token}"}


class AWSAuth:
    def __init__(
        self,
        access_key: str,
        secret_key: Union[str, SecretStr],
        region: str,
        service: str,
    ) -> None:
        self.access_key = access_key
        if isinstance(secret_key, SecretStr):
            self.secret_key = secret_key
        else:
            self.secret_key = SecretStr(secret_key)
        self.region = region
        self.service = service

    def get_headers(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Dict[str, str]:
        # AWS Signature Version 4
        now = datetime.utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        # Canonical request
        canonical_uri = path
        canonical_querystring = ""
        if query_params:
            canonical_querystring = "&".join(
                f"{k}={v}" for k, v in sorted(query_params.items())
            )

        host = f"{self.service}.{self.region}.amazonaws.com"
        canonical_headers = f"host:{host}\nx-amz-date:{amz_date}\n"

        signed_headers = "host;x-amz-date"

        payload_hash = hashlib.sha256("".encode()).hexdigest()

        canonical_request = "\n".join(
            [
                method,
                canonical_uri,
                canonical_querystring,
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )

        # String to sign
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = "\n".join(
            [
                algorithm,
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            ]
        )

        # Calculate signature
        def sign(key: bytes, msg: str) -> bytes:
            return hmac.new(key, msg.encode(), hashlib.sha256).digest()

        k_date = sign(f"AWS4{self.secret_key.get_secret_value()}".encode(), date_stamp)
        k_region = sign(k_date, self.region)
        k_service = sign(k_region, self.service)
        k_signing = sign(k_service, "aws4_request")
        signature = hmac.new(
            k_signing, string_to_sign.encode(), hashlib.sha256
        ).hexdigest()

        # Return headers
        return {
            "Authorization": f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}",
            "X-Amz-Date": amz_date,
            "host": host,
        }

    def get_auth_headers(self, *args, **kwargs) -> Dict[str, str]:
        return self.get_headers(*args, **kwargs)


class OAuth2PKCEAuth(BaseModel):
    client_id: str
    redirect_uri: str
    scope: str
    code_verifier: Optional[str] = None
    code_challenge: Optional[str] = None
    state: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.code_verifier:
            self.code_verifier = self._generate_code_verifier()
        if not self.code_challenge:
            self.code_challenge = self._generate_code_challenge()
        if not self.state:
            self.state = self._generate_state()

    def _generate_code_verifier(self) -> str:
        """Generate a code verifier for PKCE."""
        verifier = secrets.token_urlsafe(32)
        return verifier[:128]  # PKCE spec requires max 128 chars

    def _generate_code_challenge(self) -> str:
        """Generate a code challenge from the verifier."""
        sha256_hash = hashlib.sha256(self.code_verifier.encode()).digest()
        return base64.urlsafe_b64encode(sha256_hash).decode().rstrip("=")

    def _generate_state(self) -> str:
        """Generate a state parameter for CSRF protection."""
        return secrets.token_urlsafe(16)

    def get_authorization_url(self, auth_endpoint: str) -> str:
        """Get the authorization URL for the OAuth2 flow."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope.replace(" ", "+"),  # URL encode space as +
            "response_type": "code",
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256",
            "state": self.state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{auth_endpoint}?{query}"

    def get_token_request_data(self, code: str) -> Dict[str, str]:
        """Get the data for the token request."""
        return {
            "client_id": self.client_id,
            "code": code,
            "code_verifier": self.code_verifier,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }


class AzureADAuth(BaseModel):
    client_id: str
    client_secret: SecretStr
    tenant_id: str
    scope: str = "https://graph.microsoft.com/.default"
    token_endpoint: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.token_endpoint:
            self.token_endpoint = (
                f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            )

    def get_token_request_data(self) -> Dict[str, str]:
        """Get the data for the token request."""
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret.get_secret_value(),
            "scope": self.scope,
            "grant_type": "client_credentials",
        }

    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """Get the authorization headers with the token."""
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def get_token(self, session: aiohttp.ClientSession) -> str:
        """Get a new access token."""
        async with session.post(
            self.token_endpoint, data=self.get_token_request_data()
        ) as response:
            data = await response.json()
            return data["access_token"]
