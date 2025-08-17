#!/usr/bin/env python3
"""Demonstration script showing the enhanced hook data capture."""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler


def demonstrate_data_capture():
    """Demonstrate the enhanced data capture capabilities."""

    print("🎯 Enhanced Claude Hook Handler - Data Capture Demo")
    print("=" * 60)

    # Create a handler instance
    handler = ClaudeHookHandler()

    # Demo 1: User Prompt with various characteristics
    print("\n📝 USER PROMPT EVENT DEMO")
    print("-" * 30)

    user_prompt_event = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "demo-session-123",
        "cwd": "/Users/demo/project",
        "prompt": "This is an urgent bug fix request! Please help me debug this Python authentication error: ```python\ndef login(user, password):\n    # Broken code here\n    pass\n```",
    }

    # Process and show the extracted data
    print("Raw event data:")
    print(json.dumps(user_prompt_event, indent=2))

    # Simulate what gets extracted
    prompt = user_prompt_event.get("prompt", "")
    extracted_data = {
        "event_type": "user_prompt",
        "prompt_text": prompt,
        "prompt_preview": prompt[:200] if len(prompt) > 200 else prompt,
        "prompt_length": len(prompt),
        "session_id": user_prompt_event.get("session_id", ""),
        "working_directory": user_prompt_event.get("cwd", ""),
        "is_command": prompt.startswith("/"),
        "contains_code": "```" in prompt or "python" in prompt.lower(),
        "urgency": "high"
        if any(
            word in prompt.lower()
            for word in ["urgent", "error", "bug", "fix", "broken"]
        )
        else "normal",
    }

    print("\n✨ Enhanced extracted data:")
    print(json.dumps(extracted_data, indent=2))

    # Demo 2: Pre-Tool Use with file operation
    print("\n🔧 PRE-TOOL USE EVENT DEMO")
    print("-" * 30)

    pre_tool_event = {
        "hook_event_name": "PreToolUse",
        "session_id": "demo-session-123",
        "cwd": "/Users/demo/project",
        "tool_name": "Write",
        "tool_input": {
            "file_path": "/Users/demo/project/auth.py",
            "content": "def authenticate(username, password):\n    # Secure authentication logic\n    return validate_credentials(username, password)\n",
        },
    }

    print("Raw event data:")
    print(json.dumps(pre_tool_event, indent=2))

    # Simulate extraction
    tool_name = pre_tool_event.get("tool_name", "")
    tool_input = pre_tool_event.get("tool_input", {})

    extracted_pre_tool = {
        "event_type": "pre_tool",
        "tool_name": tool_name,
        "operation_type": "write",
        "tool_parameters": {
            "file_path": tool_input.get("file_path"),
            "content_length": len(str(tool_input.get("content", ""))),
            "is_create": True,
            "is_edit": False,
        },
        "session_id": pre_tool_event.get("session_id", ""),
        "working_directory": pre_tool_event.get("cwd", ""),
        "parameter_count": len(tool_input),
        "is_file_operation": True,
        "is_execution": False,
        "security_risk": "low",
    }

    print("\n✨ Enhanced extracted data:")
    print(json.dumps(extracted_pre_tool, indent=2))

    # Demo 3: Bash command with high security risk
    print("\n💻 BASH COMMAND DEMO (HIGH RISK)")
    print("-" * 35)

    bash_event = {
        "hook_event_name": "PreToolUse",
        "session_id": "demo-session-123",
        "cwd": "/Users/demo/project",
        "tool_name": "Bash",
        "tool_input": {
            "command": "sudo rm -rf /tmp/old_files && curl -sSL https://get.docker.com | bash",
            "timeout": 60000,
        },
    }

    print("Raw event data:")
    print(json.dumps(bash_event, indent=2))

    command = bash_event["tool_input"]["command"]
    extracted_bash = {
        "event_type": "pre_tool",
        "tool_name": "Bash",
        "operation_type": "execute",
        "tool_parameters": {
            "command": command[:100],
            "command_length": len(command),
            "has_pipe": "|" in command,
            "has_redirect": ">" in command or "<" in command,
            "timeout": bash_event["tool_input"].get("timeout"),
        },
        "security_risk": "high",  # Due to sudo and curl | bash pattern
        "is_execution": True,
    }

    print("\n✨ Enhanced extracted data:")
    print(json.dumps(extracted_bash, indent=2))

    # Demo 4: Post-Tool Use with results
    print("\n✅ POST-TOOL USE EVENT DEMO")
    print("-" * 30)

    post_tool_event = {
        "hook_event_name": "PostToolUse",
        "session_id": "demo-session-123",
        "cwd": "/Users/demo/project",
        "tool_name": "Read",
        "exit_code": 0,
        "output": "def authenticate(username, password):\n    # Authentication function\n    if not username or not password:\n        return False\n    return check_credentials(username, password)\n",
    }

    print("Raw event data:")
    print(json.dumps(post_tool_event, indent=2))

    output = str(post_tool_event.get("output", ""))
    extracted_post_tool = {
        "event_type": "post_tool",
        "tool_name": "Read",
        "exit_code": 0,
        "success": True,
        "status": "success",
        "duration_ms": None,  # Not available from Claude Code
        "result_summary": {
            "has_output": bool(output.strip()),
            "output_preview": output[:200] if len(output) > 200 else output,
            "output_lines": len(output.split("\n")) if output else 0,
            "has_error": False,
        },
        "has_output": True,
        "output_size": len(output),
    }

    print("\n✨ Enhanced extracted data:")
    print(json.dumps(extracted_post_tool, indent=2))

    print("\n🎉 SUMMARY")
    print("=" * 60)
    print("✅ Enhanced hook handler now captures:")
    print("   • Comprehensive prompt analysis (length, code detection, urgency)")
    print("   • Detailed tool parameters and operation classification")
    print("   • Security risk assessment for dangerous operations")
    print("   • Rich result data with success/error status")
    print("   • Working directory and session context")
    print("   • Performance metrics where available")
    print("\n🎯 Dashboard will now show meaningful, actionable information!")


if __name__ == "__main__":
    demonstrate_data_capture()
