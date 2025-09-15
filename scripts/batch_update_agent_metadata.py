#!/usr/bin/env python3
"""
Batch Agent Metadata Fix Script

This script updates all 22 existing deployed agents by removing them and forcing
redeployment with the fixed metadata transfer process. This ensures all agents
get the missing 'type' field and other metadata transferred from their JSON templates.

Usage:
    python scripts/batch_update_agent_metadata.py

The script will:
1. List all currently deployed agents
2. Back them up (in case rollback is needed)
3. Remove them to force redeployment
4. Redeploy all agents with fixed metadata transfer
5. Verify the metadata was transferred correctly
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set


def run_command(cmd: List[str], check=True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if check and result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        sys.exit(1)

    return result


def get_deployed_agents(agents_dir: Path) -> List[str]:
    """Get list of currently deployed agent names."""
    if not agents_dir.exists():
        return []

    agents = []
    for agent_file in agents_dir.glob("*.md"):
        # Skip backup files
        if not agent_file.name.endswith('.backup'):
            agent_name = agent_file.stem
            agents.append(agent_name)

    return sorted(agents)


def backup_agents(agents_dir: Path, backup_dir: Path) -> None:
    """Backup all deployed agents."""
    if not agents_dir.exists():
        print("No agents directory found - nothing to backup")
        return

    print(f"Creating backup directory: {backup_dir}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    for agent_file in agents_dir.glob("*.md"):
        if not agent_file.name.endswith('.backup'):
            backup_file = backup_dir / agent_file.name
            print(f"Backing up {agent_file} -> {backup_file}")
            shutil.copy2(agent_file, backup_file)


def extract_frontmatter_fields(agent_file: Path) -> Dict[str, str]:
    """Extract frontmatter fields from an agent markdown file."""
    if not agent_file.exists():
        return {}

    content = agent_file.read_text()
    lines = content.split('\n')

    if not lines or lines[0].strip() != '---':
        return {}

    fields = {}
    in_frontmatter = True
    i = 1

    while i < len(lines) and in_frontmatter:
        line = lines[i].strip()
        if line == '---':
            break
        elif ':' in line and not line.startswith(' '):
            # Handle simple key: value pairs
            key, value = line.split(':', 1)
            fields[key.strip()] = value.strip().strip('"')
        i += 1

    return fields


def verify_metadata_transfer(agents_dir: Path, expected_agents: List[str]) -> Dict[str, Dict[str, str]]:
    """Verify that all agents have proper metadata after deployment."""
    print(f"\nVerifying metadata transfer for {len(expected_agents)} agents...")

    results = {}

    for agent_name in expected_agents:
        agent_file = agents_dir / f"{agent_name}.md"
        fields = extract_frontmatter_fields(agent_file)

        results[agent_name] = fields

        # Check for critical fields
        has_type = 'type' in fields and fields['type']
        has_name = 'name' in fields and fields['name']
        has_model = 'model' in fields and fields['model']
        has_description = 'description' in fields and fields['description']

        status = "✅" if has_type and has_name and has_model and has_description else "❌"
        type_field = fields.get('type', 'MISSING')

        print(f"{status} {agent_name}: type={type_field}, fields={len(fields)}")

    return results


def main():
    """Main script execution."""
    print("🔧 Claude MPM Agent Metadata Batch Fix Script")
    print("=" * 50)

    # Set up paths
    project_root = Path(__file__).parent.parent
    agents_dir = project_root / ".claude" / "agents"
    backup_dir = project_root / "agent_metadata_backup"

    print(f"Project root: {project_root}")
    print(f"Agents directory: {agents_dir}")
    print(f"Backup directory: {backup_dir}")

    # Step 1: Get current deployed agents
    print("\n📋 Step 1: Identifying deployed agents...")
    deployed_agents = get_deployed_agents(agents_dir)
    print(f"Found {len(deployed_agents)} deployed agents: {', '.join(deployed_agents)}")

    if not deployed_agents:
        print("No deployed agents found. Nothing to update.")
        return

    # Step 2: Backup existing agents
    print("\n💾 Step 2: Backing up existing agents...")
    backup_agents(agents_dir, backup_dir)

    # Step 3: Check metadata BEFORE fix
    print("\n🔍 Step 3: Checking metadata BEFORE fix...")
    before_results = verify_metadata_transfer(agents_dir, deployed_agents)

    missing_type_count = sum(1 for agent, fields in before_results.items() if not fields.get('type'))
    print(f"\nSUMMARY BEFORE FIX: {missing_type_count}/{len(deployed_agents)} agents missing 'type' field")

    # Step 4: Remove agents to force redeployment
    print("\n🗑️  Step 4: Removing agents to force redeployment...")
    for agent_name in deployed_agents:
        agent_file = agents_dir / f"{agent_name}.md"
        if agent_file.exists():
            print(f"Removing {agent_file}")
            agent_file.unlink()

    # Step 5: Force redeploy all agents
    print("\n🚀 Step 5: Redeploying all agents with fixed metadata transfer...")

    # Change to project directory for claude-mpm command
    os.chdir(project_root)

    # Run deployment command
    deploy_cmd = ["./scripts/claude-mpm", "agents", "deploy", "--force"]
    result = run_command(deploy_cmd)

    print("Deployment output:")
    print(result.stdout)
    if result.stderr:
        print("Deployment errors:")
        print(result.stderr)

    # Step 6: Verify metadata transfer worked
    print("\n✅ Step 6: Verifying metadata transfer...")
    after_results = verify_metadata_transfer(agents_dir, deployed_agents)

    missing_type_after = sum(1 for agent, fields in after_results.items() if not fields.get('type'))
    fixed_count = missing_type_count - missing_type_after

    print(f"\nSUMMARY AFTER FIX:")
    print(f"  • Before: {missing_type_count}/{len(deployed_agents)} agents missing 'type' field")
    print(f"  • After:  {missing_type_after}/{len(deployed_agents)} agents missing 'type' field")
    print(f"  • Fixed:  {fixed_count} agents now have proper metadata")

    # Step 7: Show detailed comparison
    print(f"\n📊 Step 7: Detailed comparison...")
    print(f"{'Agent':<20} {'Before':<15} {'After':<15} {'Status'}")
    print("-" * 65)

    for agent_name in deployed_agents:
        before_type = before_results.get(agent_name, {}).get('type', 'MISSING')
        after_type = after_results.get(agent_name, {}).get('type', 'MISSING')

        status = "FIXED ✅" if before_type == 'MISSING' and after_type != 'MISSING' else \
                 "OK ✅" if before_type != 'MISSING' and after_type != 'MISSING' else \
                 "STILL MISSING ❌"

        print(f"{agent_name:<20} {before_type:<15} {after_type:<15} {status}")

    print(f"\n🎉 Batch metadata fix completed!")
    print(f"Backup created at: {backup_dir}")

    if missing_type_after == 0:
        print("🎯 All agents now have proper metadata including the 'type' field!")
    else:
        print(f"⚠️  {missing_type_after} agents still missing metadata - manual review needed")


if __name__ == "__main__":
    main()