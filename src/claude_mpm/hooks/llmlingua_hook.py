"""PostToolUse hook: compress Bash tool output with LLMLingua-2 (experimental).

LLMLingua-2 (https://github.com/microsoft/LLMLingua) is Microsoft's semantic
prompt compression model. Unlike ztk — which rewrites Bash *commands* via
PreToolUse to strip noise before output is generated — LLMLingua operates on
already-generated *text*. The natural integration point is therefore
PostToolUse, where we can intercept Bash output after execution and compress
it before it flows back to Claude.

Architectural note
------------------
This is an opt-in **experiment** that runs alongside the existing ZTK hook
(it does NOT modify ZTK behavior). Whether Claude Code's PostToolUse contract
ultimately exposes a mechanism to rewrite the tool_result content reaching
Claude is still evolving; the primary deliverable here is the measurement
infrastructure (savings log + CLI summary) so we can evaluate LLMLingua-2's
real-world compression ratio and latency before committing to a deeper
integration. If/when the hook contract supports output rewriting, this hook
already produces the rewritten payload.

Behavior
--------
- Opt-in only: ``CLAUDE_MPM_USE_LLMLINGUA=1`` must be set; otherwise pass-through.
- Lazy import of ``llmlingua`` so the dependency stays optional.
- Singleton ``PromptCompressor`` cached across invocations (~2-3s cold start
  is paid once per process).
- Only acts on ``Bash`` tool calls.
- Skips outputs <200 chars (compression overhead not worth it).
- Target compression ratio 0.5 (50% token reduction — conservative for quality).
- Model: ``microsoft/llmlingua-2-xlm-roberta-large-meetingbank`` (balanced
  size/quality, runs on CPU).
- Metrics: tab-separated rows in ``~/.claude-mpm/llmlingua-savings.log``
  formatted as
  ``timestamp\\tcmd_name\\toriginal_tokens\\tcompressed_tokens\\tsavings_pct\\tlatency_ms``.
- Token counting: ``len(text.split()) * 1.3`` heuristic (same approach used
  by the ZTK stats command for whitespace-tokenized text).
- Fallback: any failure (missing dep, model load error, compression error)
  returns pass-through unchanged. Experiment must never break the session.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Opt-in flag and configuration
# ---------------------------------------------------------------------------
_ENABLE_ENV_VAR = "CLAUDE_MPM_USE_LLMLINGUA"
_MODEL_NAME = "microsoft/llmlingua-2-xlm-roberta-large-meetingbank"
_TARGET_RATIO = 0.5  # keep 50% of tokens
_MIN_OUTPUT_CHARS = 200  # below this, skip compression entirely

_MPM_LOG_DIR = Path.home() / ".claude-mpm"
_MPM_LLMLINGUA_LOG = _MPM_LOG_DIR / "llmlingua-savings.log"

# Cached singleton compressor (module-level so re-imports reuse it).
_compressor_instance: Any | None = None
_compressor_failed: bool = False  # avoid retrying after a hard failure


def _log_debug(message: str) -> None:
    """Write a debug line to stderr when CLAUDE_MPM_LLMLINGUA_DEBUG=1."""
    if os.environ.get("CLAUDE_MPM_LLMLINGUA_DEBUG") == "1":
        print(f"[llmlingua-hook] {message}", file=sys.stderr, flush=True)


def _is_enabled() -> bool:
    """Return True iff the opt-in env var is set to a truthy value."""
    return os.environ.get(_ENABLE_ENV_VAR, "").lower() in ("1", "true", "yes")


def _estimate_tokens(text: str) -> int:
    """Approximate token count using whitespace * 1.3 heuristic.

    Matches the heuristic used elsewhere in claude-mpm stats so that
    comparisons against ZTK numbers are apples-to-apples. Real tokenization
    would require pulling in tiktoken/transformers tokenizer, which is too
    heavy for this measurement layer.
    """
    return int(len(text.split()) * 1.3)


def _get_compressor() -> Any | None:
    """Lazily import llmlingua and instantiate a singleton PromptCompressor.

    Returns the cached instance, or ``None`` if llmlingua is not installed or
    the model failed to load. Caches the failure state so repeated invocations
    in the same process don't keep retrying an expensive import/load.
    """
    global _compressor_instance, _compressor_failed

    if _compressor_instance is not None:
        return _compressor_instance
    if _compressor_failed:
        return None

    try:
        from llmlingua import PromptCompressor  # type: ignore[import-not-found]
    except ImportError as exc:
        _log_debug(f"llmlingua not installed: {exc}")
        _compressor_failed = True
        return None

    try:
        _log_debug(f"loading model {_MODEL_NAME!r} (this may take 2-3s)")
        _compressor_instance = PromptCompressor(
            model_name=_MODEL_NAME,
            use_llmlingua2=True,
        )
        _log_debug("model loaded")
        return _compressor_instance
    except Exception as exc:
        _log_debug(f"failed to load PromptCompressor: {exc}")
        _compressor_failed = True
        return None


def _log_metrics(
    cmd_name: str,
    original_tokens: int,
    compressed_tokens: int,
    savings_pct: int,
    latency_ms: int,
) -> None:
    """Append a tab-separated metrics row to ~/.claude-mpm/llmlingua-savings.log.

    Schema (in order):
        timestamp \\t cmd_name \\t original_tokens \\t compressed_tokens
                  \\t savings_pct \\t latency_ms
    """
    try:
        _MPM_LOG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = (
            f"{ts}\t{cmd_name}\t{original_tokens}\t{compressed_tokens}"
            f"\t{savings_pct}\t{latency_ms}\n"
        )
        with _MPM_LLMLINGUA_LOG.open("a") as fh:
            fh.write(line)
    except OSError as exc:
        _log_debug(f"failed to write metrics log: {exc}")


def _extract_bash_output(event: dict[str, Any]) -> str | None:
    """Best-effort extraction of the Bash stdout/stderr text from a hook event.

    Claude Code's PostToolUse payload shape has varied a bit across versions;
    we probe the common keys and return the first non-empty string we find.
    """
    # tool_response is the modern key
    resp = event.get("tool_response")
    if isinstance(resp, dict):
        for key in ("stdout", "output", "content"):
            val = resp.get(key)
            if isinstance(val, str) and val:
                return val
        # Some shapes nest content as a list of {type,text} blocks
        content = resp.get("content")
        if isinstance(content, list):
            parts = [
                blk.get("text", "")
                for blk in content
                if isinstance(blk, dict) and blk.get("type") == "text"
            ]
            joined = "".join(parts)
            if joined:
                return joined
    elif isinstance(resp, str) and resp:
        return resp

    # Legacy / flat layouts
    for key in ("tool_output", "output", "stdout"):
        val = event.get(key)
        if isinstance(val, str) and val:
            return val

    return None


def _extract_cmd_name(event: dict[str, Any]) -> str:
    """Extract the base command name from a Bash tool_input for log grouping.

    Mirrors ZTK's behavior of recording just the base command (e.g. ``git``,
    ``ls``) so per-command aggregation in the stats CLI works the same way.
    """
    tool_input = event.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str) or not command.strip():
        return "unknown"
    # First token, stripped of any leading path components
    first = command.strip().split()[0]
    return first.rsplit("/", 1)[-1]


def build_llmlingua_response(event: dict[str, Any]) -> dict[str, Any]:
    """Build the PostToolUse response after (optionally) compressing Bash output.

    Returns a wire-format dict ready to be JSON-serialized. On any failure or
    a non-applicable event, returns ``{"continue": True}``.

    This function is exposed as an importable symbol so a future
    ``posttooluse_dispatcher`` can call it without spawning a subprocess
    (mirroring the ZTK pattern).
    """
    if not _is_enabled():
        return {"continue": True}

    tool_name = event.get("tool_name", "")
    if tool_name != "Bash":
        return {"continue": True}

    output = _extract_bash_output(event)
    if not output or len(output) < _MIN_OUTPUT_CHARS:
        _log_debug(
            "output missing or below threshold "
            f"({len(output) if output else 0} < {_MIN_OUTPUT_CHARS})"
        )
        return {"continue": True}

    compressor = _get_compressor()
    if compressor is None:
        # llmlingua unavailable; experiment silently disabled.
        return {"continue": True}

    cmd_name = _extract_cmd_name(event)
    original_tokens = _estimate_tokens(output)

    start = time.perf_counter()
    try:
        result = compressor.compress_prompt(output, rate=_TARGET_RATIO)
    except Exception as exc:
        _log_debug(f"compression failed for {cmd_name}: {exc}")
        return {"continue": True}
    latency_ms = int((time.perf_counter() - start) * 1000)

    # PromptCompressor returns a dict with "compressed_prompt" (and stats).
    compressed_text: str
    if isinstance(result, dict) and isinstance(result.get("compressed_prompt"), str):
        compressed_text = result["compressed_prompt"]
    elif isinstance(result, str):
        compressed_text = result
    else:
        _log_debug(f"unexpected compress_prompt return shape: {type(result).__name__}")
        return {"continue": True}

    compressed_tokens = _estimate_tokens(compressed_text)
    savings_pct = (
        int((original_tokens - compressed_tokens) / original_tokens * 100)
        if original_tokens > 0
        else 0
    )

    _log_metrics(cmd_name, original_tokens, compressed_tokens, savings_pct, latency_ms)
    _log_debug(
        f"{cmd_name}: {original_tokens} -> {compressed_tokens} tokens "
        f"({savings_pct}% saved, {latency_ms} ms)"
    )

    # Emit the (potentially) rewritten output back to Claude Code. Current
    # Claude Code PostToolUse may or may not honor ``updatedOutput``; we still
    # emit it so the moment the contract exposes it, this hook starts having
    # end-to-end effect. The metrics log is the source of truth for the
    # experiment regardless.
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedOutput": compressed_text,
        }
    }


def main() -> None:
    """Read a PostToolUse event from stdin, emit the response on stdout."""
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            event = {}
    except Exception as exc:
        _log_debug(f"failed to parse event JSON: {exc}")
        print(json.dumps({"continue": True}))
        return

    try:
        response = build_llmlingua_response(event)
    except Exception as exc:
        _log_debug(f"build_llmlingua_response crashed: {exc}")
        response = {"continue": True}

    print(json.dumps(response))


if __name__ == "__main__":
    main()
