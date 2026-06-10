"""
Session analysis package: parse Claude Code JSONL transcripts and emit reports.

WHAT: Read-only, deterministic tools to extract a structured SessionReport
      from Claude Code session transcripts and render it as canonical Markdown.
WHY:  Debugging and teaching — provides a full timeline with per-call token
      counts and rack-rate cost estimates without any LLM inference.

References
----------
LINK: none  (new subsystem — spec backfill pending)
"""
