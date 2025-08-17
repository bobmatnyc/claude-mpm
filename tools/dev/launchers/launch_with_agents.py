#!/usr/bin/env python3
"""Launch Claude with native agent deployment."""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.core.claude_launcher import ClaudeLauncher
from claude_mpm.core.framework_loader import FrameworkLoader


def deploy_agents(force_redeploy=False):
    """Deploy system agents to project .claude/agents directory."""

    system_agents_dir = (
        Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "system"
    )
    local_agents_dir = Path.cwd() / ".claude" / "agents"

    # Create local directory
    local_agents_dir.mkdir(parents=True, exist_ok=True)

    print("📦 Deploying system agents...")
    print(f"  Source: {system_agents_dir}")
    print(f"  Target: {local_agents_dir}")

    deployed = []
    skipped = []

    for agent_file in system_agents_dir.glob("*.md"):
        target = local_agents_dir / agent_file.name

        if target.exists() and not force_redeploy:
            skipped.append(agent_file.name)
        else:
            shutil.copy2(agent_file, target)
            deployed.append(agent_file.name)

    if deployed:
        print(f"\n✅ Deployed {len(deployed)} agents:")
        for agent in deployed:
            print(f"  - {agent}")

    if skipped:
        print(f"\n⏭️  Skipped {len(skipped)} existing agents (use --force to redeploy)")

    return len(deployed), len(skipped)


def main():
    print("🚀 Claude MPM Launch with Native Agents")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Directory: {Path.cwd()}")

    # Parse arguments
    force_redeploy = "--force" in sys.argv
    interactive = "--non-interactive" not in sys.argv

    # Step 1: Deploy agents
    print("\n" + "=" * 60)
    print("STEP 1: Agent Deployment")
    print("=" * 60)
    deployed, skipped = deploy_agents(force_redeploy)

    # Step 2: Set environment
    print("\n" + "=" * 60)
    print("STEP 2: Environment Configuration")
    print("=" * 60)

    env = os.environ.copy()

    # Set Claude config directory to project root
    env["CLAUDE_CONFIG_DIR"] = str(Path.cwd() / ".claude")
    env["CLAUDE_MAX_PARALLEL_SUBAGENTS"] = "10"
    env["CLAUDE_TIMEOUT"] = "600000"
    env["CLAUDE_DEBUG"] = "false"
    env["CLAUDE_CONTEXT_PRESERVATION"] = "true"

    print("📋 Environment variables:")
    print(f"  CLAUDE_CONFIG_DIR: {env['CLAUDE_CONFIG_DIR']}")
    print(f"  CLAUDE_MAX_PARALLEL_SUBAGENTS: {env['CLAUDE_MAX_PARALLEL_SUBAGENTS']}")
    print(f"  CLAUDE_TIMEOUT: {env['CLAUDE_TIMEOUT']}")

    # Step 3: Load framework instructions
    print("\n" + "=" * 60)
    print("STEP 3: Framework Instructions")
    print("=" * 60)

    framework_loader = FrameworkLoader()
    framework_instructions = framework_loader.get_framework_instructions()

    # Add native agent instructions
    agent_instructions = """
## Native Agent Integration

You now have access to specialized agents through the Task tool:
- **engineer**: Code implementation and development
- **qa**: Testing and quality assurance
- **documentation**: Documentation creation and maintenance
- **research**: Investigation and analysis
- **security**: Security analysis and review
- **ops**: Operations and deployment
- **data-engineer**: Data processing and management
- **version-control**: Git and version management
- **ticketing**: Ticket creation and management

To delegate tasks, use:
```
Task("agent-name: Your task description here")
```

Example:
```
Task("engineer: Implement the user authentication module")
Task("qa: Write unit tests for the auth module")
```

The agents are loaded from .claude/agents/ and have specialized capabilities.
"""

    full_instructions = framework_instructions + "\n\n" + agent_instructions

    print("✅ Framework instructions loaded")
    print(f"  Size: {len(full_instructions)} characters")

    # Step 4: Launch Claude
    print("\n" + "=" * 60)
    print("STEP 4: Launching Claude")
    print("=" * 60)

    launcher = ClaudeLauncher(model="opus", skip_permissions=True, log_level="INFO")

    if interactive:
        print("\n🎯 Starting interactive session with native agents...")
        print("  Agents available: engineer, qa, documentation, research, etc.")
        print("  Use Task tool for delegation: Task('agent: task')")
        print("\n" + "-" * 60)

        # Create a system prompt that includes framework
        # For interactive mode, we need to pass as a flag or initial message
        # Claude doesn't support system prompts in interactive mode directly
        print("\nNOTE: In interactive mode, paste the framework instructions manually")
        print("or use non-interactive mode for automatic injection.\n")

        # Set environment then launch
        for key, value in env.items():
            os.environ[key] = value

        process = launcher.launch_interactive()
        process.wait()
    else:
        # Non-interactive mode - we can inject instructions
        user_input = (
            " ".join(sys.argv[1:])
            .replace("--non-interactive", "")
            .replace("--force", "")
            .strip()
        )

        if not user_input:
            print("❌ Error: No input provided for non-interactive mode")
            sys.exit(1)

        print(f"\n📝 User input: {user_input}")
        print("\n🔄 Running with framework and native agents...\n")

        full_message = full_instructions + "\n\nUser: " + user_input

        # Set environment then launch
        for key, value in env.items():
            os.environ[key] = value

        stdout, stderr, returncode = launcher.launch_oneshot(
            message=full_message, use_stdin=True, timeout=120
        )

        print("Response:")
        print("-" * 60)
        print(stdout)

        if stderr:
            print("\nErrors:")
            print(stderr)

    print("\n✅ Session complete!")


if __name__ == "__main__":
    main()
