"""Cursor-based pagination utilities for config API endpoints.

Provides a generic pagination helper that can be applied to any list of items.
Backward compatible: if no limit/cursor params are provided, all items are returned.

Query param convention:
    ?limit=50&cursor=<opaque_base64>&sort=asc|desc

The cursor is a base64-encoded offset index for simplicity and stability.
"""

import base64
import logging
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)

MAX_LIMIT = 100
DEFAULT_LIMIT = 50


@dataclass
class PaginatedResponse:
    """Container for paginated results."""

    items: List[Any]
    total: int
    has_more: bool
    next_cursor: Optional[str]
    limit: Optional[int]


def _encode_cursor(offset: int) -> str:
    """Encode an offset into an opaque cursor string."""
    return base64.urlsafe_b64encode(f"offset:{offset}".encode()).decode()


def _decode_cursor(cursor: str) -> int:
    """Decode an opaque cursor string back into an offset.

    Returns 0 if the cursor is invalid.
    """
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        if decoded.startswith("offset:"):
            return int(decoded[7:])
    except Exception:
        logger.warning(f"Invalid cursor: {cursor}")
    return 0


def paginate(
    items: List[Any],
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    sort_key: Optional[Callable] = None,
    sort_desc: bool = False,
) -> PaginatedResponse:
    """Apply cursor-based pagination to a list of items.

    Backward compatible: if limit and cursor are both None, returns ALL items.

    Args:
        items: Full list of items to paginate.
        limit: Max items to return. Clamped to MAX_LIMIT. None = return all.
        cursor: Opaque cursor from a previous response.
        sort_key: Optional callable for sorting (e.g., lambda x: x["name"]).
        sort_desc: If True, sort descending.

    Returns:
        PaginatedResponse with sliced items and navigation metadata.
    """
    # Sort if requested
    if sort_key is not None:
        items = sorted(items, key=sort_key, reverse=sort_desc)

    total = len(items)

    # Backward compatible: no pagination params = return all
    if limit is None and cursor is None:
        return PaginatedResponse(
            items=items,
            total=total,
            has_more=False,
            next_cursor=None,
            limit=None,
        )

    # Apply defaults and clamp
    effective_limit = min(limit or DEFAULT_LIMIT, MAX_LIMIT)
    offset = _decode_cursor(cursor) if cursor else 0

    # Fetch N+1 to determine has_more
    end = offset + effective_limit
    page_items = items[offset : end + 1]

    has_more = len(page_items) > effective_limit
    if has_more:
        page_items = page_items[:effective_limit]

    next_cursor = _encode_cursor(end) if has_more else None

    return PaginatedResponse(
        items=page_items,
        total=total,
        has_more=has_more,
        next_cursor=next_cursor,
        limit=effective_limit,
    )


def extract_pagination_params(request) -> dict:
    """Extract pagination query params from an aiohttp request.

    Args:
        request: aiohttp web.Request object.

    Returns:
        Dict with 'limit', 'cursor', 'sort_desc' keys.
    """
    limit_str = request.query.get("limit", None)
    cursor = request.query.get("cursor", None)
    sort = request.query.get("sort", "asc")

    limit = None
    if limit_str is not None:
        try:
            limit = int(limit_str)
        except ValueError:
            limit = None

    return {
        "limit": limit,
        "cursor": cursor,
        "sort_desc": sort.lower() == "desc",
    }


def paginated_json(paginated: PaginatedResponse, items_key: str = "items") -> dict:
    """Convert a PaginatedResponse into a JSON-serializable dict.

    Args:
        paginated: PaginatedResponse to convert.
        items_key: Key name for the items list (e.g., "agents", "skills").

    Returns:
        Dict ready for web.json_response.
    """
    result = {
        "success": True,
        items_key: paginated.items,
        "total": paginated.total,
    }

    # Only include pagination metadata when pagination is active
    if paginated.limit is not None:
        result["pagination"] = {
            "has_more": paginated.has_more,
            "next_cursor": paginated.next_cursor,
            "limit": paginated.limit,
        }

    return result
