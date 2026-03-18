#!/usr/bin/env python3
"""Test enhanced memory injection system with deployment checks."""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_memory_injection_with_deployment_check():
    """Test that memory injection only loads memories for deployed agents."""

    print("\n" + "=" * 60)
    print("MEMORY INJECTION DEPLOYMENT CHECK TEST")
    print("=" * 60)

    # Set up logging to capture all messages
    logging.basicConfig(
        level=logging.DEBUG, format="%(levelname)s - %(name)s - %(message)s"
    )

    # Capture log messages from the start
    log_capture = []

    class LogHandler(logging.Handler):
        def emit(self, record):
            log_capture.append((record.levelname, record.getMessage()))

    # Add handler to capture all framework loader logs
    handler = LogHandler()
    logging.getLogger("claude_mpm.framework_loader").addHandler(handler)
    logging.getLogger("claude_mpm.framework_loader").setLevel(logging.DEBUG)

    # Create framework loader
    loader = FrameworkLoader()

    # Get deployed agents
    deployed = loader._get_deployed_agents()

    print(f"\n📋 DEPLOYED AGENTS ({len(deployed)} found)")
    print("-" * 40)
    for agent in sorted(deployed):
        print(f"  ✓ {agent}")

    # Analyze memory files
    print("\n📁 MEMORY FILES ANALYSIS")
    print("-" * 40)

    memories_to_check = []

    # Check user memories
    user_memories_dir = Path.home() / ".claude-mpm" / "memories"
    if user_memories_dir.exists():
        print(f"\n🏠 User memories: {user_memories_dir}")
        for memory_file in sorted(user_memories_dir.glob("*_memories.md")):
            if memory_file.name == "PM_memories.md":
                print(f"  ✓ {memory_file.name:<40} [PM - always loaded]")
                continue

            agent_name = memory_file.stem[:-9]  # Remove "_memories" suffix
            status = "✓ DEPLOYED" if agent_name in deployed else "✗ NOT DEPLOYED"
            print(f"  {status:<15} {memory_file.name:<40} (agent: {agent_name})")
            memories_to_check.append(
                (memory_file, agent_name, agent_name in deployed, "user")
            )

    # Check project memories
    project_memories_dir = Path.cwd() / ".claude-mpm" / "memories"
    if project_memories_dir.exists():
        print(f"\n📂 Project memories: {project_memories_dir}")
        for memory_file in sorted(project_memories_dir.glob("*_memories.md")):
            if memory_file.name == "PM_memories.md":
                print(f"  ✓ {memory_file.name:<40} [PM - always loaded]")
                continue

            agent_name = memory_file.stem[:-9]  # Remove "_memories" suffix
            status = "✓ DEPLOYED" if agent_name in deployed else "✗ NOT DEPLOYED"
            print(f"  {status:<15} {memory_file.name:<40} (agent: {agent_name})")
            memories_to_check.append(
                (memory_file, agent_name, agent_name in deployed, "project")
            )

    # Test actual loading process
    print("\n🧪 TESTING MEMORY LOADING PROCESS")
    print("-" * 40)

    # Load the framework (which includes memory loading)
    try:
        # Get framework instructions which triggers memory loading
        instructions = loader.get_framework_instructions()
        print("✓ Framework loaded successfully")

        # The content is stored internally in loader.framework_content
        content = (
            loader.framework_content if hasattr(loader, "framework_content") else {}
        )
    except Exception as e:
        print(f"✗ Framework loading failed: {e}")
        return False

    # Analyze captured logs
    print("\n📊 LOG ANALYSIS")
    print("-" * 40)

    # Filter relevant log messages
    loaded_logs = [
        msg for level, msg in log_capture if "Loaded" in msg and "memory" in msg.lower()
    ]
    skipped_logs = [msg for level, msg in log_capture if "Skipped" in msg]
    warning_logs = [msg for level, msg in log_capture if level == "WARNING"]
    summary_logs = [
        msg for level, msg in log_capture if "Memory loading complete" in msg
    ]

    print(f"\n✅ Loaded memories ({len(loaded_logs)}):")
    for msg in loaded_logs:
        # Extract key info from message
        if "PM memory" in msg:
            print("  • PM memory loaded")
        elif "memory for" in msg:
            # Extract agent name from message
            import re

            match = re.search(r"memory for (\w+):", msg)
            if match:
                agent = match.group(1)
                print(f"  • {agent} memory loaded")

    print(f"\n⏭️  Skipped memories ({len(skipped_logs)}):")
    if not skipped_logs:
        # Debug: show all log messages to see what we're getting
        print("  (No skip messages found. Showing all INFO messages for debugging:)")
        info_logs = [msg for level, msg in log_capture if level == "INFO"][:10]
        for msg in info_logs[:5]:
            print(f"    - {msg[:100]}")
    else:
        for msg in skipped_logs:
            # Extract file name from message
            if "agent" in msg and "not deployed" in msg:
                import re

                match = re.search(
                    r"(\w+_memories\.md).*agent '([\w\s]+)' not deployed", msg
                )
                if match:
                    filename = match.group(1)
                    agent = match.group(2)
                    print(f"  • {filename} (agent '{agent}' not deployed)")

    if warning_logs:
        print(f"\n⚠️  Warnings ({len(warning_logs)}):")
        for msg in warning_logs:
            if "Naming mismatch" in msg:
                print(f"  • {msg}")

    if summary_logs:
        print("\n📈 Summary:")
        for msg in summary_logs:
            print(f"  {msg}")

    # Verify content
    print("\n🔍 CONTENT VERIFICATION")
    print("-" * 40)

    if "actual_memories" in content:
        pm_size = len(content["actual_memories"])
        print(f"✓ PM memories loaded into framework_content: {pm_size:,} bytes")
    else:
        print("✗ PM memories NOT found in framework_content")

    # NEW ARCHITECTURE: Agent memories should NOT be in framework_content
    # They are now loaded at deployment time and appended to agent files
    if "agent_memories" in content and len(content["agent_memories"]) > 0:
        print("✗ Agent memories found in framework_content (should NOT be there)")
        print(f"  Found: {list(content['agent_memories'].keys())}")
        print("  Agent memories are now loaded at deployment time, not framework time")
    else:
        print(
            "✓ No agent memories in framework_content (correct - now loaded at deployment time)"
        )

    # Also verify memories are in the actual instructions
    print("\n📝 INSTRUCTION INJECTION VERIFICATION")
    print("-" * 40)

    if "## Current PM Memories" in instructions:
        print("✓ PM memories injected into instructions")
    else:
        print("✗ PM memories NOT in instructions")

    # NEW ARCHITECTURE: Agent memories should NOT be in PM instructions
    # They are now appended to individual agent files at deployment time
    if "## Agent Memories" in instructions:
        print("✗ Agent memories section found in instructions (should NOT be there)")
        print("  Agent memories are now appended to agent files, not PM instructions")
    else:
        print("✓ Agent memories NOT in instructions (correct - now in agent files)")

    # Verification summary
    print("\n✨ VERIFICATION SUMMARY")
    print("-" * 40)

    # Check each expected behavior
    checks_passed = []
    checks_failed = []

    # Check 1: Non-deployed agents are skipped
    non_deployed_found = []
    for memory_file, agent_name, is_deployed, _source in memories_to_check:
        if not is_deployed:
            non_deployed_found.append(agent_name)
            # This should have been skipped
            skip_msg = f"agent '{agent_name}' not deployed"
            if any(skip_msg in msg for level, msg in log_capture if "Skipped" in msg):
                checks_passed.append(
                    f"Non-deployed agent '{agent_name}' was properly skipped"
                )
            else:
                checks_failed.append(
                    f"Non-deployed agent '{agent_name}' was not properly skipped"
                )

    if not non_deployed_found:
        checks_passed.append(
            "No non-deployed agents found (all memories are for deployed agents)"
        )

    # Check 2: Deployed agents - NEW: should NOT be in framework content
    # Agent memories are now loaded at deployment time
    for memory_file, agent_name, is_deployed, _source in memories_to_check:
        if is_deployed:
            # NEW: This should NOT be in framework content anymore
            if agent_name in content.get("agent_memories", {}):
                checks_failed.append(
                    f"Deployed agent '{agent_name}' memory found in framework (should be in agent file now)"
                )
            else:
                checks_passed.append(
                    f"Deployed agent '{agent_name}' memory not in framework (correct - now in agent file)"
                )

    # Check 3: PM memories are always loaded
    if "actual_memories" in content:
        checks_passed.append("PM memories were loaded (as expected)")
    else:
        checks_failed.append("PM memories were NOT loaded (should always be loaded)")

    # Print results
    print(f"\n✅ Passed checks ({len(checks_passed)}):")
    for check in checks_passed:
        print(f"  • {check}")

    if checks_failed:
        print(f"\n❌ Failed checks ({len(checks_failed)}):")
        for check in checks_failed:
            print(f"  • {check}")

    print("\n" + "=" * 60)
    print(f"TEST {'PASSED' if not checks_failed else 'FAILED'}")
    print("=" * 60 + "\n")

    return len(checks_failed) == 0


if __name__ == "__main__":
    success = test_memory_injection_with_deployment_check()
    sys.exit(0 if success else 1)
