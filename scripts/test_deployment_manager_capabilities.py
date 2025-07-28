#!/usr/bin/env python3
"""Test DeploymentManager integration with dynamic capabilities."""

import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.framework_claude_md_generator.deployment_manager import DeploymentManager
from claude_mpm.services.framework_claude_md_generator.version_manager import VersionManager
from claude_mpm.services.framework_claude_md_generator.content_validator import ContentValidator
from claude_mpm.services.framework_claude_md_generator.content_assembler import ContentAssembler


def test_deployment_manager_processing():
    """Test that DeploymentManager correctly processes dynamic capabilities."""
    print("Testing DeploymentManager Dynamic Capabilities Integration")
    print("=" * 80)
    
    # Initialize services
    version_manager = VersionManager()
    validator = ContentValidator()
    deployment_manager = DeploymentManager(version_manager, validator)
    
    # Test 1: Check if deployment manager processes placeholders
    print("\n1. Testing placeholder processing in deployment...")
    
    # Create test content that matches validation requirements
    test_content = """<!-- CLAUDE_MD_VERSION: 0006 -->
<!-- FRAMEWORK_VERSION: 0006 -->
<!-- LAST_MODIFIED: 2025-01-27T00:00:00Z -->

# Claude Multi-Agent Project Manager Instructions

## Version Metadata
CLAUDE_MD_VERSION: 0006

## Core Identity & Authority
You are Claude-PM, a Project Manager specialized in multi-agent coordination.

## Role Designation & Expertise
This is the role designation section.

## Agent Names & Capabilities
{{capabilities-list}}

## Enhanced Task Delegation Format
Task delegation section.

## Todo/Task Tools
Todo and task tools section.

## Claude-PM Init
Initialization section.

## Core Responsibilities
Core responsibilities section.

## Critical Orchestration Principles
Orchestration principles section.

## Subprocess Validation
Subprocess validation section.

## Delegation Constraints
Delegation constraints section.

## Troubleshooting Guide
Troubleshooting section.
"""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test deployment
        success, message = deployment_manager.deploy_to_parent(test_content, temp_path, force=True)
        
        print(f"   Deployment result: {success}")
        print(f"   Message: {message}")
        
        if success:
            # Check deployed file
            deployed_file = temp_path / "INSTRUCTIONS.md"
            if deployed_file.exists():
                with open(deployed_file, 'r') as f:
                    deployed_content = f.read()
                
                # Check if placeholder was replaced
                if "{{capabilities-list}}" in deployed_content:
                    print("   ✗ Placeholder not replaced during deployment")
                else:
                    print("   ✓ Placeholder replaced during deployment")
                    
                    # Check for dynamic content
                    if "**Core Agents**:" in deployed_content:
                        print("   ✓ Dynamic content generated and inserted")
                    else:
                        print("   ✗ Dynamic content not found")
            else:
                print("   ✗ Deployed file not found")
        else:
            print("   ✗ Deployment failed")
    
    # Test 2: Test processing with ContentAssembler directly
    print("\n2. Testing ContentAssembler processing...")
    assembler = ContentAssembler()
    
    simple_content = "Before {{capabilities-list}} After"
    processed = assembler.apply_template_variables(simple_content)
    
    if "{{capabilities-list}}" not in processed and "**Core Agents**:" in processed:
        print("   ✓ ContentAssembler correctly processes placeholders")
    else:
        print("   ✗ ContentAssembler failed to process placeholders")
    
    # Test 3: Test deployment manager's process_content method
    print("\n3. Testing DeploymentManager's content processing...")
    
    # Check if deployment manager has process_content or similar method
    if hasattr(deployment_manager, 'process_content'):
        processed = deployment_manager.process_content(test_content)
        if "{{capabilities-list}}" not in processed:
            print("   ✓ DeploymentManager processes content before deployment")
        else:
            print("   ✗ DeploymentManager doesn't process placeholders")
    else:
        print("   - DeploymentManager doesn't have explicit process_content method")
        print("   - Processing happens during deployment")


if __name__ == "__main__":
    test_deployment_manager_processing()