import os
import secrets
import time

from pydantic import AnyHttpUrl

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
)
from mcp.server.fastmcp import FastMCP
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthToken,
)


PORT = int(os.getenv("PORT", "8002"))

BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    f"http://127.0.0.1:{PORT}",
).rstrip("/")

MCP_URL = f"{BASE_URL}/mcp"


class LocalOAuthProvider(
    OAuthAuthorizationServerProvider[
        AuthorizationCode,
        RefreshToken,
        AccessToken,
    ]
):
    def __init__(self):
        self.clients = {}
        self.codes = {}
        self.access_tokens = {}
        self.refresh_tokens = {}

    async def get_client(
        self,
        client_id: str,
    ) -> OAuthClientInformationFull | None:
        return self.clients.get(client_id)

    async def register_client(
        self,
        client_info: OAuthClientInformationFull,
    ) -> None:
        self.clients[
            client_info.client_id
        ] = client_info

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        code_value = secrets.token_urlsafe(32)

        code = AuthorizationCode(
            code=code_value,
            scopes=params.scopes or ["wiki:read"],
            expires_at=time.time() + 300,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=(
                params.redirect_uri_provided_explicitly
            ),
            resource=params.resource,
            subject="oauth-test-user",
        )

        self.codes[code_value] = code

        return construct_redirect_uri(
            str(params.redirect_uri),
            code=code_value,
            state=params.state,
        )

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        code = self.codes.get(
            authorization_code
        )

        if code is None:
            return None

        if code.client_id != client.client_id:
            return None

        if code.expires_at < time.time():
            return None

        return code

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        access_value = secrets.token_urlsafe(32)
        refresh_value = secrets.token_urlsafe(32)

        access_token = AccessToken(
            token=access_value,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(
                time.time() + 3600
            ),
            resource=authorization_code.resource,
            subject="oauth-test-user",
        )

        refresh_token = RefreshToken(
            token=refresh_value,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=int(
                time.time() + 86400
            ),
            subject="oauth-test-user",
        )

        self.access_tokens[
            access_value
        ] = access_token

        self.refresh_tokens[
            refresh_value
        ] = refresh_token

        self.codes.pop(
            authorization_code.code,
            None,
        )

        return OAuthToken(
            access_token=access_value,
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(
                authorization_code.scopes
            ),
            refresh_token=refresh_value,
        )

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        token = self.refresh_tokens.get(
            refresh_token
        )

        if token is None:
            return None

        if token.client_id != client.client_id:
            return None

        if (
            token.expires_at is not None
            and token.expires_at < time.time()
        ):
            return None

        return token

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        new_access_value = (
            secrets.token_urlsafe(32)
        )

        requested_scopes = (
            scopes
            if scopes
            else refresh_token.scopes
        )

        access_token = AccessToken(
            token=new_access_value,
            client_id=client.client_id,
            scopes=requested_scopes,
            expires_at=int(
                time.time() + 3600
            ),
            subject=refresh_token.subject,
        )

        self.access_tokens[
            new_access_value
        ] = access_token

        return OAuthToken(
            access_token=new_access_value,
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(
                requested_scopes
            ),
            refresh_token=refresh_token.token,
        )

    async def load_access_token(
        self,
        token: str,
    ) -> AccessToken | None:
        access_token = (
            self.access_tokens.get(token)
        )

        if access_token is None:
            return None

        if (
            access_token.expires_at is not None
            and access_token.expires_at
            < time.time()
        ):
            return None

        return access_token

    async def revoke_token(
        self,
        token: AccessToken | RefreshToken,
    ) -> None:
        self.access_tokens.pop(
            token.token,
            None,
        )

        self.refresh_tokens.pop(
            token.token,
            None,
        )


provider = LocalOAuthProvider()


auth_settings = AuthSettings(
    issuer_url=AnyHttpUrl(
        BASE_URL
    ),
    resource_server_url=AnyHttpUrl(
        MCP_URL
    ),
    required_scopes=[
        "wiki:read",
    ],
    client_registration_options=(
        ClientRegistrationOptions(
            enabled=True,
            valid_scopes=[
                "wiki:read",
            ],
            default_scopes=[
                "wiki:read",
            ],
        )
    ),
)


mcp = FastMCP(
    "personal-wiki-oauth-test",
    auth_server_provider=provider,
    auth=auth_settings,
)


@mcp.tool()
def oauth_test() -> dict:
    return {
        "authenticated": True,
        "message": (
            "Claude successfully authenticated "
            "with the OAuth MCP test server."
        ),
    }


if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = PORT

    mcp.run(
        transport="streamable-http"
    )