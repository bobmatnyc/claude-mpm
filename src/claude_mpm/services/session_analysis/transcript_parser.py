"""
Parse Claude Code JSONL session transcripts into a structured SessionReport.

WHAT: Locate, read, and cross-correlate main-PM and subagent JSONL files,
      producing an ordered list of TimelineEvents enriched with token counts,
      USD cost, and call/response pairs — all without any LLM inference.
WHY:  Provides the deterministic data layer that both the Markdown emitter and
      any future converter can consume; keeping parsing separate from rendering
      makes each half independently testable.

References
----------
LINK: none  (new subsystem — spec backfill pending)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .pricing import compute_cost, resolve_model_rates

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

_EMPTY_USAGE: dict[str, int] = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
}

# Tolerance in seconds for PM-to-subagent timestamp correlation.
_CORRELATION_TOLERANCE_S: float = 2.0


def _empty_usage() -> dict[str, int]:
    return dict(_EMPTY_USAGE)


@dataclass
class CallDetail:
    """One tool call embedded inside a timeline event."""

    tool_name: str
    tool_use_id: str
    input_summary: str  # first ~120 chars of JSON-serialised input
    response_text: str  # paired tool_result content (may be empty)

    # For Agent calls
    subagent_type: str = ""
    subagent_model: str = ""
    subagent_description: str = ""

    # For Skill calls
    skill_name: str = ""
    skill_args: str = ""


@dataclass
class TimelineEvent:
    """One entry in the ordered session timeline."""

    # Identity
    uuid: str
    timestamp: datetime
    actor: str  # "bob" | "mpm" | subagent attribution name
    event_type: (
        str  # user_prompt | pm_turn | agent_call | skill_call | mcp_call | outcome
    )

    # Content
    title: str  # first ~120 chars, mechanical
    detail: str  # full text

    # Tool calls within this event (for pm_turn / subagent turns)
    calls: list[CallDetail] = field(default_factory=list)

    # Token accounting
    model: str = ""
    usage: dict[str, int] = field(default_factory=_empty_usage)
    cost_usd: float = 0.0
    pricing_fallback: bool = False

    # Links discovered in text
    github_links: list[str] = field(default_factory=list)

    # Subagent correlation metadata (set on agent_call events)
    subagent_file: str = ""  # relative path to subagent JSONL
    correlation_ambiguous: bool = False


@dataclass
class ModelTotals:
    """Aggregate token/cost totals for a single model string."""

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    total_cost_usd: float = 0.0
    turn_count: int = 0


@dataclass
class SessionReport:
    """Top-level structure produced by the parser."""

    session_id: str
    project_path: str  # absolute cwd encoded into the transcript directory name
    transcript_path: str  # absolute path to main JSONL file

    # Ordered events
    events: list[TimelineEvent] = field(default_factory=list)

    # Aggregates
    model_totals: dict[str, ModelTotals] = field(default_factory=dict)
    grand_total_cost_usd: float = 0.0
    pm_cost_usd: float = 0.0
    subagent_cost_usd: float = 0.0

    # Counts
    total_turns: int = 0
    agent_call_count: int = 0
    skill_call_count: int = 0
    mcp_call_count: int = 0

    # Derived metadata
    title: str = ""  # first user message, truncated
    started_at: datetime | None = None
    ended_at: datetime | None = None
    github_links: list[str] = field(default_factory=list)
    has_pricing_fallback: bool = False


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _encode_cwd(cwd: str) -> str:
    """Encode an absolute path to the directory-name segment used by Claude Code.

    Claude Code stores sessions under::

        ~/.claude/projects/{encoded_cwd}/{session_id}.jsonl

    where ``encoded_cwd`` is the absolute path with every ``/`` replaced by ``-``
    (the leading ``-`` is preserved; stripping it would break lookup on macOS/Linux).
    """
    return cwd.replace("/", "-")


def _claude_projects_root() -> Path:
    """Return ~/.claude/projects/."""
    return Path.home() / ".claude" / "projects"


def locate_transcript(session_id: str, cwd: str) -> Path:
    """Return the absolute path to ``{session_id}.jsonl`` for *cwd*.

    Parameters
    ----------
    session_id:
        The Claude Code session UUID (hex string, no extension).
    cwd:
        Absolute path of the project directory.

    Returns
    -------
    Path
        Path object (may not exist if the session is not recorded).
    """
    encoded = _encode_cwd(cwd)
    return _claude_projects_root() / encoded / f"{session_id}.jsonl"


def locate_subagent_transcript(session_id: str, cwd: str, agent_id: str) -> Path:
    """Return the path to a subagent's JSONL file."""
    encoded = _encode_cwd(cwd)
    return (
        _claude_projects_root()
        / encoded
        / session_id
        / "subagents"
        / f"agent-{agent_id}.jsonl"
    )


def _last_line_timestamp(path: Path) -> datetime | None:
    """Return the ``timestamp`` field of the last non-empty JSON line in *path*.

    WHAT: Reads the file from the end (up to 4 KB) to extract the last valid
          JSON object's ``timestamp`` field without loading the whole file.
    WHY:  ``find_most_recent_session`` prefers JSONL content timestamps over
          filesystem mtime so sessions are ordered by actual activity time even
          when mtime has been touched by backup/sync tools.

    Parameters
    ----------
    path:
        Path to a JSONL session file.

    Returns
    -------
    datetime | None
        Parsed UTC-aware datetime, or ``None`` if unreadable or no timestamp.
    """
    try:
        with path.open("rb") as fh:
            # Read up to 4 KB from the end -- enough for any single JSONL line.
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 4096))
            tail = fh.read()
        lines = tail.decode("utf-8", errors="replace").splitlines()
        # Walk backward to find the last non-empty, valid JSON line.
        for raw_line in reversed(lines):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                obj = json.loads(raw_line)
                ts_str = obj.get("timestamp", "")
                if ts_str:
                    return _parse_iso(ts_str)
            except (json.JSONDecodeError, AttributeError):
                continue
    except OSError:
        pass
    return None


def find_most_recent_session(cwd: str) -> str | None:
    """Return the session_id of the most recently active session for *cwd*.

    Prefers the JSONL whose last line has the newest ``timestamp`` field,
    falling back to ``st_mtime`` for files that are unreadable or have no
    timestamp.  Returns ``None`` if no sessions exist.
    """
    encoded = _encode_cwd(cwd)
    project_dir = _claude_projects_root() / encoded
    if not project_dir.is_dir():
        return None

    jsonl_files = [
        p for p in project_dir.iterdir() if p.is_file() and p.suffix == ".jsonl"
    ]
    if not jsonl_files:
        return None

    def _sort_key(p: Path) -> tuple[int, float]:
        ts = _last_line_timestamp(p)
        if ts is not None:
            # Timestamp available: primary sort (1), use epoch seconds
            return (1, ts.timestamp())
        # Fallback to mtime; primary sort (0) so these always rank below
        # files with a parsed timestamp.
        return (0, p.stat().st_mtime)

    most_recent = max(jsonl_files, key=_sort_key)
    return most_recent.stem


# ---------------------------------------------------------------------------
# Low-level JSONL helpers
# ---------------------------------------------------------------------------


def _parse_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse all valid JSON lines from a JSONL file."""
    lines: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    lines.append(obj)
            except json.JSONDecodeError:
                # Corrupt line — skip silently; the report will just miss it.
                pass
    return lines


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp string, always returning a UTC-aware datetime."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, AttributeError):
        return datetime.now(tz=UTC)


def _extract_text_from_content(content: Any) -> str:
    """Extract a single concatenated string from a message content value.

    *content* may be a plain string or a list of content blocks.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    # Nested content in tool_result
                    inner = block.get("content", [])
                    parts.append(_extract_text_from_content(inner))
        return "\n".join(p for p in parts if p)
    return ""


# ---------------------------------------------------------------------------
# Harness control-tag patterns to strip from user-visible text.
#
# Claude Code injects several XML-like wrapper tags into user prompts:
#   - Paired noise tags whose ENTIRE content should be removed:
#       <system-reminder>…</system-reminder>   (injected system context)
#       <local-command-stdout>…</local-command-stdout>  (shell output blobs)
#       <local-command-caveat>…</local-command-caveat>  (harness disclaimers)
#   - Standalone command-plumbing tags whose INNER TEXT we preserve
#     (they encode the human intent, e.g. the actual slash-command name):
#       <command-name>…</command-name>
#       <command-message>…</command-message>
#       <command-args>…</command-args>
# ---------------------------------------------------------------------------

# Tags whose entire element (tags + inner content) should be removed.
_CONTROL_BLOCK_RE = re.compile(
    r"<(system-reminder|local-command-stdout|local-command-caveat)"
    r"(?:\s[^>]*)?>.*?</\1>",
    re.DOTALL | re.IGNORECASE,
)

# Tags that wrap human intent — keep inner text, drop tags.
_COMMAND_TAG_RE = re.compile(
    r"<(command-name|command-message|command-args)(?:\s[^>]*)?>([^<]*)</\1>",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Secret redaction patterns
#
# Applied to ALL ingested text before it is stored in any TimelineEvent field
# (title, detail, call inputs/outputs, subagent prompt/response, outcome text).
# This prevents live credentials from leaking into report .md files, .jsx data,
# or <!-- meta --> blocks.
#
# Pattern order is intentional: specific prefixed patterns run FIRST so they
# match before the generic "high-entropy assignment" rule at the bottom.
# The function is idempotent: ``[REDACTED:...]`` placeholders never match any
# live-credential pattern, so re-running on already-redacted text is a no-op.
# ---------------------------------------------------------------------------

# (pattern, replacement_label) — compiled once at module load
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # npm tokens:  npm_<36 alphanum>
    (re.compile(r"npm_[A-Za-z0-9]{36}"), "npm_token"),
    # GitHub tokens:  ghp_ / gho_ / ghu_ / ghs_ / ghr_  followed by 36+ alphanum
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"), "github_token"),
    # AWS access key ID:  AKIA followed by 16 uppercase+digits
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_key"),
    # OpenAI / Anthropic-style API keys:  sk-  followed by 20+ alphanum/_/-
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "api_key"),
    # Slack tokens:  xoxb / xoxa / xoxp / xoxr / xoxs  followed by 10+ alphanum/-
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "slack_token"),
    # Authorization / Bearer tokens appearing in headers or logs.
    #
    # Two sub-cases with different prefix requirements:
    #
    #   (a) bare "Bearer <token>" — unambiguous; no Authorization: prefix needed.
    #       e.g. log line: "Sending request with Bearer eyJ..."
    #
    #   (b) "Authorization: token <token>" — requires the Authorization: prefix
    #       because bare "token <word>" appears constantly in normal prose
    #       (e.g. "The token abcde... was accepted") and would cause false positives.
    #
    # In both cases only the VALUE is replaced; the scheme word (bearer / token)
    # is kept so the line stays readable:
    #   "Authorization: Bearer [REDACTED:bearer_token]"
    #   "token [REDACTED:bearer_token]"
    # Value charset covers JWTs (dots), base64 (+/=), URL-safe variants (-_).
    # The ≥20-char minimum prevents false positives on ordinary prose.
    # Negative lookahead ``(?!\[REDACTED:)`` ensures idempotency.
    #
    # Case (a): bare Bearer (no Authorization: prefix required)
    (
        re.compile(
            r"""(?ix)
            (?:Authorization\s*:\s*)?            # optional "Authorization:" prefix
            bearer                               # scheme keyword (case-insensitive via (?i))
            \s+                                   # required whitespace
            (?!\[REDACTED:)                       # not already redacted
            (?P<val>[A-Za-z0-9._\-+/=]{20,})     # value: ≥20 chars (JWTs, base64, etc.)
            """,
        ),
        "bearer_token",
    ),
    # Case (b): "token" keyword — requires the Authorization: prefix to avoid
    # redacting bare "token <word>" in ordinary prose.
    (
        re.compile(
            r"""(?ix)
            Authorization\s*:\s*                 # "Authorization:" prefix is REQUIRED
            token                                # scheme keyword (case-insensitive via (?i))
            \s+                                   # required whitespace
            (?!\[REDACTED:)                       # not already redacted
            (?P<val>[A-Za-z0-9._\-+/=]{20,})     # value: ≥20 chars (JWTs, base64, etc.)
            """,
        ),
        "bearer_token",
    ),
    # PEM private-key blocks (DOTALL — may span multiple lines)
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
        "private_key",
    ),
    # Generic high-entropy assignment:
    #   token/password/passwd/secret/api_key/apikey/access_key
    #   followed by =, :, or => (with optional surrounding whitespace)
    #   followed by an optional quote and a value of 16+ chars
    #
    # Only the VALUE portion is replaced; the key name is preserved so the
    # report still shows context like ``api_key = [REDACTED:api_key]``.
    #
    # Negative lookahead ``(?!\[REDACTED:)`` prevents double-redaction of values
    # that a specific pattern has already replaced (e.g. when ``npm_<token>``
    # was first turned into ``[REDACTED:npm_token]``, the ``TOKEN=`` prefix in
    # ``NPM_TOKEN=`` would otherwise re-fire this rule on the placeholder).
    (
        re.compile(
            r"""(?ix)
            (?:token|password|passwd|secret|api[_\-]?key|apikey|access[_\-]key)  # key name
            \s*(?:=>|[:=])\s*                                                      # separator
            (?P<q>["\']?)                                                           # optional quote
            (?!\[REDACTED:)                                                         # not already redacted
            (?P<val>[A-Za-z0-9+/=_\-!@#$%^&*()\[\]{}<>.,;:~]{16,})               # value (≥16 chars)
            (?P=q)                                                                  # close quote
            """,
        ),
        "api_key",
    ),
]

# Pre-compiled: already-redacted placeholder — never re-redact these
_ALREADY_REDACTED_RE = re.compile(r"\[REDACTED:[a-z_]+\]")


def _redact_secrets(text: str) -> str:
    """Remove live credential strings from *text*, replacing them with labelled placeholders.

    WHAT: Scans *text* for known secret patterns (npm tokens, GitHub tokens,
          AWS access keys, OpenAI/Anthropic-style ``sk-`` API keys, Slack
          tokens, Authorization/Bearer header tokens, PEM private-key blocks,
          and generic high-entropy assignments to credential-like keys) and
          replaces each match with a ``[REDACTED:<type>]`` sentinel.
    WHY:  ``session-report`` reproduces transcript text verbatim.  Without
          scrubbing, real tokens that appeared in tool inputs, shell output, or
          assistant responses would propagate into the report ``.md``, ``.jsx``
          data files, and ``<!-- meta -->`` blocks — exactly the npm-token
          leak described in issue #738.

    Pattern order
    -------------
    Specific prefixed patterns (npm, GitHub, AWS, sk-, Slack, PEM) run before
    the generic high-entropy-assignment rule so they always win on any value
    that starts with a recognisable prefix.

    Idempotency
    -----------
    ``[REDACTED:<type>]`` placeholders do not match any live-credential regex,
    so calling this function on already-redacted text is always a no-op.

    Scope
    -----
    Normal prose (sentences, code identifiers, URLs) is not affected unless
    it accidentally matches a secret pattern — which is extremely unlikely
    given the minimum-length constraints and required prefixes.

    Parameters
    ----------
    text:
        Arbitrary UTF-8 string ingested from a JSONL transcript.

    Returns
    -------
    str
        *text* with all matched secrets replaced by ``[REDACTED:<label>]``.
    """
    for pattern, label in _SECRET_PATTERNS:
        replacement = f"[REDACTED:{label}]"
        # For the generic assignment rule the named group ``val`` covers only
        # the value portion; we splice the replacement into the full match so
        # the key name is preserved.
        if pattern.groupindex.get("val"):
            # Build a replacement that keeps everything except the ``val`` group
            def _replace_val(m: re.Match[str], _label: str = label) -> str:
                start, end = m.span("val")
                rel_start = start - m.start()
                rel_end = end - m.start()
                full = m.group(0)
                return full[:rel_start] + f"[REDACTED:{_label}]" + full[rel_end:]

            text = pattern.sub(_replace_val, text)
        else:
            text = pattern.sub(replacement, text)
    return text


def _strip_control_tags(text: str) -> str:
    """Remove Claude Code harness control tags from *text*.

    WHAT: Strips paired noise tags (system-reminder, local-command-stdout,
          local-command-caveat) and their inner content entirely, then unwraps
          command-plumbing tags (command-name, command-message, command-args)
          keeping only their inner text.
    WHY:  User prompts in session transcripts contain injected harness metadata
          that pollutes titles and user-prompt timeline cards when displayed.
          Removing them surfaces the human's actual intent.

    Tags handled
    ------------
    Remove entirely (tag + content):
      ``<system-reminder>``, ``<local-command-stdout>``,
      ``<local-command-caveat>``

    Unwrap (keep inner text, drop tags):
      ``<command-name>``, ``<command-message>``, ``<command-args>``
    """
    # Remove full block tags and their content first (may be multi-line).
    text = _CONTROL_BLOCK_RE.sub("", text)
    # Unwrap command plumbing tags, keeping only the inner text.
    text = _COMMAND_TAG_RE.sub(lambda m: m.group(2), text)
    # Collapse runs of blank lines left by removed blocks.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _make_title(text: str, max_len: int = 120) -> str:
    """Return the first non-empty line of *text*, stripped of control tags, truncated."""
    clean = _strip_control_tags(text)
    for line in clean.splitlines():
        line = line.strip()
        if line:
            return line[:max_len]
    return clean.strip()[:max_len]


_GITHUB_LINK_RE = re.compile(
    r"https?://github\.com/[^\s\)\"'>\]]+",
    re.IGNORECASE,
)


def _extract_github_links(text: str) -> list[str]:
    """Return deduplicated GitHub URLs found in *text*."""
    return list(dict.fromkeys(_GITHUB_LINK_RE.findall(text)))


def _summarise_input(inp: Any, max_len: int = 120) -> str:
    """Produce a short human-readable summary of a tool-use input dict."""
    if not inp:
        return ""
    try:
        s = json.dumps(inp, ensure_ascii=False)
    except (TypeError, ValueError):
        s = str(inp)
    return s[:max_len]


# ---------------------------------------------------------------------------
# Subagent file discovery
# ---------------------------------------------------------------------------


def _list_subagent_files(session_id: str, cwd: str) -> list[Path]:
    """Return all subagent JSONL paths for this session."""
    encoded = _encode_cwd(cwd)
    subagent_dir = _claude_projects_root() / encoded / session_id / "subagents"
    if not subagent_dir.is_dir():
        return []
    return sorted(subagent_dir.glob("agent-*.jsonl"))


# ---------------------------------------------------------------------------
# Subagent parsing
# ---------------------------------------------------------------------------


@dataclass
class _SubagentSummary:
    """Collapsed view of one subagent transcript."""

    agent_id: str  # from filename stem "agent-{agentId}"
    file_path: Path
    attribution_agent: str  # human-readable e.g. "Python Engineer"
    first_user_timestamp: datetime | None
    prompt_text: str  # first user message (the task sent to the subagent)
    response_text: str  # last assistant text block
    model: str
    usage: dict[str, int]
    cost_usd: float
    pricing_fallback: bool
    all_events: list[TimelineEvent]  # full subagent timeline for deep reporting


def _parse_subagent_transcript(path: Path) -> _SubagentSummary:
    """Parse a subagent JSONL file into a _SubagentSummary."""
    lines = _parse_jsonl(path)

    stem = path.stem  # "agent-{agentId}"
    agent_id = stem.removeprefix("agent-")
    attribution_agent = ""
    first_user_ts: datetime | None = None
    prompt_text = ""
    last_assistant_text = ""
    aggregate_model = ""
    total_usage: dict[str, int] = _empty_usage()
    all_events: list[TimelineEvent] = []
    has_fallback = False

    first_user_seen = False

    # Build a tool-use → result index for the subagent transcript
    tool_results: dict[str, str] = {}
    for raw in lines:
        msg = raw.get("message", {})
        role = msg.get("role", "")
        if role == "user":
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tid = block.get("tool_use_id", "")
                        result_content = block.get("content", [])
                        tool_results[tid] = _extract_text_from_content(result_content)

    for raw in lines:
        msg = raw.get("message", {})
        role = msg.get("role", "")
        ts = _parse_iso(raw.get("timestamp", ""))

        # Pick up attributionAgent from any line
        if not attribution_agent and raw.get("attributionAgent"):
            attribution_agent = str(raw["attributionAgent"])

        if role == "user":
            content = msg.get("content", "")
            text = _extract_text_from_content(content)
            # Skip pure tool_result messages
            content_list = content if isinstance(content, list) else []
            is_tool_result_only = bool(content_list) and all(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in content_list
            )
            if not first_user_seen and text.strip() and not is_tool_result_only:
                first_user_ts = ts
                prompt_text = text
                first_user_seen = True

        elif role == "assistant":
            model_str = msg.get("model", "")
            if model_str and not aggregate_model:
                aggregate_model = model_str
            usage = msg.get("usage", {})
            for k in total_usage:
                total_usage[k] = total_usage.get(k, 0) + (usage.get(k, 0) or 0)

            content = msg.get("content", [])
            # Collect last assistant text
            if isinstance(content, list):
                for block in reversed(content):
                    if isinstance(block, dict) and block.get("type") == "text":
                        candidate = block.get("text", "").strip()
                        if candidate:
                            last_assistant_text = candidate
                            break

            # Build per-turn events (tool uses)
            calls: list[CallDetail] = []
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        tid = block.get("id", "")
                        name = block.get("name", "")
                        inp = block.get("input", {})
                        resp = tool_results.get(tid, "")
                        cd = CallDetail(
                            tool_name=name,
                            tool_use_id=tid,
                            input_summary=_summarise_input(inp),
                            response_text=resp[:500],
                        )
                        if name == "Skill":
                            cd.skill_name = inp.get("skill", "")
                            cd.skill_args = str(inp.get("args", ""))
                        calls.append(cd)

            turn_cost = compute_cost(
                aggregate_model or "claude-sonnet",
                {k: usage.get(k, 0) or 0 for k in total_usage},
            )
            rates = resolve_model_rates(aggregate_model or "claude-sonnet")
            if rates.is_fallback:
                has_fallback = True

            event_type = "pm_turn"
            if calls:
                # Classify by dominant call type
                types = {c.tool_name for c in calls}
                if "Agent" in types:
                    event_type = "agent_call"
                elif "Skill" in types:
                    event_type = "skill_call"
                elif any(t.startswith("mcp__") for t in types):
                    event_type = "mcp_call"

            text_content = _extract_text_from_content(content)
            all_events.append(
                TimelineEvent(
                    uuid=raw.get("uuid", ""),
                    timestamp=ts,
                    actor=attribution_agent or agent_id,
                    event_type=event_type,
                    title=_make_title(text_content),
                    detail=text_content,
                    calls=calls,
                    model=aggregate_model,
                    usage={k: usage.get(k, 0) or 0 for k in total_usage},
                    cost_usd=turn_cost,
                    pricing_fallback=rates.is_fallback,
                )
            )

    aggregate_cost = compute_cost(aggregate_model or "claude-sonnet", total_usage)
    rates = resolve_model_rates(aggregate_model or "claude-sonnet")
    if rates.is_fallback:
        has_fallback = True

    return _SubagentSummary(
        agent_id=agent_id,
        file_path=path,
        attribution_agent=attribution_agent,
        first_user_timestamp=first_user_ts,
        prompt_text=prompt_text,
        response_text=last_assistant_text,
        model=aggregate_model,
        usage=total_usage,
        cost_usd=aggregate_cost,
        pricing_fallback=has_fallback,
        all_events=all_events,
    )


# ---------------------------------------------------------------------------
# Main transcript parsing
# ---------------------------------------------------------------------------


def _build_tool_result_index(lines: list[dict[str, Any]]) -> dict[str, str]:
    """Build a mapping tool_use_id -> result text from all tool_result blocks."""
    index: dict[str, str] = {}
    for raw in lines:
        msg = raw.get("message", {})
        content = msg.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tid = block.get("tool_use_id", "")
                    result_content = block.get("content", [])
                    index[tid] = _extract_text_from_content(result_content)
    return index


def _correlate_subagents(
    agent_calls: list[tuple[datetime, str]],  # (timestamp, tool_use_id)
    subagent_summaries: list[_SubagentSummary],
) -> dict[str, list[tuple[_SubagentSummary, bool]]]:
    """Match PM Agent tool_use calls to subagent files by timestamp proximity.

    Returns a mapping tool_use_id -> list of (SubagentSummary, ambiguous).
    A list length >1 means multiple distinct subagents all correlated to the
    same PM tool_use_id; every entry is preserved so no subagent is dropped.
    ``ambiguous=True`` on an entry means either:
      - multiple PM calls fell within the tolerance window for that subagent, OR
      - the tool_use_id was claimed by more than one subagent summary.
    """
    result: dict[str, list[tuple[_SubagentSummary, bool]]] = {}

    # For each subagent, find the nearest PM agent_call timestamp
    for summary in subagent_summaries:
        if summary.first_user_timestamp is None:
            continue

        sub_ts = summary.first_user_timestamp

        # Collect all PM calls within tolerance
        candidates = [
            (abs((call_ts - sub_ts).total_seconds()), tool_use_id)
            for call_ts, tool_use_id in agent_calls
            if abs((call_ts - sub_ts).total_seconds()) <= _CORRELATION_TOLERANCE_S
        ]

        if not candidates:
            continue

        candidates.sort(key=lambda x: x[0])
        # Check if multiple calls are within tolerance → ambiguous for this summary
        ambiguous = len(candidates) > 1
        best_tool_use_id = candidates[0][1]

        if best_tool_use_id in result:
            # Another subagent already mapped here — mark ALL entries ambiguous
            result[best_tool_use_id] = [(s, True) for s, _ in result[best_tool_use_id]]
            ambiguous = True

        result.setdefault(best_tool_use_id, []).append((summary, ambiguous))

    return result


def parse_session(
    session_id: str,
    cwd: str,
    *,
    include_subagents: bool = True,
    redact: bool = True,
) -> SessionReport:
    """Parse a full session into a SessionReport.

    WHAT: Reads the main JSONL, all subagent JSONLs, correlates them by
          timestamp, and builds an ordered list of TimelineEvents enriched
          with token counts, USD cost, and call/response pairings.
    WHY:  Single entry-point so callers never need to know about JSONL layout
          or correlation heuristics.

    Parameters
    ----------
    session_id:
        Claude Code session UUID.
    cwd:
        Absolute path of the project directory that owns the session.
    include_subagents:
        If ``False``, skip subagent JSONL files (useful for tests).
    redact:
        If ``True`` (default), apply :func:`_redact_secrets` to every text
        field as it is ingested so that live credentials (API tokens, private
        keys, etc.) never reach any output stage.  Pass ``redact=False`` only
        for trusted local-only use where the raw transcript text must be
        preserved verbatim (e.g. ``--no-redact`` CLI flag).

    Returns
    -------
    SessionReport
        Fully populated report (may have empty events if transcript missing).
    """
    # Local helper: apply redaction only when the redact flag is True.
    # Using a local alias keeps all call-sites terse and makes the flag
    # easy to thread through without touching every leaf expression.
    _scrub: Any = _redact_secrets if redact else (lambda t: t)

    transcript_path = locate_transcript(session_id, cwd)
    report = SessionReport(
        session_id=session_id,
        project_path=cwd,
        transcript_path=str(transcript_path),
    )

    if not transcript_path.exists():
        return report

    lines = _parse_jsonl(transcript_path)
    tool_result_index = _build_tool_result_index(lines)
    # Redact tool-result texts immediately after building the index so every
    # downstream consumer (response_text on CallDetail, outcome events) sees
    # scrubbed output.
    if redact:
        tool_result_index = {
            k: _redact_secrets(v) for k, v in tool_result_index.items()
        }

    # Parse subagent files first so we can correlate
    subagent_summaries: list[_SubagentSummary] = []
    if include_subagents:
        for sa_path in _list_subagent_files(session_id, cwd):
            sa = _parse_subagent_transcript(sa_path)
            if redact:
                # Scrub the two text fields that flow into output stages
                sa.prompt_text = _redact_secrets(sa.prompt_text)
                sa.response_text = _redact_secrets(sa.response_text)
                # Scrub all per-turn events inside the subagent summary
                for sa_ev in sa.all_events:
                    sa_ev.title = _redact_secrets(sa_ev.title)
                    sa_ev.detail = _redact_secrets(sa_ev.detail)
                    for sa_cd in sa_ev.calls:
                        sa_cd.input_summary = _redact_secrets(sa_cd.input_summary)
                        sa_cd.response_text = _redact_secrets(sa_cd.response_text)
            subagent_summaries.append(sa)

    # Collect PM-side Agent tool_use timestamps for correlation
    pm_agent_calls: list[tuple[datetime, str]] = []  # (ts, tool_use_id)

    events: list[TimelineEvent] = []
    first_user_text = ""

    for raw in lines:
        if raw.get("isSidechain"):
            continue  # main transcript should not have sidechain lines, but guard

        ts = _parse_iso(raw.get("timestamp", ""))
        uuid = raw.get("uuid", "")
        msg = raw.get("message", {})
        role = msg.get("role", "")

        if role == "user":
            content = msg.get("content", "")
            content_list = content if isinstance(content, list) else []
            is_tool_result_only = bool(content_list) and all(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in content_list
            )
            if is_tool_result_only:
                continue  # these are paired to assistant tool_uses already

            text = _extract_text_from_content(content)
            if not text.strip():
                continue

            # Strip harness control tags so user-prompt cards and the session
            # title show the human's actual intent, not injected metadata.
            clean_text = _strip_control_tags(text)
            if not clean_text:
                # After stripping, if nothing human-readable remains, skip.
                continue

            # Redact secrets AFTER stripping control tags (so we don't waste
            # effort scanning injected harness content that gets removed anyway).
            clean_text = _scrub(clean_text)

            if not first_user_text:
                first_user_text = clean_text

            links = _extract_github_links(clean_text)
            event = TimelineEvent(
                uuid=uuid,
                timestamp=ts,
                actor="bob",
                event_type="user_prompt",
                title=_make_title(clean_text),
                detail=clean_text,
                github_links=links,
            )
            events.append(event)
            if report.started_at is None:
                report.started_at = ts

        elif role == "assistant":
            model_str = msg.get("model", "")
            usage = msg.get("usage", {})
            content = msg.get("content", [])

            text_parts: list[str] = []
            calls: list[CallDetail] = []
            event_type = "pm_turn"
            has_agent = False
            has_skill = False
            has_mcp = False

            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type", "")
                    if btype == "text":
                        t = block.get("text", "")
                        if t.strip():
                            text_parts.append(_scrub(t))
                    elif btype == "tool_use":
                        tid = block.get("id", "")
                        name = block.get("name", "")
                        inp = block.get("input", {})
                        response_text = tool_result_index.get(tid, "")

                        cd = CallDetail(
                            tool_name=name,
                            tool_use_id=tid,
                            input_summary=_scrub(_summarise_input(inp)),
                            response_text=_scrub(response_text[:500]),
                        )

                        if name == "Agent":
                            has_agent = True
                            cd.subagent_type = inp.get("subagent_type", "")
                            cd.subagent_model = inp.get("model", "")
                            cd.subagent_description = _scrub(inp.get("description", ""))
                            pm_agent_calls.append((ts, tid))
                        elif name == "Skill":
                            has_skill = True
                            cd.skill_name = inp.get("skill", "")
                            cd.skill_args = _scrub(str(inp.get("args", "")))
                        elif name.startswith("mcp__"):
                            has_mcp = True

                        calls.append(cd)

            full_text = "\n".join(text_parts)
            if has_agent:
                event_type = "agent_call"
            elif has_skill:
                event_type = "skill_call"
            elif has_mcp:
                event_type = "mcp_call"

            norm_usage = {k: (usage.get(k, 0) or 0) for k in _EMPTY_USAGE}
            turn_cost = compute_cost(model_str, norm_usage)
            rates = resolve_model_rates(model_str)

            links = _extract_github_links(full_text)

            # Derive a meaningful title for this PM turn.
            # Priority: (1) PM's own text prose, (2) for Agent calls surface the
            # subagent name so the card reads "Agent → Python Engineer" rather
            # than the bare tool name "Agent", (3) generic tool name fallback.
            if full_text.strip():
                pm_title = _make_title(full_text)
            elif has_agent:
                agent_cd = next((c for c in calls if c.tool_name == "Agent"), None)
                if agent_cd and agent_cd.subagent_type:
                    pm_title = f"Agent → {agent_cd.subagent_type}"[:120]
                else:
                    pm_title = "Agent"
            elif calls:
                pm_title = _make_title(calls[0].tool_name)
            else:
                pm_title = ""

            event = TimelineEvent(
                uuid=uuid,
                timestamp=ts,
                actor="mpm",
                event_type=event_type,
                title=pm_title,
                detail=full_text,
                calls=calls,
                model=model_str,
                usage=norm_usage,
                cost_usd=turn_cost,
                pricing_fallback=rates.is_fallback,
                github_links=links,
            )
            events.append(event)
            report.ended_at = ts

            # Accumulate model totals
            if model_str not in report.model_totals:
                report.model_totals[model_str] = ModelTotals(model=model_str)
            mt = report.model_totals[model_str]
            mt.input_tokens += norm_usage.get("input_tokens", 0)
            mt.output_tokens += norm_usage.get("output_tokens", 0)
            mt.cache_creation_input_tokens += norm_usage.get(
                "cache_creation_input_tokens", 0
            )
            mt.cache_read_input_tokens += norm_usage.get("cache_read_input_tokens", 0)
            mt.total_cost_usd += turn_cost
            mt.turn_count += 1
            report.pm_cost_usd += turn_cost
            report.grand_total_cost_usd += turn_cost

            if rates.is_fallback:
                report.has_pricing_fallback = True

    # Correlate PM Agent calls → subagent summaries
    corr_map = _correlate_subagents(pm_agent_calls, subagent_summaries)

    # Attach subagent metadata to agent_call events and add subagent turn events
    # Guard against double-counting when two PM Agent calls both correlate to
    # the same subagent summary (concurrent/parallel delegation within the ±2s
    # window).  We accumulate each summary's cost/tokens EXACTLY ONCE, keyed by
    # the Python object identity of the summary, while still attaching the
    # correlation to every matching agent_call event for display purposes.
    seen_summaries: set[int] = set()
    subagent_events_to_add: list[tuple[TimelineEvent, TimelineEvent]] = []
    for event in events:
        if event.event_type != "agent_call":
            continue
        for cd in event.calls:
            if cd.tool_name != "Agent":
                continue
            tid = cd.tool_use_id
            if tid not in corr_map:
                continue
            # corr_map[tid] is now a list — iterate ALL summaries for this id
            for summary, ambiguous in corr_map[tid]:
                event.subagent_file = str(summary.file_path.name)
                event.correlation_ambiguous = ambiguous

                # Accumulate cost/tokens only on the first encounter of this summary
                if id(summary) not in seen_summaries:
                    seen_summaries.add(id(summary))

                    sa_model = summary.model or "claude-sonnet"
                    if sa_model not in report.model_totals:
                        report.model_totals[sa_model] = ModelTotals(model=sa_model)
                    mt = report.model_totals[sa_model]
                    mt.input_tokens += summary.usage.get("input_tokens", 0)
                    mt.output_tokens += summary.usage.get("output_tokens", 0)
                    mt.cache_creation_input_tokens += summary.usage.get(
                        "cache_creation_input_tokens", 0
                    )
                    mt.cache_read_input_tokens += summary.usage.get(
                        "cache_read_input_tokens", 0
                    )
                    mt.total_cost_usd += summary.cost_usd
                    mt.turn_count += len(summary.all_events)
                    report.subagent_cost_usd += summary.cost_usd
                    report.grand_total_cost_usd += summary.cost_usd

                    if summary.pricing_fallback:
                        report.has_pricing_fallback = True

                # Inject a synthetic "outcome" event after the agent_call.
                # Use the subagent's last event timestamp so the outcome appears at
                # the subagent's actual completion time rather than the parent
                # agent_call dispatch time.  Fall back to the agent_call timestamp
                # only when no subagent events were recorded.
                # cost_usd is set to 0.0: the outcome event is a display artifact
                # only; the real cost has already been accumulated into report
                # totals above.  Setting cost_usd=0.0 prevents any future re-sum
                # of events from double-counting.
                if summary.response_text:
                    outcome_ts = (
                        summary.all_events[-1].timestamp
                        if summary.all_events
                        else event.timestamp
                    )
                    # response_text was already scrubbed above when redact=True
                    outcome_event = TimelineEvent(
                        uuid=f"{cd.tool_use_id}-{summary.agent_id}-outcome",
                        timestamp=outcome_ts,
                        actor=summary.attribution_agent or summary.agent_id,
                        event_type="outcome",
                        title=_make_title(summary.response_text),
                        detail=summary.response_text,
                        model=summary.model,
                        usage=summary.usage,
                        cost_usd=0.0,
                        pricing_fallback=summary.pricing_fallback,
                        github_links=_extract_github_links(summary.response_text),
                        subagent_file=str(summary.file_path.name),
                    )
                    subagent_events_to_add.append((event, outcome_event))

    # Insert outcome events right after their parent agent_call event
    for parent, child in subagent_events_to_add:
        idx = events.index(parent)
        events.insert(idx + 1, child)

    # Compile final report
    report.events = events
    report.title = _make_title(first_user_text) if first_user_text else session_id

    # Count event types
    report.total_turns = sum(1 for e in events if e.actor in ("mpm",))
    report.agent_call_count = sum(
        len([c for c in e.calls if c.tool_name == "Agent"]) for e in events
    )
    report.skill_call_count = sum(
        len([c for c in e.calls if c.tool_name == "Skill"]) for e in events
    )
    report.mcp_call_count = sum(
        len([c for c in e.calls if c.tool_name.startswith("mcp__")]) for e in events
    )

    # Aggregate all GitHub links
    all_links: list[str] = []
    for event in events:
        all_links.extend(event.github_links)
    report.github_links = list(dict.fromkeys(all_links))

    return report
