"""
Rack-rate pricing table and cost computation for Anthropic Claude models.

WHAT: Resolve per-model token rates and compute USD cost from a usage dict.
WHY:  A single authoritative pricing table used by the session analyzer so
      cost estimates are consistent, easily auditable, and only need updating
      in one place when Anthropic changes list prices.

References
----------
LINK: none  (new subsystem -- spec backfill pending)

Source: https://www.anthropic.com/pricing  (retrieved 2026-06-10)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Pricing retrieval date -- update whenever the hardcoded table is refreshed.
# ---------------------------------------------------------------------------

PRICING_RETRIEVED_DATE: str = "2026-06-10"  # Rates retrieved 2026-06-10 (current date); update when Anthropic pricing changes.

# ---------------------------------------------------------------------------
# Rate table -- USD per 1 000 000 tokens
# Source: https://www.anthropic.com/pricing  (retrieved 2026-06-10)
# Update the table here (and only here) when Anthropic changes list prices.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rates:
    """Per-model token rates in USD per 1 000 000 tokens."""

    input: float
    output: float
    cache_write: float  # 5-minute prompt-cache write
    cache_read: float
    model_family: str = field(default="", compare=False)
    is_fallback: bool = field(default=False, compare=False)


# Ordered list of (prefix, Rates).  First prefix-match wins (case-insensitive).
_RATE_TABLE: list[tuple[str, Rates]] = [
    (
        "claude-opus",
        Rates(
            input=15.00,
            output=75.00,
            cache_write=18.75,
            cache_read=1.50,
            model_family="opus",
        ),
    ),
    (
        "claude-sonnet",
        Rates(
            input=3.00,
            output=15.00,
            cache_write=3.75,
            cache_read=0.30,
            model_family="sonnet",
        ),
    ),
    (
        "claude-haiku",
        Rates(
            input=0.80,
            output=4.00,
            cache_write=1.00,
            cache_read=0.08,
            model_family="haiku",
        ),
    ),
]

# Default fallback when no prefix matches -- use sonnet rates and flag it.
_FALLBACK_RATES = Rates(
    input=3.00,
    output=15.00,
    cache_write=3.75,
    cache_read=0.30,
    model_family="unknown",
    is_fallback=True,
)


def _load_rate_table_from_file(path: Path) -> list[tuple[str, Rates]]:
    """Load a rate table from a JSON file.

    WHAT: Parses a JSON array of {prefix, input, output, cache_write,
          cache_read, model_family} objects and returns a list of
          (prefix, Rates) tuples in the same order.
    WHY:  Allows operators to supply an up-to-date pricing file via the
          CLAUDE_MPM_PRICING_FILE env var without modifying source code.

    Parameters
    ----------
    path:
        Absolute or relative path to the JSON pricing file.

    Returns
    -------
    list[tuple[str, Rates]]
        Parsed rate table, same shape as _RATE_TABLE.

    Raises
    ------
    ValueError
        If the file cannot be parsed or is missing required keys.
    """
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, list):
        raise ValueError(f"Pricing file must contain a JSON array, got {type(raw)}")
    table: list[tuple[str, Rates]] = []
    for entry in raw:
        prefix = entry["prefix"]
        table.append(
            (
                prefix,
                Rates(
                    input=float(entry["input"]),
                    output=float(entry["output"]),
                    cache_write=float(entry["cache_write"]),
                    cache_read=float(entry["cache_read"]),
                    model_family=str(entry.get("model_family", "")),
                ),
            )
        )
    return table


# Module-level cache: (env_value, table).  The env var is stable within a
# process, so we re-load only when it changes (handles monkeypatching in tests).
_rate_table_cache: tuple[str, list[tuple[str, Rates]]] | None = None


def _active_rate_table() -> list[tuple[str, Rates]]:
    """Return the rate table, preferring CLAUDE_MPM_PRICING_FILE if set.

    Results are cached by env-var value so repeated per-turn calls do not
    re-stat the filesystem on every invocation.
    """
    global _rate_table_cache
    pricing_file = os.environ.get("CLAUDE_MPM_PRICING_FILE", "").strip()
    if _rate_table_cache is not None and _rate_table_cache[0] == pricing_file:
        return _rate_table_cache[1]
    if pricing_file:
        p = Path(pricing_file)
        if p.is_file():
            table = _load_rate_table_from_file(p)
            _rate_table_cache = (pricing_file, table)
            return table
    _rate_table_cache = (pricing_file, _RATE_TABLE)
    return _RATE_TABLE


def resolve_model_rates(model: str) -> Rates:
    """Return the Rates for *model*, falling back to sonnet if unknown.

    WHAT: Case-insensitive prefix match against the rate table; returns a
          Rates with is_fallback=True when no prefix matches so callers can
          surface a warning.
    WHY:  Keeps all pricing logic in one place and makes unknown-model
          handling explicit rather than silently wrong.

    Parameters
    ----------
    model:
        Model identifier string, e.g. ``"claude-sonnet-4-6"``.

    Returns
    -------
    Rates
        Matched or fallback rate object.
    """
    model_lower = model.lower().strip()
    for prefix, rates in _active_rate_table():
        if model_lower.startswith(prefix):
            return rates
    return _FALLBACK_RATES


def compute_cost(model: str, usage: dict[str, int]) -> float:
    """Compute USD cost from a Claude usage dict.

    WHAT: Multiplies each token count by the appropriate per-million rate and
          sums to a total USD float.
    WHY:  Encapsulates the cost formula so tests and callers never duplicate it.

    Parameters
    ----------
    model:
        Model identifier string.
    usage:
        Dict with keys ``input_tokens``, ``output_tokens``,
        ``cache_creation_input_tokens``, ``cache_read_input_tokens``
        (all optional; absent keys are treated as 0).

    Returns
    -------
    float
        Estimated USD cost (may be 0.0 for empty usage).
    """
    rates = resolve_model_rates(model)
    per_m = 1_000_000.0

    input_tok = usage.get("input_tokens", 0) or 0
    output_tok = usage.get("output_tokens", 0) or 0
    cache_write_tok = usage.get("cache_creation_input_tokens", 0) or 0
    cache_read_tok = usage.get("cache_read_input_tokens", 0) or 0

    return (
        input_tok * rates.input
        + output_tok * rates.output
        + cache_write_tok * rates.cache_write
        + cache_read_tok * rates.cache_read
    ) / per_m
