#!/usr/bin/env python3
"""Test that redeployment correctly skips up-to-date agents."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService

def main():
    """Test redeployment with semantic versioning."""
    service = AgentDeploymentService()
    
    print("Running deployment again (should skip all agents)...")
    results = service.deploy_agents(force_rebuild=False)
    
    print(f"\nDeployment results:")
    print(f"  Target: {results['target_dir']}")
    print(f"  Deployed: {len(results['deployed'])}")
    print(f"  Updated: {len(results['updated'])}")
    print(f"  Skipped: {len(results['skipped'])}")
    print(f"  Errors: {len(results['errors'])}")
    
    if results['skipped']:
        print(f"\nSkipped agents: {', '.join(results['skipped'])}")
    
    # Test version comparison examples
    print("\n\nVersion comparison examples:")
    
    def compare_versions(v1: tuple, v2: tuple) -> int:
        """Compare two version tuples."""
        for a, b in zip(v1, v2):
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0
    
    examples = [
        ((2, 1, 0), (2, 0, 0), "2.1.0 > 2.0.0"),
        ((2, 1, 0), (2, 1, 0), "2.1.0 == 2.1.0"),
        ((2, 1, 0), (2, 1, 1), "2.1.0 < 2.1.1"),
        ((3, 0, 0), (2, 9, 9), "3.0.0 > 2.9.9"),
    ]
    
    for v1, v2, expected in examples:
        result = compare_versions(v1, v2)
        op = ">" if result > 0 else "==" if result == 0 else "<"
        v1_str = service._format_version_display(v1)
        v2_str = service._format_version_display(v2)
        print(f"  {v1_str} {op} {v2_str} - {expected}")

if __name__ == "__main__":
    main()