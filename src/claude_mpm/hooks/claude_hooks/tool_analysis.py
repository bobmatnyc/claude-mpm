#!/usr/bin/env python3
"""Tool analysis utilities for Claude Code hook handler.

This module provides utilities for analyzing tool usage, extracting parameters,
and assessing security risks.
"""


def extract_tool_parameters(tool_name: str, tool_input: dict) -> dict:
    """Extract relevant parameters based on tool type.

    WHY tool-specific extraction:
    - Different tools have different important parameters
    - Provides meaningful context for dashboard display
    - Enables tool-specific analysis and monitoring
    """
    if not isinstance(tool_input, dict):
        return {"raw_input": str(tool_input)}

    # Common parameters across all tools
    params = {
        "input_type": type(tool_input).__name__,
        "param_keys": list(tool_input.keys()) if tool_input else [],
    }

    # Tool-specific parameter extraction
    if tool_name in [
        "Write",
        "Edit",
        "MultiEdit",
        "Read",
        "NotebookRead",
        "NotebookEdit",
    ]:
        params.update(
            {
                "file_path": tool_input.get("file_path")
                or tool_input.get("notebook_path"),
                "content_length": len(
                    str(tool_input.get("content", tool_input.get("new_string", "")))
                ),
                "is_create": tool_name == "Write",
                "is_edit": tool_name in ["Edit", "MultiEdit", "NotebookEdit"],
            }
        )
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        params.update(
            {
                "command": command[:100],  # Truncate long commands
                "command_length": len(command),
                "has_pipe": "|" in command,
                "has_redirect": ">" in command or "<" in command,
                "timeout": tool_input.get("timeout"),
            }
        )
    elif tool_name in ["Grep", "Glob"]:
        params.update(
            {
                "pattern": tool_input.get("pattern", ""),
                "path": tool_input.get("path", ""),
                "output_mode": tool_input.get("output_mode"),
            }
        )
    elif tool_name == "WebFetch":
        params.update(
            {
                "url": tool_input.get("url", ""),
                "prompt": tool_input.get("prompt", "")[:50],  # Truncate prompt
            }
        )
    elif tool_name == "Task":
        # Special handling for Task tool (agent delegations)
        params.update(
            {
                "subagent_type": tool_input.get("subagent_type", "unknown"),
                "description": tool_input.get("description", ""),
                "prompt": tool_input.get("prompt", ""),
                "prompt_preview": (
                    tool_input.get("prompt", "")[:200]
                    if tool_input.get("prompt")
                    else ""
                ),
                "is_pm_delegation": tool_input.get("subagent_type") == "pm",
                "is_research_delegation": tool_input.get("subagent_type") == "research",
                "is_engineer_delegation": tool_input.get("subagent_type") == "engineer",
            }
        )
    elif tool_name == "TodoWrite":
        # Special handling for TodoWrite tool (task management)
        todos = tool_input.get("todos", [])
        params.update(
            {
                "todo_count": len(todos),
                "todos": todos,  # Full todo list
                "todo_summary": summarize_todos(todos),
                "has_in_progress": any(t.get("status") == "in_progress" for t in todos),
                "has_pending": any(t.get("status") == "pending" for t in todos),
                "has_completed": any(t.get("status") == "completed" for t in todos),
                "priorities": list({t.get("priority", "medium") for t in todos}),
            }
        )

    return params


def summarize_todos(todos: list) -> dict:
    """Create a summary of the todo list for quick understanding."""
    if not todos:
        return {"total": 0, "summary": "Empty todo list"}

    status_counts = {"pending": 0, "in_progress": 0, "completed": 0}
    priority_counts = {"high": 0, "medium": 0, "low": 0}

    for todo in todos:
        status = todo.get("status", "pending")
        priority = todo.get("priority", "medium")

        if status in status_counts:
            status_counts[status] += 1
        if priority in priority_counts:
            priority_counts[priority] += 1

    # Create a text summary
    summary_parts = []
    if status_counts["completed"] > 0:
        summary_parts.append(f"{status_counts['completed']} completed")
    if status_counts["in_progress"] > 0:
        summary_parts.append(f"{status_counts['in_progress']} in progress")
    if status_counts["pending"] > 0:
        summary_parts.append(f"{status_counts['pending']} pending")

    return {
        "total": len(todos),
        "status_counts": status_counts,
        "priority_counts": priority_counts,
        "summary": ", ".join(summary_parts) if summary_parts else "No tasks",
    }


def classify_tool_operation(tool_name: str, tool_input: dict) -> str:
    """Classify the type of operation being performed."""
    if tool_name in ["Read", "LS", "Glob", "Grep", "NotebookRead"]:
        return "read"
    if tool_name in ["Write", "Edit", "MultiEdit", "NotebookEdit"]:
        return "write"
    if tool_name == "Bash":
        return "execute"
    if tool_name in ["WebFetch", "WebSearch"]:
        return "network"
    if tool_name == "TodoWrite":
        return "task_management"
    if tool_name == "Task":
        return "delegation"
    return "other"


def assess_security_risk(tool_name: str, tool_input: dict) -> str:
    """Assess the security risk level of the tool operation."""
    if tool_name == "Bash":
        command = tool_input.get("command", "").lower()
        # Check for potentially dangerous commands
        dangerous_patterns = [
            "rm -rf",
            "sudo",
            "chmod 777",
            "curl",
            "wget",
            "> /etc/",
            "dd if=",
        ]
        if any(pattern in command for pattern in dangerous_patterns):
            return "high"
        if any(word in command for word in ["install", "delete", "format", "kill"]):
            return "medium"
        return "low"
    if tool_name in ["Write", "Edit", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")
        # Check for system file modifications
        if any(path in file_path for path in ["/etc/", "/usr/", "/var/", "/sys/"]):
            return "high"
        if file_path.startswith("/"):
            return "medium"
        return "low"
    return "low"


def extract_tool_results(event: dict) -> dict:
    """Extract and summarize tool execution results."""
    result = {
        "exit_code": event.get("exit_code", 0),
        "has_output": False,
        "has_error": False,
    }

    # Extract output if available
    if "output" in event:
        output = str(event["output"])
        result.update(
            {
                "has_output": bool(output.strip()),
                "output_preview": output[:200] if len(output) > 200 else output,
                "output_lines": len(output.split("\n")) if output else 0,
            }
        )

    # Extract error information
    if "error" in event or event.get("exit_code", 0) != 0:
        error = str(event.get("error", ""))
        result.update(
            {
                "has_error": True,
                "error_preview": error[:200] if len(error) > 200 else error,
            }
        )

    return result


def calculate_duration(event: dict) -> int:
    """Calculate operation duration in milliseconds if timestamps are available."""
    # This would require start/end timestamps from Claude Code
    # For now, return None as we don't have this data
    return None
