"""Shared response models for the UI Service API."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class SuccessResponse(BaseModel):
    """Generic success response envelope.

    Attributes:
        success: Always True for success responses.
        message: Human-readable success message.
        data: Optional payload data.
    """

    model_config = ConfigDict(from_attributes=True)

    success: bool = True
    message: str = "OK"
    data: Any | None = None


class ErrorResponse(BaseModel):
    """Generic error response envelope.

    Attributes:
        success: Always False for error responses.
        error: Machine-readable error code.
        message: Human-readable error description.
        detail: Optional additional detail.
    """

    model_config = ConfigDict(from_attributes=True)

    success: bool = False
    error: str
    message: str
    detail: Any | None = None
