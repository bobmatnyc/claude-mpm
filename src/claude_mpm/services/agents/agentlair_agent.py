"""AgentLair async messaging integration for Claude MPM.

Provides a persistent, cross-machine async inbox for Claude MPM instances via
the AgentLair REST API (https://agentlair.dev).  Unlike the SQLite-backed
``MessageService`` (which is local-filesystem-only), AgentLair messages work
across machines, networks, and sessions.

Each MPM instance claims an ``@agentlair.dev`` address and can send or receive
messages from any other MPM instance worldwide — no shared filesystem needed.

Usage::

    from claude_mpm.services.agents.agentlair_agent import (
        is_agentlair_available,
        claim_inbox,
        send_message,
        receive_messages,
        AgentLairMessage,
    )

    # Check whether AGENTLAIR_API_KEY is configured
    if is_agentlair_available():
        # Claim a persistent inbox for this MPM instance
        await claim_inbox("myproject@agentlair.dev")

        # Send a message to another MPM instance
        result = await send_message(
            from_address="myproject@agentlair.dev",
            to_address="otherproject@agentlair.dev",
            subject="Task delegation request",
            body="Please summarise the recent git log for /repo/foo",
        )

        # Poll for incoming messages
        messages = await receive_messages("myproject@agentlair.dev")
        for msg in messages:
            print(f"From: {msg.from_address}  Subject: {msg.subject}")
            print(msg.body)

Configuration::

    Set ``AGENTLAIR_API_KEY`` in the environment (or export it from
    ``~/.claude-mpm/.env``).  A free key is available at https://agentlair.dev.
    If the variable is absent the module degrades gracefully — all functions
    return error results instead of raising exceptions.

API reference:
    https://agentlair.dev (GET / returns full machine-readable API manifest)
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE_URL = "https://agentlair.dev/v1"

# ---------------------------------------------------------------------------
# Module-level availability cache
# ---------------------------------------------------------------------------

_agentlair_available: bool | None = None  # None = not yet checked


def is_agentlair_available() -> bool:
    """Return True when ``AGENTLAIR_API_KEY`` is present in the environment.

    The result is cached after the first call so repeated checks are free.
    The key is not validated against the remote API at check time; the first
    real API call will surface an authentication error if the key is invalid.

    Returns:
        True when the environment variable is set to a non-empty string.
    """
    global _agentlair_available
    if _agentlair_available is not None:
        return _agentlair_available

    api_key = os.environ.get("AGENTLAIR_API_KEY", "").strip()
    _agentlair_available = bool(api_key)

    if _agentlair_available:
        logger.debug("AgentLair API key found; async messaging available")
    else:
        logger.debug("AGENTLAIR_API_KEY not set; AgentLair messaging unavailable")

    return _agentlair_available


def _get_api_key() -> str:
    """Return the API key from the environment."""
    return os.environ.get("AGENTLAIR_API_KEY", "").strip()


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Result / message dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AgentLairResult:
    """Outcome of an AgentLair API call.

    Attributes:
        success: True when the API call completed without error.
        data: Parsed JSON response body (dict or list).
        error: Human-readable error description when ``success`` is False.
        duration_ms: Wall-clock milliseconds for the HTTP round-trip.
        status_code: HTTP status code returned by the server (0 if no response).
    """

    success: bool
    data: dict[str, Any] | list[Any]
    error: str = ""
    duration_ms: int = 0
    status_code: int = 0


@dataclass
class AgentLairMessage:
    """A single message retrieved from an AgentLair inbox.

    Attributes:
        message_id: Unique message identifier (RFC 2822 Message-ID, may include
            angle brackets — use :func:`strip_message_id` for URL encoding).
        from_address: Sender email address.
        subject: Message subject line.
        body: Plain-text message body (empty when not yet fetched).
        received_at: ISO-8601 timestamp when the message arrived.
        read: Whether the message has been marked as read.
        raw: The raw API response dict for this message.
    """

    message_id: str
    from_address: str
    subject: str
    body: str = ""
    received_at: str = ""
    read: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def strip_message_id(message_id: str) -> str:
        """Strip RFC 2822 angle brackets from a message ID for URL use."""
        return message_id.lstrip("<").rstrip(">")


# ---------------------------------------------------------------------------
# Low-level HTTP helper
# ---------------------------------------------------------------------------


async def _request(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    params: dict[str, str] | None = None,
    timeout: int = 30,
) -> AgentLairResult:
    """Perform an authenticated HTTP request against the AgentLair API.

    Imports ``httpx`` lazily so that environments without httpx installed do not
    crash on import — they will receive a clear error on the first real call.

    Args:
        method: HTTP verb (``"GET"``, ``"POST"``, etc.).
        path: API path (e.g. ``"/email/claim"``).
        json: Optional request body, serialised as JSON.
        params: Optional query-string parameters.
        timeout: Request timeout in seconds.

    Returns:
        An :class:`AgentLairResult` with ``success=True`` and ``data`` populated
        on HTTP 2xx, or ``success=False`` with ``error`` set on failure.
    """
    try:
        import httpx
    except ImportError:
        return AgentLairResult(
            success=False,
            data={},
            error=(
                "httpx is not installed.  "
                "Run `pip install httpx` or `uv add httpx` to enable AgentLair messaging."
            ),
        )

    url = f"{_BASE_URL}{path}"
    start_ms = int(time.monotonic() * 1000)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=_auth_headers(),
                json=json,
                params=params,
                timeout=timeout,
            )
    except httpx.TimeoutException as exc:
        elapsed = int(time.monotonic() * 1000) - start_ms
        logger.warning("AgentLair request timed out: %s", exc)
        return AgentLairResult(
            success=False,
            data={},
            error=f"Request timed out after {timeout}s: {exc}",
            duration_ms=elapsed,
        )
    except httpx.RequestError as exc:
        elapsed = int(time.monotonic() * 1000) - start_ms
        logger.error("AgentLair request error: %s", exc)
        return AgentLairResult(
            success=False,
            data={},
            error=f"HTTP request failed: {exc}",
            duration_ms=elapsed,
        )

    elapsed = int(time.monotonic() * 1000) - start_ms

    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}

    if response.is_success:
        return AgentLairResult(
            success=True,
            data=data,
            duration_ms=elapsed,
            status_code=response.status_code,
        )

    error_msg = (
        data.get("error", data.get("message", response.text))
        if isinstance(data, dict)
        else str(data)
    )
    logger.warning(
        "AgentLair API error %d: %s", response.status_code, error_msg
    )
    return AgentLairResult(
        success=False,
        data=data,
        error=f"API error {response.status_code}: {error_msg}",
        duration_ms=elapsed,
        status_code=response.status_code,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def claim_inbox(address: str) -> AgentLairResult:
    """Claim an ``@agentlair.dev`` inbox for this MPM instance.

    Idempotent — calling this repeatedly with the same address is safe.  The
    address must end with ``@agentlair.dev``.

    Args:
        address: The desired inbox address, e.g. ``"myproject@agentlair.dev"``.

    Returns:
        An :class:`AgentLairResult`.  On success ``data`` contains
        ``{"claimed": true, "address": "..."}`` (or ``{"already_owned": true}``
        if the inbox was previously claimed by this account).
    """
    if not is_agentlair_available():
        return AgentLairResult(
            success=False,
            data={},
            error="AGENTLAIR_API_KEY is not set.",
        )

    logger.debug("Claiming AgentLair inbox: %s", address)
    result = await _request("POST", "/email/claim", json={"address": address})

    if result.success:
        logger.info("AgentLair inbox ready: %s", address)
    return result


async def send_message(
    *,
    from_address: str,
    to_address: str,
    subject: str,
    body: str,
    html: str | None = None,
) -> AgentLairResult:
    """Send a message from one MPM instance to another via AgentLair.

    The ``from_address`` must have been previously claimed with
    :func:`claim_inbox`.  The ``to_address`` can be any email address —
    both ``@agentlair.dev`` inboxes and external addresses are supported.

    Args:
        from_address: Sender ``@agentlair.dev`` address.
        to_address: Recipient address (``@agentlair.dev`` or external).
        subject: Message subject.
        body: Plain-text message body.
        html: Optional HTML version of the body.

    Returns:
        An :class:`AgentLairResult`.  On success ``data`` contains
        ``{"id": "out_...", "status": "sent", ...}``.
    """
    if not is_agentlair_available():
        return AgentLairResult(
            success=False,
            data={},
            error="AGENTLAIR_API_KEY is not set.",
        )

    payload: dict[str, Any] = {
        "from": from_address,
        "to": [to_address],
        "subject": subject,
        "text": body,
    }
    if html:
        payload["html"] = html

    logger.debug(
        "Sending AgentLair message: %s -> %s [%s]", from_address, to_address, subject
    )
    result = await _request("POST", "/email/send", json=payload)

    if result.success:
        msg_id = result.data.get("id", "") if isinstance(result.data, dict) else ""
        logger.info("Message sent via AgentLair: %s", msg_id)
    return result


async def receive_messages(
    address: str,
    *,
    limit: int = 20,
    unread_only: bool = False,
) -> list[AgentLairMessage]:
    """Retrieve messages from an AgentLair inbox.

    Args:
        address: The ``@agentlair.dev`` inbox address to check.
        limit: Maximum number of messages to return (default 20).
        unread_only: When True, only return unread messages.

    Returns:
        A list of :class:`AgentLairMessage` objects.  Returns an empty list
        when the inbox is empty or the API call fails.
    """
    if not is_agentlair_available():
        logger.warning("AGENTLAIR_API_KEY not set; cannot receive messages")
        return []

    params: dict[str, str] = {
        "address": address,
        "limit": str(limit),
    }

    result = await _request("GET", "/email/inbox", params=params)
    if not result.success:
        logger.warning("Failed to fetch AgentLair inbox %s: %s", address, result.error)
        return []

    raw_messages = (
        result.data.get("messages", []) if isinstance(result.data, dict) else []
    )

    messages: list[AgentLairMessage] = []
    for raw in raw_messages:
        if not isinstance(raw, dict):
            continue
        msg = AgentLairMessage(
            message_id=raw.get("message_id", ""),
            from_address=raw.get("from", ""),
            subject=raw.get("subject", ""),
            received_at=raw.get("received_at", ""),
            read=raw.get("read", False),
            raw=raw,
        )
        if unread_only and msg.read:
            continue
        messages.append(msg)

    logger.debug(
        "AgentLair inbox %s: %d message(s) retrieved", address, len(messages)
    )
    return messages


async def read_message(address: str, message_id: str) -> AgentLairResult:
    """Fetch the full body of a specific message.

    Args:
        address: The inbox address that owns the message.
        message_id: The message ID as returned by :func:`receive_messages`
            (angle brackets are stripped automatically).

    Returns:
        An :class:`AgentLairResult`.  On success ``data`` contains the full
        message dict including ``"text"`` and ``"html"`` body fields.
    """
    if not is_agentlair_available():
        return AgentLairResult(
            success=False,
            data={},
            error="AGENTLAIR_API_KEY is not set.",
        )

    import urllib.parse

    clean_id = AgentLairMessage.strip_message_id(message_id)
    encoded_id = urllib.parse.quote(clean_id, safe="")
    params = {"address": address}

    return await _request("GET", f"/email/messages/{encoded_id}", params=params)
