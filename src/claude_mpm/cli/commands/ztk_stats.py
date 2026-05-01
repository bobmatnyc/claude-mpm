"""ztk-stats command: summarize token savings from ztk compression.

WHY: ztk compresses shell command output before it reaches Claude, reducing
token usage by 80-97% on common commands. This command reads ztk's native
savings log (~/.local/share/ztk/savings.log) and presents an MPM-formatted
summary so users can understand the cost savings from the ztk hook.

DESIGN DECISIONS:
- Read ztk's own log directly rather than duplicating logging in the hook.
  ztk already tracks every run accurately; double-logging would diverge.
- Compute token counts using a 4-bytes-per-token heuristic (standard estimate
  for English/code output). Exact tiktoken counts would require a large dep.
- Cost estimate uses Sonnet 4 input price ($3/1M tokens) as the reference.
  The flag --cost-per-mtok lets users override for their actual model.
- Support --days filter so users can scope the report to recent work.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

_BYTES_PER_TOKEN = 4  # rough heuristic: 1 token ≈ 4 bytes for code/English
_DEFAULT_COST_PER_MTOK = 3.0  # USD per million input tokens (Sonnet 4)
_DEFAULT_DAYS = 30


def _ztk_log_path() -> Path:
    """Return the path to ztk's native savings log."""
    home = os.environ.get("HOME", str(Path.home()))
    return Path(home) / ".local" / "share" / "ztk" / "savings.log"


def _parse_log(log_path: Path, since: datetime | None = None) -> list[dict]:
    """Parse ztk savings.log entries.

    Log format (tab-separated):
        unix_timestamp  cmd_name  original_bytes  filtered_bytes  savings_pct  exit=N

    Returns list of dicts with keys: ts, cmd, original, filtered, pct, exit_code.
    """
    entries: list[dict] = []
    if not log_path.exists():
        return entries

    with log_path.open("r", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 6:
                continue
            try:
                ts_raw, cmd, orig_raw, filt_raw, pct_raw, exit_raw = (
                    parts[0],
                    parts[1],
                    parts[2],
                    parts[3],
                    parts[4],
                    parts[5],
                )
                ts = datetime.fromtimestamp(int(ts_raw), tz=UTC)
                if since and ts < since:
                    continue
                entries.append(
                    {
                        "ts": ts,
                        "cmd": cmd,
                        "original": int(orig_raw),
                        "filtered": int(filt_raw),
                        "pct": int(pct_raw.rstrip("%")),
                        "exit_code": int(exit_raw.split("=", 1)[-1]),
                    }
                )
            except (ValueError, IndexError):
                continue
    return entries


def _bytes_to_tokens(byte_count: int) -> int:
    return max(0, byte_count // _BYTES_PER_TOKEN)


def _format_bytes(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n}B"


def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def run_ztk_stats(args: argparse.Namespace) -> int:
    """Print ztk compression savings summary."""
    days: int = getattr(args, "days", _DEFAULT_DAYS)
    top_n: int = getattr(args, "top", 10)
    cost_per_mtok: float = getattr(args, "cost_per_mtok", _DEFAULT_COST_PER_MTOK)
    json_output: bool = getattr(args, "json", False)

    since: datetime | None = None
    if days > 0:
        since = datetime.now(tz=UTC) - timedelta(days=days)

    log_path = _ztk_log_path()
    entries = _parse_log(log_path, since=since)

    if not entries:
        if json_output:
            import json

            print(json.dumps({"error": "no data", "log": str(log_path)}))
        elif not log_path.exists():
            print(
                f"No ztk savings log found at {log_path}.\n"
                "Run some commands through claude-mpm to accumulate data."
            )
        else:
            period = f"last {days} days" if days > 0 else "all time"
            print(f"No ztk data for {period}.")
        return 0

    # Aggregate
    total_original = sum(e["original"] for e in entries)
    total_filtered = sum(e["filtered"] for e in entries)
    total_saved = total_original - total_filtered
    overall_pct = (total_saved / total_original * 100) if total_original > 0 else 0.0

    tokens_saved = _bytes_to_tokens(total_saved)
    cost_saved = tokens_saved / 1_000_000 * cost_per_mtok

    # Per-command aggregation
    cmd_stats: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "original": 0, "filtered": 0}
    )
    for e in entries:
        cs = cmd_stats[e["cmd"]]
        cs["count"] += 1
        cs["original"] += e["original"]
        cs["filtered"] += e["filtered"]

    # Sort by bytes saved descending
    top_cmds = sorted(
        [
            {
                "cmd": cmd,
                "count": cs["count"],
                "saved": cs["original"] - cs["filtered"],
                "pct": int((cs["original"] - cs["filtered"]) / cs["original"] * 100)
                if cs["original"] > 0
                else 0,
            }
            for cmd, cs in cmd_stats.items()
        ],
        key=lambda x: x["saved"],
        reverse=True,
    )[:top_n]

    period_label = f"last {days} days" if days > 0 else "all time"

    if json_output:
        import json

        print(
            json.dumps(
                {
                    "period": period_label,
                    "commands_compressed": len(entries),
                    "total_original_bytes": total_original,
                    "total_filtered_bytes": total_filtered,
                    "bytes_saved": total_saved,
                    "reduction_pct": round(overall_pct, 1),
                    "tokens_saved": tokens_saved,
                    "cost_saved_usd": round(cost_saved, 4),
                    "cost_per_mtok": cost_per_mtok,
                    "top_commands": top_cmds,
                    "log_path": str(log_path),
                },
                indent=2,
            )
        )
        return 0

    # Rich terminal output
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text

        console = Console()

        console.print()
        console.print(
            f"[bold cyan]ztk compression stats[/bold cyan]  [dim]({period_label})[/dim]"
        )
        console.print("[dim]" + "─" * 50 + "[/dim]")
        console.print(f"  Commands compressed:  [bold]{len(entries):,}[/bold]")
        console.print(
            f"  Data in / out:        [bold]{_format_bytes(total_original)}[/bold] "
            f"→ [bold]{_format_bytes(total_filtered)}[/bold]"
        )
        console.print(
            f"  Bytes saved:          [bold green]{_format_bytes(total_saved)}[/bold green] "
            f"[dim]({overall_pct:.1f}% reduction)[/dim]"
        )
        console.print(
            f"  Tokens saved:         [bold green]~{_format_tokens(tokens_saved)}[/bold green]"
        )
        console.print(
            f"  Cost saved:           [bold green]~${cost_saved:.2f}[/bold green] "
            f"[dim](at ${cost_per_mtok}/1M tokens)[/dim]"
        )
        console.print()

        if top_cmds:
            table = Table(
                title="Top commands by bytes saved",
                show_header=True,
                header_style="dim",
                border_style="dim",
            )
            table.add_column("#", justify="right", style="dim", width=3)
            table.add_column("Command", min_width=12)
            table.add_column("Count", justify="right")
            table.add_column("Saved", justify="right")
            table.add_column("Avg %", justify="right")

            for i, row in enumerate(top_cmds, 1):
                pct = int(row["pct"])
                pct_color = "green" if pct >= 80 else ("yellow" if pct >= 40 else "dim")
                table.add_row(
                    str(i),
                    str(row["cmd"]),
                    str(row["count"]),
                    _format_bytes(int(row["saved"])),
                    Text(f"{pct}%", style=pct_color),
                )
            console.print(table)

        console.print(f"\n[dim]Log: {log_path}[/dim]")
        console.print()

    except ImportError:
        # Fallback: plain text output when rich is unavailable
        print(f"\nztk compression stats ({period_label})")
        print("-" * 40)
        print(f"  Commands compressed:  {len(entries):,}")
        print(
            f"  Bytes saved:          {_format_bytes(total_saved)} ({overall_pct:.1f}%)"
        )
        print(f"  Tokens saved:         ~{_format_tokens(tokens_saved)}")
        print(
            f"  Cost saved:           ~${cost_saved:.2f} (at ${cost_per_mtok}/1M tokens)"
        )
        if top_cmds:
            print("\nTop commands by bytes saved:")
            for i, row in enumerate(top_cmds, 1):
                print(
                    f"  {i:2}. {row['cmd']:<20} {row['count']:>5} runs  "
                    f"{_format_bytes(int(row['saved'])):>8} saved  {row['pct']}%"
                )
        print(f"\nLog: {log_path}\n")

    return 0


def add_ztk_stats_parser(subparsers) -> None:
    """Register the ztk-stats subcommand."""
    parser = subparsers.add_parser(
        "ztk-stats",
        help="Show ztk token compression savings summary",
        description=(
            "Summarize token savings from ztk output compression.\n\n"
            "Reads ztk's native savings log at ~/.local/share/ztk/savings.log "
            "and reports compressed bytes, estimated tokens saved, and "
            "approximate cost savings per command."
        ),
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=_DEFAULT_DAYS,
        metavar="N",
        help=f"Limit report to the last N days (0 = all time, default: {_DEFAULT_DAYS})",
    )
    parser.add_argument(
        "--top",
        "-n",
        type=int,
        default=10,
        metavar="N",
        help="Number of top commands to show (default: 10)",
    )
    parser.add_argument(
        "--cost-per-mtok",
        type=float,
        default=_DEFAULT_COST_PER_MTOK,
        metavar="PRICE",
        help=f"Input token cost in USD per 1M tokens (default: {_DEFAULT_COST_PER_MTOK})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--all-time",
        action="store_true",
        help="Show stats for all time (equivalent to --days 0)",
    )
    parser.set_defaults(command="ztk-stats")
