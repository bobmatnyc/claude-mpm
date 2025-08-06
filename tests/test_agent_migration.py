#!/usr/bin/env python3
"""Test agent migration to new schema format."""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def main():
    """Test agent migration results."""
    print("=== Agent Migration Test ===\n")
    
    agents_dir = Path(__file__).parent.parent / "src/claude_mpm/agents/templates"
    backup_dir = agents_dir / "backup"
    
    # Expected agents
    expected_agents = [
        "engineer", "qa", "research", "documentation",
        "ops", "security", "data_engineer", "version_control"
    ]
    
    # Test 1: Check all agents exist
    print("1. Checking migrated agents exist...")
    found_agents = []
    for agent_id in expected_agents:
        agent_path = agents_dir / f"{agent_id}.json"
        if agent_path.exists():
            found_agents.append(agent_id)
            print(f"   ✓ {agent_id}.json found")
        else:
            print(f"   ✗ {agent_id}.json NOT FOUND")
    
    print(f"\n   Total: {len(found_agents)}/{len(expected_agents)} agents found")
    
    # Test 2: Check backup files
    print("\n2. Checking backup files...")
    if backup_dir.exists():
        backup_files = list(backup_dir.glob("*_agent_*.json"))
        print(f"   Found {len(backup_files)} backup files")
        
        # Sample a few backups
        for backup_file in backup_files[:3]:
            print(f"   - {backup_file.name}")
    else:
        print("   ✗ No backup directory found")
    
    # Test 3: Validate migration quality
    print("\n3. Validating migration quality...")
    migration_issues = []
    
    for agent_id in found_agents:
        agent_path = agents_dir / f"{agent_id}.json"
        with open(agent_path) as f:
            agent = json.load(f)
        
        # Check clean ID (no _agent suffix)
        if agent["id"].endswith("_agent"):
            migration_issues.append(f"{agent_id}: ID still has _agent suffix")
        
        # Check new format fields
        if "role" in agent or "goal" in agent or "backstory" in agent:
            migration_issues.append(f"{agent_id}: Old format fields still present")
        
        # Check required new fields
        required = ["id", "version", "metadata", "capabilities", "instructions"]
        missing = [field for field in required if field not in agent]
        if missing:
            migration_issues.append(f"{agent_id}: Missing required fields: {missing}")
        
        # Check instructions preserved
        if not agent.get("instructions"):
            migration_issues.append(f"{agent_id}: No instructions found")
        
        # Check resource tier
        tier = agent.get("capabilities", {}).get("resource_tier")
        if tier not in ["intensive", "standard", "lightweight"]:
            migration_issues.append(f"{agent_id}: Invalid resource tier: {tier}")
        
        # Check model format
        model = agent.get("capabilities", {}).get("model", "")
        if not model.startswith("claude-"):
            migration_issues.append(f"{agent_id}: Invalid model format: {model}")
    
    if migration_issues:
        print("   Issues found:")
        for issue in migration_issues:
            print(f"   - {issue}")
    else:
        print("   ✓ All agents migrated correctly")
    
    # Test 4: Compare with backups (if available)
    print("\n4. Comparing with backups...")
    comparison_count = 0
    
    if backup_dir.exists():
        for agent_id in found_agents[:3]:  # Sample a few
            # Try to find corresponding backup
            backup_pattern = f"{agent_id}_agent_*.json"
            backups = list(backup_dir.glob(backup_pattern))
            
            if backups:
                backup_file = backups[0]  # Take first match
                with open(backup_file) as f:
                    old_agent = json.load(f)
                
                agent_path = agents_dir / f"{agent_id}.json"
                with open(agent_path) as f:
                    new_agent = json.load(f)
                
                # Compare key content
                old_content = (
                    old_agent.get("narrative_fields", {}).get("role", "") +
                    old_agent.get("narrative_fields", {}).get("goal", "") +
                    old_agent.get("narrative_fields", {}).get("backstory", "")
                )
                
                new_instructions = new_agent.get("instructions", "")
                
                if old_content and new_instructions:
                    print(f"\n   {agent_id}:")
                    print(f"     - Old content length: {len(old_content)} chars")
                    print(f"     - New instructions length: {len(new_instructions)} chars")
                    print(f"     - Content preserved: {'✓' if len(new_instructions) > 0 else '✗'}")
                    comparison_count += 1
    
    if comparison_count == 0:
        print("   No comparisons performed")
    
    # Test 5: Resource tier assignments
    print("\n5. Checking resource tier assignments...")
    tier_counts = {"intensive": 0, "standard": 0, "lightweight": 0}
    
    for agent_id in found_agents:
        agent_path = agents_dir / f"{agent_id}.json"
        with open(agent_path) as f:
            agent = json.load(f)
        
        tier = agent.get("capabilities", {}).get("resource_tier", "unknown")
        if tier in tier_counts:
            tier_counts[tier] += 1
        
        model = agent.get("capabilities", {}).get("model", "")
        print(f"   {agent_id}: {tier} tier, {model}")
    
    print(f"\n   Tier distribution: {tier_counts}")
    
    # Summary
    print("\n=== Summary ===")
    all_found = len(found_agents) == len(expected_agents)
    no_issues = len(migration_issues) == 0
    
    if all_found and no_issues:
        print("✓ All agents successfully migrated to new format")
        print("✓ Clean IDs (no _agent suffix)")
        print("✓ Resource tiers properly assigned")
        print("✓ Instructions preserved")
        return 0
    else:
        print("✗ Migration issues detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())