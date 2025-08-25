#!/usr/bin/env python3
"""Test agent deployment to Markdown format.

This script provides basic integration testing for the AgentDeploymentService.
It tests the core deployment functionality by deploying agents to a temporary
directory and verifying the results.

OPERATIONAL PURPOSE:
- Validates deployment pipeline before production releases
- Ensures agent Markdown files are correctly generated
- Verifies deployment service initialization and execution
- Provides quick smoke test for CI/CD pipelines

TEST SCENARIOS COVERED:
1. Service initialization with default paths
2. Agent deployment to a temporary directory with force_rebuild=True
3. Deployment results reporting (total, deployed, updated, migrated, skipped, errors)
4. Markdown file generation and basic validation
5. Sample content verification from deployed files

TEST COVERAGE GAPS:
- No testing of version checking/update logic
- No testing of deployment without force_rebuild
- No testing of migration from old version formats
- No error handling scenarios (missing templates, invalid JSON, etc.)
- No testing of environment variable configuration
- No testing of deployment verification
- No testing of cleanup functionality

DEPLOYMENT PIPELINE INTEGRATION:
1. Run before production deployments
2. Include in CI/CD test suite
3. Monitor execution time (should be < 5 seconds)
4. Check for zero errors in results
5. Verify all expected agents are deployed

TROUBLESHOOTING:
- Template not found: Check src/claude_mpm/agents/templates/
- JSON parse errors: Validate template files with jq
- Missing base agent: Verify base_agent.json exists
- Deployment failures: Check file permissions
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService


def main():
    """Test agent deployment.

    This function executes a basic deployment test that:
    1. Creates a temporary directory for deployment
    2. Initializes the deployment service
    3. Deploys all agents with force_rebuild=True
    4. Reports deployment statistics
    5. Lists deployed Markdown files with sizes
    6. Shows sample content from the first deployed agent

    OPERATIONAL METRICS TO MONITOR:
    - Total execution time (target: < 5 seconds)
    - Number of agents deployed (should match template count)
    - Error count (must be 0 for success)
    - File sizes (typical range: 2-5 KB per agent)

    SUCCESS CRITERIA:
    - Zero deployment errors
    - All templates produce Markdown files
    - Markdown files contain valid frontmatter
    - Agent instructions are preserved

    Returns:
        0 on success, non-zero on failure
    """
    # Create temporary directory for testing
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Testing deployment to: {temp_path}")

        # Initialize deployment service
        service = AgentDeploymentService()

        # Deploy agents to temp directory
        results = service.deploy_agents(target_dir=temp_path, force_rebuild=True)

        print("\nDeployment Results:")
        print(f"  Total agents: {results['total']}")
        print(f"  Deployed: {len(results['deployed'])}")
        print(f"  Updated: {len(results['updated'])}")
        print(f"  Migrated: {len(results['migrated'])}")
        print(f"  Skipped: {len(results['skipped'])}")
        print(f"  Errors: {len(results['errors'])}")

        if results["errors"]:
            print("\nErrors:")
            for error in results["errors"]:
                print(f"  - {error}")

        # List deployed files
        md_files = list(temp_path.glob("*.md"))
        print(f"\nDeployed {len(md_files)} Markdown files:")
        for md_file in sorted(md_files):
            print(f"  - {md_file.name} ({md_file.stat().st_size} bytes)")

        # Show sample of first agent
        if md_files:
            sample_file = md_files[0]
            print(f"\nSample content from {sample_file.name}:")
            print("-" * 60)
            content = sample_file.read_text()
            # Show first 30 lines
            lines = content.split("\n")[:30]
            for line in lines:
                print(line)
            if len(content.split("\n")) > 30:
                print("... (truncated)")
            print("-" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
