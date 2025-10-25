"""
Output formatting utilities for CLI commands.
"""

import json
from typing import Any, Dict, List, Optional, Union

import yaml

from claude_mpm.core.enums import OutputFormat


class OutputFormatter:
    """Handles formatting output in different formats."""

    @staticmethod
    def format_json(data: Any, indent: int = 2) -> str:
        """Format data as JSON."""
        return json.dumps(data, indent=indent, default=str)

    @staticmethod
    def format_yaml(data: Any) -> str:
        """Format data as YAML."""
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @staticmethod
    def format_table(
        data: Union[List[Dict], Dict], headers: Optional[List[str]] = None
    ) -> str:
        """Format data as a simple table."""
        if not data:
            return "No data to display"

        # Handle single dict
        if isinstance(data, dict):
            data = [data]

        # Auto-detect headers if not provided
        if headers is None and data:
            headers = list(data[0].keys())

        if not headers:
            return "No data to display"

        # Calculate column widths
        col_widths = {}
        for header in headers:
            col_widths[header] = len(header)
            for row in data:
                value = str(row.get(header, ""))
                col_widths[header] = max(col_widths[header], len(value))

        # Build table
        lines = []

        # Header row
        header_row = " | ".join(header.ljust(col_widths[header]) for header in headers)
        lines.append(header_row)

        # Separator row
        separator = " | ".join("-" * col_widths[header] for header in headers)
        lines.append(separator)

        # Data rows
        for row in data:
            data_row = " | ".join(
                str(row.get(header, "")).ljust(col_widths[header]) for header in headers
            )
            lines.append(data_row)

        return "\n".join(lines)

    @staticmethod
    def format_text(data: Any) -> str:
        """Format data as human-readable text."""
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{key}:")
                    # Indent nested content
                    nested = OutputFormatter.format_text(value)
                    for line in nested.split("\n"):
                        if line.strip():
                            lines.append(f"  {line}")
                else:
                    lines.append(f"{key}: {value}")
            return "\n".join(lines)

        if isinstance(data, list):
            if not data:
                return "No items"

            lines = []
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    lines.append(f"Item {i + 1}:")
                    nested = OutputFormatter.format_text(item)
                    for line in nested.split("\n"):
                        if line.strip():
                            lines.append(f"  {line}")
                else:
                    lines.append(f"- {item}")
            return "\n".join(lines)

        return str(data)


def format_output(data: Any, format_type: str = OutputFormat.TEXT, **kwargs) -> str:
    """
    Format data according to the specified format.

    Args:
        data: Data to format
        format_type: Output format (use OutputFormat enum or string)
        **kwargs: Additional formatting options

    Returns:
        Formatted string
    """
    formatter = OutputFormatter()

    # Convert to string for comparison (handles both enum and string inputs)
    fmt = str(format_type).lower()

    if fmt == OutputFormat.JSON:
        return formatter.format_json(data, **kwargs)
    if fmt == OutputFormat.YAML:
        return formatter.format_yaml(data)
    if fmt == OutputFormat.TABLE:
        return formatter.format_table(data, **kwargs)
    if fmt == OutputFormat.TEXT:
        return formatter.format_text(data)
    # Fallback to text format
    return formatter.format_text(data)


def format_success_message(
    message: str, data: Any = None, format_type: str = OutputFormat.TEXT
) -> str:
    """
    Format a success message with optional data.

    Args:
        message: Success message
        data: Optional data to include
        format_type: Output format (use OutputFormat enum or string)

    Returns:
        Formatted success message
    """
    fmt = str(format_type).lower()
    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        result = {"success": True, "message": message}
        if data is not None:
            result["data"] = data
        return format_output(result, format_type)
    # Text format
    lines = [f"✓ {message}"]
    if data is not None:
        lines.append("")
        lines.append(format_output(data, format_type))
    return "\n".join(lines)


def format_error_message(
    message: str, details: Any = None, format_type: str = OutputFormat.TEXT
) -> str:
    """
    Format an error message with optional details.

    Args:
        message: Error message
        details: Optional error details
        format_type: Output format (use OutputFormat enum or string)

    Returns:
        Formatted error message
    """
    fmt = str(format_type).lower()
    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        result = {"success": False, "error": message}
        if details is not None:
            result["details"] = details
        return format_output(result, format_type)
    # Text format
    lines = [f"✗ {message}"]
    if details is not None:
        lines.append("")
        lines.append(format_output(details, format_type))
    return "\n".join(lines)


def format_list_output(
    items: List[Any],
    title: Optional[str] = None,
    format_type: str = OutputFormat.TEXT,
    headers: Optional[List[str]] = None,
) -> str:
    """
    Format a list of items for output.

    Args:
        items: List of items to format
        title: Optional title for the list
        format_type: Output format (use OutputFormat enum or string)
        headers: Optional headers for table format

    Returns:
        Formatted list output
    """
    fmt = str(format_type).lower()

    if not items:
        empty_msg = f"No {title.lower() if title else 'items'} found"
        if fmt in (OutputFormat.JSON, OutputFormat.YAML):
            return format_output({"items": [], "message": empty_msg}, format_type)
        return empty_msg

    if fmt in (OutputFormat.JSON, OutputFormat.YAML):
        result = {"items": items}
        if title:
            result["title"] = title
        return format_output(result, format_type)

    if fmt == OutputFormat.TABLE:
        output = ""
        if title:
            output += f"{title}\n{'=' * len(title)}\n\n"
        output += format_output(items, OutputFormat.TABLE, headers=headers)
        return output

    # Text format
    lines = []
    if title:
        lines.append(title)
        lines.append("=" * len(title))
        lines.append("")

    lines.append(format_output(items, OutputFormat.TEXT))
    return "\n".join(lines)
