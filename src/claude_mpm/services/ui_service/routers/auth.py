"""Authentication router.

Endpoints:
    GET  /auth/status  — check current auth state
    POST /auth/login   — set API key or initiate OAuth
    POST /auth/logout  — clear credentials
"""

import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    """Request body for login.

    Attributes:
        method: Authentication method ('api_key' or 'oauth').
        api_key: Anthropic API key (for api_key method).
    """

    model_config = ConfigDict(from_attributes=True)

    method: str = "api_key"
    api_key: str | None = None


@router.get("/status", summary="Get authentication status")
async def auth_status(request: Request):
    """Return the current authentication state.

    Checks for ANTHROPIC_API_KEY in the environment and the app config.
    """
    api_key = request.app.state.config.anthropic_api_key or os.environ.get(
        "ANTHROPIC_API_KEY"
    )

    if api_key:
        # Mask all but the last 4 characters
        masked = "*" * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else "****"
        return {
            "authenticated": True,
            "method": "api_key",
            "account": masked,
            "provider": "anthropic",
        }

    return {
        "authenticated": False,
        "method": None,
        "account": None,
        "provider": None,
    }


@router.post("/login", summary="Login with API key or OAuth")
async def login(request: Request, body: LoginRequest):
    """Set credentials for the current process.

    For ``api_key`` method: stores the key in process environment.
    For ``oauth`` method: returns the Anthropic OAuth redirect URL (stub).
    """
    if body.method == "api_key":
        if not body.api_key:
            raise HTTPException(
                status_code=400, detail="api_key required for api_key method"
            )
        os.environ["ANTHROPIC_API_KEY"] = body.api_key
        request.app.state.config.anthropic_api_key = body.api_key
        return {"authenticated": True, "method": "api_key"}

    if body.method == "oauth":
        # OAuth flow stub — real implementation would initiate PKCE flow
        return {
            "authenticated": False,
            "method": "oauth",
            "redirect_url": "https://console.anthropic.com/oauth/authorize",
            "message": "OAuth flow not yet implemented; use api_key method",
        }

    raise HTTPException(status_code=400, detail=f"Unknown login method: {body.method}")


@router.post("/logout", summary="Log out and clear credentials")
async def logout(request: Request):
    """Clear stored credentials from the process environment."""
    os.environ.pop("ANTHROPIC_API_KEY", None)
    request.app.state.config.anthropic_api_key = None
    return {"authenticated": False, "message": "Logged out"}
