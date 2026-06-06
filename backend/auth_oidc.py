"""
auth_oidc.py
────────────
OpenID Connect (OIDC) authentication integration.

Supports:
- Okta
- Azure AD (Entra ID)
- Google Identity
- Custom OIDC providers

Usage:
    from backend.auth_oidc import OIDCProvider
    
    provider = OIDCProvider(
        client_id="your_client_id",
        client_secret="your_client_secret",
        discovery_url="https://your-provider/.well-known/openid-configuration"
    )
    
    # Verify token
    user_info = provider.verify_token(access_token)
    
    # Get authorization URL
    auth_url = provider.get_authorization_url(redirect_uri)
    
    # Exchange code for token
    token = provider.get_token(code, redirect_uri)
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
import jwt
from pydantic import BaseModel, ConfigDict

from backend.logging_config import get_logger

logger = get_logger(__name__)


class UserInfo(BaseModel):
    """User information from OIDC provider."""
    
    sub: str  # Subject (unique user ID)
    email: Optional[str] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False
    groups: Optional[list[str]] = None  # For Azure AD, Okta
    roles: Optional[list[str]] = None  # For custom providers
    org_id: Optional[str] = None  # Organization ID

    model_config = ConfigDict(extra="allow")


class TokenPayload(BaseModel):
    """JWT token payload."""
    
    sub: str
    email: Optional[str] = None
    name: Optional[str] = None
    exp: int
    iat: int
    aud: Optional[str | list[str]] = None
    iss: Optional[str] = None


class OIDCProvider:
    """OpenID Connect provider client."""
    
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        discovery_url: str,
        cache_well_known: bool = True,
    ):
        """
        Initialize OIDC provider.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            discovery_url: OIDC discovery endpoint (.well-known/openid-configuration)
            cache_well_known: Cache discovery endpoint response
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.discovery_url = discovery_url
        self.cache_well_known = cache_well_known
        self._well_known_cache: Optional[dict[str, Any]] = None
        self._jwks_cache: Optional[dict[str, Any]] = None
        
        logger.info(
            "OIDC provider initialized",
            extra={
                "client_id": client_id,
                "discovery_url": discovery_url,
            }
        )
    
    async def get_well_known(self) -> dict[str, Any]:
        """Fetch OpenID Connect discovery document."""
        if self.cache_well_known and self._well_known_cache:
            return self._well_known_cache
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.discovery_url, timeout=10.0)
            response.raise_for_status()
            well_known = response.json()
        
        if self.cache_well_known:
            self._well_known_cache = well_known
        
        return well_known
    
    async def get_jwks(self) -> dict[str, Any]:
        """Fetch JSON Web Key Set for token verification."""
        if self._jwks_cache:
            return self._jwks_cache
        
        well_known = await self.get_well_known()
        jwks_uri = well_known.get("jwks_uri")
        
        if not jwks_uri:
            raise ValueError("OIDC provider does not expose jwks_uri")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_uri, timeout=10.0)
            response.raise_for_status()
            jwks = response.json()
        
        self._jwks_cache = jwks
        return jwks
    
    async def verify_token(self, token: str) -> UserInfo:
        """
        Verify and decode JWT token from OIDC provider.
        
        Args:
            token: ID token from OIDC provider
            
        Returns:
            UserInfo with validated claims
            
        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        # Get discovery document
        well_known = await self.get_well_known()
        issuer = well_known.get("issuer")
        
        # Decode header to get kid (key ID)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        
        # Get JWKS and find the key
        jwks = await self.get_jwks()
        key = self._find_key(jwks, kid)
        
        if not key:
            raise jwt.InvalidTokenError(f"Key {kid} not found in JWKS")
        
        # Convert JWK to PEM format
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            pem_key = self._jwk_to_pem(key)
        except Exception as e:
            logger.error("Failed to convert JWK to PEM", extra={"error": str(e)})
            raise jwt.InvalidTokenError("Failed to process key") from e
        
        # Verify and decode token
        try:
            payload = jwt.decode(
                token,
                pem_key,
                algorithms=header.get("alg", "RS256"),
                audience=self.client_id,
                issuer=issuer,
            )
        except jwt.InvalidTokenError as e:
            logger.warning(
                "Token verification failed",
                extra={
                    "error": str(e),
                    "client_id": self.client_id,
                }
            )
            raise
        
        logger.info(
            "Token verified",
            extra={
                "sub": payload.get("sub"),
                "email": payload.get("email"),
            }
        )
        
        return UserInfo(**payload)
    
    async def get_authorization_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
        nonce: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Generate authorization URL for user login.
        
        Args:
            redirect_uri: Where to redirect after login
            state: State parameter for CSRF protection
            nonce: Nonce for token binding
            **kwargs: Additional parameters (scope, prompt, etc)
            
        Returns:
            Full authorization URL
        """
        well_known = await self.get_well_known()
        auth_endpoint = well_known.get("authorization_endpoint")
        
        if not auth_endpoint:
            raise ValueError("OIDC provider does not expose authorization_endpoint")
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": kwargs.pop("scope", "openid email profile"),
            "redirect_uri": redirect_uri,
        }
        
        if state:
            params["state"] = state
        if nonce:
            params["nonce"] = nonce
        
        params.update(kwargs)
        
        return f"{auth_endpoint}?{urlencode(params)}"
    
    async def get_token(
        self,
        code: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            redirect_uri: Must match authorization request
            
        Returns:
            Token response with access_token, id_token, etc
        """
        well_known = await self.get_well_known()
        token_endpoint = well_known.get("token_endpoint")
        
        if not token_endpoint:
            raise ValueError("OIDC provider does not expose token_endpoint")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            tokens = response.json()
        
        logger.info(
            "Token exchange successful",
            extra={
                "token_type": tokens.get("token_type"),
            }
        )
        
        return tokens
    
    @staticmethod
    def _find_key(jwks: dict[str, Any], kid: Optional[str]) -> Optional[dict[str, Any]]:
        """Find key in JWKS by kid."""
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        # If no kid specified, return first key
        if not kid and jwks.get("keys"):
            return jwks["keys"][0]
        return None
    
    @staticmethod
    def _jwk_to_pem(key: dict[str, Any]) -> str:
        """Convert JWK to PEM format for jwt.decode()."""
        # For RS256/RS512, we can use the JWK directly with python-jose
        # This is a simplified version - consider using python-jose for full support
        try:
            from jose import utils
            return utils.base64url_decode(key.get("x5c", [""])[0])
        except Exception:
            # Fallback: return the key as-is for cryptography library
            pass
        
        # For simplicity, use cryptography to construct the public key
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            
            # Build RSA key from JWK components
            e = int.from_bytes(
                __import__("base64").urlsafe_b64decode(key["e"] + "=="),
                byteorder="big"
            )
            n = int.from_bytes(
                __import__("base64").urlsafe_b64decode(key["n"] + "=="),
                byteorder="big"
            )
            
            public_numbers = rsa.RSAPublicNumbers(e, n)
            public_key = public_numbers.public_key(default_backend())
            
            return public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        except Exception as e:
            raise ValueError(f"Failed to convert JWK to PEM: {e}")


class OIDCFactory:
    """Factory for creating OIDC providers from environment variables."""
    
    @staticmethod
    def create_okta() -> OIDCProvider:
        """Create Okta OIDC provider."""
        domain = os.getenv("OKTA_DOMAIN")
        client_id = os.getenv("OKTA_CLIENT_ID")
        client_secret = os.getenv("OKTA_CLIENT_SECRET")
        
        if not all([domain, client_id, client_secret]):
            raise ValueError("Missing Okta configuration (OKTA_DOMAIN, OKTA_CLIENT_ID, OKTA_CLIENT_SECRET)")
        
        discovery_url = f"https://{domain}/.well-known/openid-configuration"
        
        return OIDCProvider(
            client_id=client_id,
            client_secret=client_secret,
            discovery_url=discovery_url,
        )
    
    @staticmethod
    def create_azure_ad() -> OIDCProvider:
        """Create Azure AD (Entra ID) OIDC provider."""
        tenant_id = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        client_secret = os.getenv("AZURE_CLIENT_SECRET")
        
        if not all([tenant_id, client_id, client_secret]):
            raise ValueError("Missing Azure AD configuration")
        
        discovery_url = (
            f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
        )
        
        return OIDCProvider(
            client_id=client_id,
            client_secret=client_secret,
            discovery_url=discovery_url,
        )
    
    @staticmethod
    def create_google() -> OIDCProvider:
        """Create Google Identity OIDC provider."""
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not all([client_id, client_secret]):
            raise ValueError("Missing Google configuration")
        
        discovery_url = "https://accounts.google.com/.well-known/openid-configuration"
        
        return OIDCProvider(
            client_id=client_id,
            client_secret=client_secret,
            discovery_url=discovery_url,
        )
    
    @staticmethod
    def create_from_env() -> Optional[OIDCProvider]:
        """Create OIDC provider based on OIDC_PROVIDER environment variable."""
        provider_type = os.getenv("OIDC_PROVIDER")
        
        if not provider_type:
            return None
        
        if provider_type.lower() == "okta":
            return OIDCFactory.create_okta()
        elif provider_type.lower() == "azure":
            return OIDCFactory.create_azure_ad()
        elif provider_type.lower() == "google":
            return OIDCFactory.create_google()
        else:
            # Custom provider
            discovery_url = os.getenv("OIDC_DISCOVERY_URL")
            client_id = os.getenv("OIDC_CLIENT_ID")
            client_secret = os.getenv("OIDC_CLIENT_SECRET")
            
            if not all([discovery_url, client_id, client_secret]):
                raise ValueError("Missing OIDC configuration for custom provider")
            
            return OIDCProvider(
                client_id=client_id,
                client_secret=client_secret,
                discovery_url=discovery_url,
            )
