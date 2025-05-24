import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import jwt
from pydantic import BaseModel, SecretStr
import secrets
import aiohttp


class JWTAuth(BaseModel):
    secret: SecretStr
    algorithm: str = "HS256"
    expires_in: int = 3600  # 1 hour
    issuer: Optional[str] = None
    audience: Optional[str] = None

    def generate_token(self, claims: Optional[Dict] = None) -> str:
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

    def verify_token(self, token: str) -> Dict:
        return jwt.decode(
            token,
            self.secret.get_secret_value(),
            algorithms=[self.algorithm],
            issuer=self.issuer,
            audience=self.audience,
        )


class AWSAuth(BaseModel):
    access_key: str
    secret_key: SecretStr
    region: str
    service: str

    def _get_signature_key(self, date_stamp: str) -> bytes:
        k_date = self._sign(
            ("AWS4" + self.secret_key.get_secret_value()).encode("utf-8"), date_stamp
        )
        k_region = self._sign(k_date, self.region)
        k_service = self._sign(k_region, self.service)
        k_signing = self._sign(k_service, "aws4_request")
        return k_signing

    def _sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def get_auth_headers(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        body: Optional[bytes] = None,
    ) -> Dict[str, str]:
        t = datetime.utcnow()
        amz_date = t.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = t.strftime("%Y%m%d")

        # Prepare canonical request
        canonical_uri = path
        canonical_querystring = "&".join(
            f"{k}={v}" for k, v in sorted((query_params or {}).items())
        )

        headers = headers or {}
        headers["host"] = headers.get(
            "host", f"{self.service}.{self.region}.amazonaws.com"
        )
        headers["x-amz-date"] = amz_date

        canonical_headers = "\n".join(
            f"{k.lower()}:{v}" for k, v in sorted(headers.items())
        )

        signed_headers = ";".join(k.lower() for k in sorted(headers.keys()))

        payload_hash = hashlib.sha256(body or b"").hexdigest()

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

        # Prepare string to sign
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self.region}/{self.service}/aws4_request"
        string_to_sign = "\n".join(
            [
                algorithm,
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )

        # Calculate signature
        signing_key = self._get_signature_key(date_stamp)
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Prepare authorization header
        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        return {
            "Authorization": authorization_header,
            "X-Amz-Date": amz_date,
            **headers,
        }


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
