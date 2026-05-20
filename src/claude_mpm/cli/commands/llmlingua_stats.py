"""llmlingua-stats command: summarize compression savings from LLMLingua-2.

WHY: Mirrors the ``ztk-stats`` command but for the experimental LLMLingua-2
PostToolUse hook (``claude_mpm.hooks.llmlingua_hook``). Reads the metrics
log written by that hook and presents a summary so we can evaluate the
experiment.

LOG SCHEMA (tab-separated, written by ``llmlingua_hook._log_metrics``):
    timestamp  cmd_name  original_tokens  compressed_tokens  savings_pct  latency_ms

If the ZTK savings log also exists, a small side-by-side comparison is
appended so we can see how the two approaches stack up.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

_DEFAULT_COST_PER_MTOK = 3.0  # USD per million input tokens (Sonnet 4)
_DEFAULT_DAYS = 30
_BYTES_PER_TOKEN = 4  # used only when comparing against ZTK's byte-based log


def _llmlingua_log_path() -> Path:
    """Return the path to the LLMLingua-2 metrics log."""
    return Path.home() / ".claude-mpm" / "llmlingua-savings.log"


def _ztk_log_path() -> Path:
    """Return the path to ZTK's native savings log (for side-by-side compare)."""
    home = os.environ.get("HOME", str(Path.home()))
    return Path(home) / ".local" / "share" / "ztk" / "savings.log"


def _parse_llmlingua_log(log_path: Path, since: datetime | None = None) -> list[dict]:
    """Parse the LLMLingua-2 metrics log.

    Format (tab-separated):
        iso_timestamp  cmd  original_tokens  compressed_tokens  savings_pct  latency_ms
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
                ts = datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=UTC
                )
                if since and ts < since:
                    continue
                entries.append(
                    {
                        "ts": ts,
                        "cmd": parts[1],
                        "original_tokens": int(parts[2]),
                        "compressed_tokens": int(parts[3]),
                        "savings_pct": int(parts[4]),
                        "latency_ms": int(parts[5]),
                    }
                )
            except (ValueError, IndexError):
                continue
    return entries


def _parse_ztk_summary(log_path: Path, since: datetime | None = None) -> dict | None:
    """Lightweight ZTK log parser for the comparison row.

    Returns ``None`` if the log is absent or empty; otherwise a dict with
    ``count``, ``tokens_saved``, ``avg_pct``.
    """
    if not log_path.exists():
        return None

    count = 0
    bytes_orig = 0
    bytes_filt = 0
    with log_path.open("r", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            try:
                ts = datetime.fromtimestamp(int(parts[0]), tz=UTC)
                if since and ts < since:
                    continue
                orig = int(parts[2])
                filt = int(parts[3])
            except (ValueError, IndexError):
                continue
            count += 1
            bytes_orig += orig
            bytes_filt += filt

    if count == 0:
        return None
    saved = max(0, bytes_orig - bytes_filt)
    return {
        "count": count,
        "tokens_saved": saved // _BYTES_PER_TOKEN,
        "avg_pct": int(saved / bytes_orig * 100) if bytes_orig else 0,
    }


def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def run_llmlingua_stats(args: argparse.Namespace) -> int:
    """Print LLMLingua-2 compression savings summary."""
    days: int = getattr(args, "days", _DEFAULT_DAYS)
    top_n: int = getattr(args, "top", 10)
    cost_per_mtok: float = getattr(args, "cost_per_mtok", _DEFAULT_COST_PER_MTOK)
    json_output: bool = getattr(args, "json", False)

    since: datetime | None = None
    if days > 0:
        since = datetime.now(tz=UTC) - timedelta(days=days)

    log_path = _llmlingua_log_path()
    entries = _parse_llmlingua_log(log_path, since=since)

    if not entries:
        if json_output:
            import json

            print(json.dumps({"error": "no data", "log": str(log_path)}))
        elif not log_path.exists():
            print(
                f"No LLMLingua-2 savings log found at {log_path}.\n"
                "Set CLAUDE_MPM_USE_LLMLINGUA=1 and run some Bash commands "
                "to accumulate data."
            )
        else:
            period = f"last {days} days" if days > 0 else "all time"
            print(f"No LLMLingua-2 data for {period}.")
        return 0

    # Aggregate totals
    total_original = sum(e["original_tokens"] for e in entries)
    total_compressed = sum(e["compressed_tokens"] for e in entries)
    total_saved = total_original - total_compressed
    overall_pct = (total_saved / total_original * 100) if total_original > 0 else 0.0
    avg_latency = sum(e["latency_ms"] for e in entries) / len(entries)
    cost_saved = total_saved / 1_000_000 * cost_per_mtok

    # Per-command rollup
    cmd_stats: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "original": 0, "compressed": 0, "latency_sum": 0}
    )
    for e in entries:
        cs = cmd_stats[e["cmd"]]
        cs["count"] += 1
        cs["original"] += e["original_tokens"]
        cs["compressed"] += e["compressed_tokens"]
        cs["latency_sum"] += e["latency_ms"]

    top_cmds = sorted(
        [
            {
                "cmd": cmd,
                "count": cs["count"],
                "saved": cs["original"] - cs["compressed"],
                "pct": int((cs["original"] - cs["compressed"]) / cs["original"] * 100)
                if cs["original"] > 0
                else 0,
                "avg_latency_ms": int(cs["latency_sum"] / cs["count"])
                if cs["count"]
                else 0,
            }
            for cmd, cs in cmd_stats.items()
        ],
        key=lambda x: x["saved"],
        reverse=True,
    )[:top_n]

    # Side-by-side ZTK comparison (optional)
    ztk_summary = _parse_ztk_summary(_ztk_log_path(), since=since)

    period_label = f"last {days} days" if days > 0 else "all time"

    if json_output:
        import json

        payload = {
            "period": period_label,
            "commands_compressed": len(entries),
            "total_original_tokens": total_original,
            "total_compressed_tokens": total_compressed,
            "tokens_saved": total_saved,
            "reduction_pct": round(overall_pct, 1),
            "avg_latency_ms": round(avg_latency, 1),
            "cost_saved_usd": round(cost_saved, 4),
            "cost_per_mtok": cost_per_mtok,
            "top_commands": top_cmds,
            "log_path": str(log_path),
        }
        if ztk_summary is not None:
            payload["ztk_comparison"] = ztk_summary
        print(json.dumps(payload, indent=2))
        return 0

    # Rich terminal output
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text

        console = Console()

        console.print()
        console.print(
            "[bold cyan]LLMLingua-2 compression stats[/bold cyan]  "
            f"[dim]({period_label}, experimental)[/dim]"
        )
        console.print("[dim]" + "─" * 50 + "[/dim]")
        console.print(f"  Commands compressed:  [bold]{len(entries):,}[/bold]")
        console.print(
            f"  Tokens in / out:      "
            f"[bold]{_format_tokens(total_original)}[/bold] → "
            f"[bold]{_format_tokens(total_compressed)}[/bold]"
        )
        console.print(
            f"  Tokens saved:         "
            f"[bold green]~{_format_tokens(total_saved)}[/bold green] "
            f"[dim]({overall_pct:.1f}% reduction)[/dim]"
        )
        console.print(f"  Avg latency:          [bold]{avg_latency:.0f} ms[/bold]")
        console.print(
            f"  Cost saved:           [bold green]~${cost_saved:.2f}[/bold green] "
            f"[dim](at ${cost_per_mtok}/1M tokens)[/dim]"
        )
        console.print()

        if top_cmds:
            table = Table(
                title="Top commands by tokens saved",
                show_header=True,
                header_style="dim",
                border_style="dim",
            )
            table.add_column("#", justify="right", style="dim", width=3)
            table.add_column("Command", min_width=12)
            table.add_column("Count", justify="right")
            table.add_column("Saved", justify="right")
            table.add_column("Avg %", justify="right")
            table.add_column("Avg ms", justify="right")

            for i, row in enumerate(top_cmds, 1):
                pct = int(row["pct"])
                pct_color = "green" if pct >= 50 else ("yellow" if pct >= 25 else "dim")
                table.add_row(
                    str(i),
                    str(row["cmd"]),
                    str(row["count"]),
                    _format_tokens(int(row["saved"])),
                    Text(f"{pct}%", style=pct_color),
                    str(row["avg_latency_ms"]),
                )
            console.print(table)

        if ztk_summary is not None:
            console.print()
            console.print("[bold]vs. ZTK (same period)[/bold]")
            console.print("[dim]" + "─" * 50 + "[/dim]")
            compare = Table(show_header=True, header_style="dim", border_style="dim")
            compare.add_column("Approach", min_width=14)
            compare.add_column("Commands", justify="right")
            compare.add_column("Tokens saved", justify="right")
            compare.add_column("Avg reduction", justify="right")
            compare.add_row(
                "LLMLingua-2",
                f"{len(entries):,}",
                f"~{_format_tokens(total_saved)}",
                f"{overall_pct:.1f}%",
            )
            compare.add_row(
                "ZTK",
                f"{ztk_summary['count']:,}",
                f"~{_format_tokens(ztk_summary['tokens_saved'])}",
                f"{ztk_summary['avg_pct']}%",
            )
            console.print(compare)

        console.print(f"\n[dim]Log: {log_path}[/dim]")
        console.print()

    except ImportError:
        # Plain fallback when rich is unavailable
        print(f"\nLLMLingua-2 compression stats ({period_label}, experimental)")
        print("-" * 40)
        print(f"  Commands compressed:  {len(entries):,}")
        print(
            f"  Tokens saved:         ~{_format_tokens(total_saved)} "
            f"({overall_pct:.1f}%)"
        )
        print(f"  Avg latency:          {avg_latency:.0f} ms")
        print(
            f"  Cost saved:           ~${cost_saved:.2f} (at ${cost_per_mtok}/1M tokens)"
        )
        if top_cmds:
            print("\nTop commands by tokens saved:")
            for i, row in enumerate(top_cmds, 1):
                print(
                    f"  {i:2}. {row['cmd']:<20} {row['count']:>5} runs  "
                    f"{_format_tokens(int(row['saved'])):>8} saved  "
                    f"{row['pct']}%  ({row['avg_latency_ms']} ms)"
                )
        if ztk_summary is not None:
            print("\nvs. ZTK (same period):")
            print(
                f"  LLMLingua-2: {len(entries):>5} cmds, "
                f"~{_format_tokens(total_saved)} tokens, {overall_pct:.1f}%"
            )
            print(
                f"  ZTK:         {ztk_summary['count']:>5} cmds, "
                f"~{_format_tokens(ztk_summary['tokens_saved'])} tokens, "
                f"{ztk_summary['avg_pct']}%"
            )
        print(f"\nLog: {log_path}\n")

    return 0


def add_llmlingua_stats_parser(subparsers) -> None:
    """Register the llmlingua-stats subcommand."""
    parser = subparsers.add_parser(
        "llmlingua-stats",
        help="Show LLMLingua-2 token compression savings summary (experimental)",
        description=(
            "Summarize compression savings from the experimental LLMLingua-2 "
            "PostToolUse hook.\n\n"
            "Reads ~/.claude-mpm/llmlingua-savings.log written by "
            "claude_mpm.hooks.llmlingua_hook when CLAUDE_MPM_USE_LLMLINGUA=1 "
            "is set. If ZTK's native log is also present, a side-by-side "
            "comparison is shown."
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
    parser.set_defaults(command="llmlingua-stats")
