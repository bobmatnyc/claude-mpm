"""Models router.

Endpoints:
    GET /models         — list available models
    GET /models/current — current model from settings
    PUT /models/current — update current model in settings
"""

import json
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/models", tags=["Models"])

# Known Anthropic models used as fallback when API is unavailable
_KNOWN_MODELS = [
    {"id": "claude-opus-4-5", "name": "Claude Opus 4.5", "context_window": 200000},
    {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5", "context_window": 200000},
    {"id": "claude-haiku-3-5", "name": "Claude Haiku 3.5", "context_window": 200000},
    {"id": "claude-opus-4-0", "name": "Claude Opus 4", "context_window": 200000},
    {"id": "claude-sonnet-4-0", "name": "Claude Sonnet 4", "context_window": 200000},
    {
        "id": "claude-3-5-sonnet-20241022",
        "name": "Claude 3.5 Sonnet",
        "context_window": 200000,
    },
    {
        "id": "claude-3-5-haiku-20241022",
        "name": "Claude 3.5 Haiku",
        "context_window": 200000,
    },
    {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "context_window": 200000},
]

_USER_SETTINGS = Path.home() / ".claude" / "settings.json"


class ModelUpdate(BaseModel):
    """Request body for updating the current model.

    Attributes:
        model: New model ID to set as default.
    """

    model_config = ConfigDict(from_attributes=True)

    model: str


def _read_user_settings() -> dict:
    """Read ~/.claude/settings.json, returning {} on any failure."""
    try:
        return json.loads(_USER_SETTINGS.read_text())
    except Exception:
        return {}


def _write_user_settings(data: dict) -> None:
    """Write data to ~/.claude/settings.json, creating directories as needed."""
    _USER_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    _USER_SETTINGS.write_text(json.dumps(data, indent=2))


@router.get("", summary="List available Claude models")
async def list_models(request: Request):
    """Return a list of available Claude models.

    Attempts to fetch the live model list from the Anthropic API when
    ANTHROPIC_API_KEY is configured; falls back to a known static list.
    """
    api_key = request.app.state.config.anthropic_api_key
    if api_key:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass  # fall through to known list

    return {"data": _KNOWN_MODELS, "source": "fallback"}


@router.get("/current", summary="Get current default model")
async def get_current_model():
    """Return the model currently set in ~/.claude/settings.json."""
    settings = _read_user_settings()
    model = settings.get("model", "claude-opus-4-5")
    return {"model": model}


@router.put("/current", summary="Update the default model")
async def set_current_model(body: ModelUpdate):
    """Write the chosen model to ~/.claude/settings.json."""
    settings = _read_user_settings()
    settings["model"] = body.model
    _write_user_settings(settings)
    return {"model": body.model, "updated": True}
