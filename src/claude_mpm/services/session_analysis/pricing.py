"""
Rack-rate pricing table and cost computation for Anthropic Claude models.

WHAT: Resolve per-model token rates and compute USD cost from a usage dict.
WHY:  A single authoritative pricing table used by the session analyzer so
      cost estimates are consistent, easily auditable, and only need updating
      in one place when Anthropic changes list prices.

References
----------
LINK: none  (new subsystem — spec backfill pending)

Source: https://www.anthropic.com/pricing  (retrieved 2025-06-10)
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Rate table — USD per 1 000 000 tokens
# Source: https://www.anthropic.com/pricing  (retrieved 2025-06-10)
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

# Default fallback when no prefix matches — use sonnet rates and flag it.
_FALLBACK_RATES = Rates(
    input=3.00,
    output=15.00,
    cache_write=3.75,
    cache_read=0.30,
    model_family="unknown",
    is_fallback=True,
)


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
    for prefix, rates in _RATE_TABLE:
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
