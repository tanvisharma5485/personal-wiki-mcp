import os

import jwt
from jwt import PyJWKClient

from mcp.server.auth.provider import AccessToken, TokenVerifier


class Auth0TokenVerifier(TokenVerifier):
    def __init__(self):
        self.domain = os.environ["AUTH0_DOMAIN"].rstrip("/")
        self.audience = os.environ["AUTH0_AUDIENCE"]

        self.issuer = f"{self.domain}/"
        self.jwks_url = f"{self.domain}/.well-known/jwks.json"

        self.jwks_client = PyJWKClient(self.jwks_url)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
            )

            scope_string = payload.get("scope", "")
            scopes = scope_string.split() if scope_string else []

            client_id = (
                payload.get("azp")
                or payload.get("client_id")
                or "unknown"
            )

            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=scopes,
                expires_at=payload.get("exp"),
                resource=self.audience,
                subject=payload.get("sub"),
                claims=payload,
            )

        except Exception as exc:
            print(f"Auth0 token verification failed: {exc}")
            return None
