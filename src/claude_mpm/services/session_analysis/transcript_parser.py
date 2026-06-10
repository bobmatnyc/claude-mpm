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


def find_most_recent_session(cwd: str) -> str | None:
    """Return the session_id of the most recently modified session for *cwd*.

    Scans ``~/.claude/projects/{encoded_cwd}/`` for ``*.jsonl`` files and
    returns the stem of the most recently modified one, or ``None`` if no
    sessions exist.
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

    most_recent = max(jsonl_files, key=lambda p: p.stat().st_mtime)
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


def _make_title(text: str, max_len: int = 120) -> str:
    """Return the first non-empty line of *text*, truncated to *max_len*."""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:max_len]
    return text.strip()[:max_len]


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
) -> dict[str, tuple[_SubagentSummary, bool]]:
    """Match PM Agent tool_use calls to subagent files by timestamp proximity.

    Returns a mapping tool_use_id -> (SubagentSummary, ambiguous).
    ``ambiguous=True`` means multiple agent calls fell within the tolerance
    window of the same subagent first-message timestamp.
    """
    result: dict[str, tuple[_SubagentSummary, bool]] = {}

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
        # Check if multiple calls are within tolerance → ambiguous
        ambiguous = len(candidates) > 1
        best_tool_use_id = candidates[0][1]

        # Also check if this tool_use_id is already claimed by another subagent
        if best_tool_use_id in result:
            # Mark existing as ambiguous too
            existing = result[best_tool_use_id]
            result[best_tool_use_id] = (existing[0], True)
            ambiguous = True

        result[best_tool_use_id] = (summary, ambiguous)

    return result


def parse_session(
    session_id: str,
    cwd: str,
    *,
    include_subagents: bool = True,
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

    Returns
    -------
    SessionReport
        Fully populated report (may have empty events if transcript missing).
    """
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

    # Parse subagent files first so we can correlate
    subagent_summaries: list[_SubagentSummary] = []
    if include_subagents:
        for sa_path in _list_subagent_files(session_id, cwd):
            subagent_summaries.append(_parse_subagent_transcript(sa_path))

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

            if not first_user_text:
                first_user_text = text

            links = _extract_github_links(text)
            event = TimelineEvent(
                uuid=uuid,
                timestamp=ts,
                actor="bob",
                event_type="user_prompt",
                title=_make_title(text),
                detail=text,
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
                            text_parts.append(t)
                    elif btype == "tool_use":
                        tid = block.get("id", "")
                        name = block.get("name", "")
                        inp = block.get("input", {})
                        response_text = tool_result_index.get(tid, "")

                        cd = CallDetail(
                            tool_name=name,
                            tool_use_id=tid,
                            input_summary=_summarise_input(inp),
                            response_text=response_text[:500],
                        )

                        if name == "Agent":
                            has_agent = True
                            cd.subagent_type = inp.get("subagent_type", "")
                            cd.subagent_model = inp.get("model", "")
                            cd.subagent_description = inp.get("description", "")
                            pm_agent_calls.append((ts, tid))
                        elif name == "Skill":
                            has_skill = True
                            cd.skill_name = inp.get("skill", "")
                            cd.skill_args = str(inp.get("args", ""))
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
            event = TimelineEvent(
                uuid=uuid,
                timestamp=ts,
                actor="mpm",
                event_type=event_type,
                title=_make_title(full_text or (calls[0].tool_name if calls else "")),
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
    subagent_events_to_add: list[TimelineEvent] = []
    for event in events:
        if event.event_type != "agent_call":
            continue
        for cd in event.calls:
            if cd.tool_name != "Agent":
                continue
            tid = cd.tool_use_id
            if tid not in corr_map:
                continue
            summary, ambiguous = corr_map[tid]
            event.subagent_file = str(summary.file_path.name)
            event.correlation_ambiguous = ambiguous

            # Add subagent usage to totals
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

            # Inject a synthetic "outcome" event after the agent_call
            if summary.response_text:
                outcome_event = TimelineEvent(
                    uuid=f"{cd.tool_use_id}-outcome",
                    timestamp=event.timestamp,
                    actor=summary.attribution_agent or summary.agent_id,
                    event_type="outcome",
                    title=_make_title(summary.response_text),
                    detail=summary.response_text,
                    model=summary.model,
                    usage=summary.usage,
                    cost_usd=summary.cost_usd,
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
