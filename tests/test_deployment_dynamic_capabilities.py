#!/usr/bin/env python3
"""Test the deployment with dynamic agent capabilities.

This script tests that the DeploymentManager correctly processes
dynamic capabilities during deployment.
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


def test_deployment_with_placeholder():
    """Test deployment with dynamic capabilities placeholder."""
    print("\n=== Testing Deployment with Dynamic Capabilities ===")
    
    # Create test instances
    version_manager = VersionManager()
    validator = ContentValidator()
    deployment_manager = DeploymentManager(version_manager, validator)
    
    # Create test content with placeholder
    test_content = """<!-- FRAMEWORK_VERSION: 0006 -->
<!-- LAST_MODIFIED: 2025-01-26T20:50:00Z -->

# Test Instructions

## Static Content
This is static content.

{{capabilities-list}}

## More Static Content
This is more static content.
"""
    
    # Create temporary directory for deployment
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Testing deployment to: {temp_path}")
        
        # Deploy content
        success, message = deployment_manager.deploy_to_parent(test_content, temp_path, force=True)
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
                    print("\nDeployed content preview:")
                    print("-" * 80)
                    print(deployed_content[:500] + "..." if len(deployed_content) > 500 else deployed_content)
                    print("-" * 80)
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


def test_deployment_without_placeholder():
    """Test deployment with content that has no placeholder."""
    print("\n=== Testing Deployment without Placeholder ===")
    
    # Create test instances
    version_manager = VersionManager()
    validator = ContentValidator()
    deployment_manager = DeploymentManager(version_manager, validator)
    
    # Create test content without placeholder
    test_content = """<!-- FRAMEWORK_VERSION: 0006 -->
<!-- LAST_MODIFIED: 2025-01-26T20:50:00Z -->

# Test Instructions

## Static Content Only
This content has no dynamic placeholders.
"""
    
    # Create temporary directory for deployment
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Testing deployment to: {temp_path}")
        
        # Deploy content
        success, message = deployment_manager.deploy_to_parent(test_content, temp_path, force=True)
        print(f"Deployment result: {success} - {message}")
        
        if success:
            # Read deployed file
            deployed_file = temp_path / "INSTRUCTIONS.md"
            if deployed_file.exists():
                with open(deployed_file, 'r') as f:
                    deployed_content = f.read()
                
                # Verify content is unchanged
                if deployed_content.strip() == test_content.strip():
                    print("SUCCESS: Content without placeholder deployed unchanged")
                    return True
                else:
                    print("ERROR: Content was modified unexpectedly")
                    return False
            else:
                print("ERROR: Deployed file not found")
                return False
        else:
            print(f"ERROR: Deployment failed - {message}")
            return False


def main():
    """Run all deployment tests."""
    print("Testing Deployment with Dynamic Agent Capabilities")
    print("=" * 80)
    
    # Run tests
    test1_success = test_deployment_with_placeholder()
    test2_success = test_deployment_without_placeholder()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY:")
    print(f"  - Deployment with placeholder: {'PASS' if test1_success else 'FAIL'}")
    print(f"  - Deployment without placeholder: {'PASS' if test2_success else 'FAIL'}")
    
    overall_success = test1_success and test2_success
    print(f"\nOVERALL: {'PASS' if overall_success else 'FAIL'}")
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())