#!/usr/bin/env python3
"""
Proof of concept: Generate delegation matrix from agent descriptions using Claude API.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anthropic import Anthropic


def get_api_key() -> str:
    """Get API key from multiple sources."""
    # 1. Environment variable (highest priority)
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]

    # 2. Try ModelConfigManager
    try:
        from claude_mpm.config.model_config import ModelConfigManager

        config = ModelConfigManager.load_config()
        if config.claude.api_key:
            return config.claude.api_key
    except Exception as e:
        print(f"   Config load failed: {e}")

    # 3. Try keyring
    try:
        import keyring

        key = keyring.get_password("anthropic", "api_key")
        if key:
            return key
    except Exception:  # nosec B110 - keyring may not be installed
        pass

    # 4. Check common config file locations
    config_paths = [
        Path.home() / ".anthropic" / "api_key",
        Path.home() / ".config" / "anthropic" / "api_key",
    ]
    for path in config_paths:
        if path.exists():
            return path.read_text().strip()

    return ""


def load_agent_descriptions() -> list[dict]:
    """Load all agent JSON templates and extract relevant info."""
    # Look in the archive directory where agent templates are stored
    templates_dir = (
        Path(__file__).parent.parent / "src/claude_mpm/agents/templates/archive"
    )
    agents = []

    if not templates_dir.exists():
        print(f"Warning: Templates directory not found at {templates_dir}")
        # Fallback to examples directory
        templates_dir = (
            Path(__file__).parent.parent
            / "examples/project_agents/.claude-mpm/agents/templates"
        )

    if not templates_dir.exists():
        print("Error: No templates directory found")
        return agents

    for json_file in templates_dir.glob("*.json"):
        try:
            with open(json_file) as f:
                data = json.load(f)

            # Extract routing-relevant fields
            agent_info = {
                "id": data.get("agent_id", json_file.stem),
                "name": data.get("metadata", {}).get("name", data.get("name", "")),
                "description": data.get("metadata", {}).get(
                    "description", data.get("description", "")
                ),
                "type": data.get("agent_type", ""),
                "model": data.get("capabilities", {}).get("model", "sonnet"),
                "triggers": data.get("interactions", {}).get("triggers", []),
                "handoff_agents": data.get("interactions", {}).get(
                    "handoff_agents", []
                ),
                "routing_keywords": data.get("memory_routing", {}).get("keywords", [])[
                    :10
                ],  # First 10 keywords
                "tools": data.get("capabilities", {}).get("tools", [])[
                    :5
                ],  # First 5 tools
                "domain_expertise": data.get("knowledge", {}).get(
                    "domain_expertise", []
                )[:5],  # First 5
            }
            agents.append(agent_info)
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return agents


def generate_delegation_matrix(agents: list[dict]) -> str:
    """Call Claude to generate delegation matrix from agent descriptions."""
    client = Anthropic()

    # Build the prompt
    agent_summary = json.dumps(agents, indent=2)

    prompt = f"""You are helping build a Project Manager (PM) agent's delegation instructions.

Given these deployed agents with their capabilities:

{agent_summary}

Generate a concise delegation matrix that the PM can use to route tasks. Format as markdown with:

1. **Quick Reference Table**: Agent ID, Best For (2-3 words), Key Triggers
2. **Routing Decision Tree**: When user says X -> delegate to Y
3. **Handoff Chains**: Common sequences (e.g., Research -> Engineer -> QA)
4. **Model Tier Guidance**: When to use opus vs sonnet vs haiku agents

Keep it concise and actionable. The PM will use this to make instant delegation decisions."""

    print("Calling Claude API...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def main():
    print("=" * 60)
    print("Delegation Matrix Generator - Proof of Concept")
    print("=" * 60)

    # Get API key
    print("\n1. Looking for API key...")
    api_key = get_api_key()
    if not api_key:
        print("   ERROR: No API key found. Checked:")
        print("   - ANTHROPIC_API_KEY environment variable")
        print("   - ~/.claude-mpm/configuration.yaml")
        print("   - keyring storage")
        print("   - ~/.anthropic/api_key")
        print("\n   Set ANTHROPIC_API_KEY or add to configuration.yaml")
        sys.exit(1)
    print(f"   Found API key: {api_key[:10]}...")

    # Set for Anthropic client
    os.environ["ANTHROPIC_API_KEY"] = api_key

    # Load agents
    print("\n2. Loading agent descriptions...")
    agents = load_agent_descriptions()
    print(f"   Found {len(agents)} agents")

    if not agents:
        print("ERROR: No agents found to process")
        sys.exit(1)

    for agent in agents[:5]:
        desc = agent.get("description", "No description")[:50]
        print(f"   - {agent['id']}: {desc}...")
    if len(agents) > 5:
        print(f"   ... and {len(agents) - 5} more")

    # Generate matrix
    print("\n3. Generating delegation matrix via Claude API...")
    matrix = generate_delegation_matrix(agents)

    # Output
    print("\n4. Generated Delegation Matrix:")
    print("=" * 60)
    print(matrix)
    print("=" * 60)

    # Save to file
    output_file = (
        Path(__file__).parent.parent / "docs/research/generated-delegation-matrix.md"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write("# Generated Delegation Matrix\n\n")
        f.write(f"Generated: {__import__('datetime').datetime.now().isoformat()}\n\n")
        f.write(f"Source: {len(agents)} agent templates\n\n")
        f.write(matrix)
    print(f"\nSaved to: {output_file}")


if __name__ == "__main__":
    main()
