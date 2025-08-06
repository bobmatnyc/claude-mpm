#!/usr/bin/env python3
"""Test deployment with the real INSTRUCTIONS.md template.

This script tests that the deployment process correctly handles
the actual INSTRUCTIONS.md template with dynamic capabilities.
"""

import sys
import tempfile
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.framework_claude_md_generator.deployment_manager import DeploymentManager
from claude_mpm.services.framework_claude_md_generator.version_manager import VersionManager
from claude_mpm.services.framework_claude_md_generator.content_validator import ContentValidator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_real_instructions_deployment():
    """Test deployment with the real INSTRUCTIONS.md template."""
    print("\n=== Testing Real INSTRUCTIONS.md Deployment ===")
    
    # Read the actual INSTRUCTIONS.md template
    template_path = Path(__file__).parent.parent / "src/claude_mpm/agents/INSTRUCTIONS.md"
    if not template_path.exists():
        print(f"ERROR: Template not found at {template_path}")
        return False
    
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    print(f"Loaded template from: {template_path}")
    print(f"Template contains placeholder: {'{{capabilities-list}}' in template_content}")
    
    # Create test instances
    version_manager = VersionManager()
    validator = ContentValidator()
    deployment_manager = DeploymentManager(version_manager, validator)
    
    # Create temporary directory for deployment
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"\nDeploying to: {temp_path}")
        
        # Deploy content
        success, message = deployment_manager.deploy_to_parent(template_content, temp_path, force=True)
        print(f"Deployment result: {success} - {message}")
        
        if success:
            # Read deployed file
            deployed_file = temp_path / "INSTRUCTIONS.md"
            if deployed_file.exists():
                with open(deployed_file, 'r') as f:
                    deployed_content = f.read()
                
                # Check if placeholder was replaced
                if "{{capabilities-list}}" in deployed_content:
                    print("ERROR: Placeholder was not replaced during deployment!")
                    return False
                
                if "**Core Agents**:" in deployed_content:
                    print("SUCCESS: Dynamic capabilities were generated during deployment")
                    
                    # Extract and display the generated section
                    start = deployed_content.find("## Agent Names & Capabilities")
                    if start != -1:
                        end = deployed_content.find("## TodoWrite Requirements", start)
                        if end != -1:
                            generated_section = deployed_content[start:end].strip()
                            print("\nGenerated capabilities section:")
                            print("-" * 80)
                            print(generated_section)
                            print("-" * 80)
                    
                    # Verify specific agents are listed
                    expected_agents = ["research", "engineer", "qa", "documentation"]
                    all_found = all(agent in deployed_content.lower() for agent in expected_agents)
                    if all_found:
                        print("\nSUCCESS: All expected agents found in deployed content")
                    else:
                        print("\nWARNING: Some expected agents might be missing")
                    
                    return True
                else:
                    print("ERROR: Dynamic content not found in deployed file")
                    return False
            else:
                print("ERROR: Deployed file not found")
                return False
        else:
            print(f"ERROR: Deployment failed - {message}")
            return False


def main():
    """Run the deployment test."""
    print("Testing Real Deployment with Dynamic Agent Capabilities")
    print("=" * 80)
    
    # Run test
    test_success = test_real_instructions_deployment()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY:")
    print(f"  - Real INSTRUCTIONS.md deployment: {'PASS' if test_success else 'FAIL'}")
    print(f"\nOVERALL: {'PASS' if test_success else 'FAIL'}")
    
    return 0 if test_success else 1


if __name__ == "__main__":
    sys.exit(main())