#!/usr/bin/env python3
"""Test agent deployment and verify schema compliance.

This script validates that agent deployment correctly maps fields from JSON
templates to YAML files, ensuring schema compliance and proper data transformation.

OPERATIONAL PURPOSE:
Validation script for the agent deployment pipeline. Ensures that JSON to YAML
transformation preserves all critical agent configuration and that deployed
agents are discoverable and functional in Claude Code.

TEST SCENARIOS COVERED:
1. Agent deployment to a temporary directory
2. YAML frontmatter parsing and validation
3. Field mapping verification between JSON templates and deployed YAML
4. Tools field mapping validation
5. Description and tags field mapping
6. Instruction content preservation
7. Deployment statistics reporting

TEST FOCUS:
- Verifies that the deployment process correctly transforms JSON agent templates
  into YAML files with proper frontmatter
- Validates that essential fields are properly mapped
- Checks that agent-specific configurations are preserved
- Ensures instructions are included in the deployed files

TEST COVERAGE GAPS:
- No testing of allowed_tools/disallowed_tools mapping
- No testing of temperature and model field mapping
- No testing of priority field assignment
- No validation of YAML syntax correctness
- No testing of deployment update scenarios
- No testing of version field handling

OPERATIONAL USAGE:
1. Pre-deployment validation: Run before production deployments
2. Post-deployment verification: Confirm successful deployment
3. Troubleshooting: Identify field mapping issues
4. CI/CD integration: Include in automated test suites

MONITORING POINTS:
- Field mapping success rate (should be 100%)
- Deployment completion time
- YAML parsing errors
- Missing instructions or tools

TROUBLESHOOTING GUIDE:
- YAML parse errors: Check for special characters in JSON
- Missing fields: Verify JSON template structure
- Empty tools: Check capabilities.tools in template
- Failed deployment: Check file permissions
"""

import json
import sys
from pathlib import Path
import tempfile
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)

def parse_yaml_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content.
    
    Parses content that follows the YAML frontmatter format:
    ---
    key: value
    ---
    
    OPERATIONAL NOTES:
    - Critical for validating deployed agent configuration
    - Must handle edge cases like missing frontmatter gracefully
    - Returns empty dict rather than failing to support validation flow
    - Used by Claude Code to discover agent capabilities
    
    COMMON ISSUES:
    - Special characters in values need proper escaping
    - Multi-line values require correct YAML formatting
    - Empty frontmatter should return empty dict, not error
    
    Args:
        content: File content with YAML frontmatter
        
    Returns:
        Dictionary of parsed YAML frontmatter, empty dict if no frontmatter found
    """
    if not content.startswith('---'):
        return {}
    
    # Find the end of frontmatter
    end_idx = content.find('---', 3)
    if end_idx == -1:
        return {}
    
    yaml_content = content[3:end_idx].strip()
    return yaml.safe_load(yaml_content)

def main():
    """Run deployment test and verify field mapping.
    
    This is the main test function that:
    1. Creates a temporary deployment directory
    2. Deploys agents using AgentDeploymentService
    3. Verifies specific agents (qa, engineer) were deployed correctly
    4. Compares JSON template data with deployed YAML frontmatter
    5. Reports on field mapping accuracy
    
    The test focuses on validating that the deployment process correctly
    transforms agent data from JSON templates to YAML format while
    preserving essential fields and configurations.
    
    OPERATIONAL WORKFLOW:
    1. Setup: Create isolated test environment
    2. Deploy: Run full deployment pipeline
    3. Validate: Check each agent for correctness
    4. Report: Provide detailed validation results
    
    SUCCESS CRITERIA:
    - All agents deploy without errors
    - YAML frontmatter is valid and parseable
    - Essential fields (name, tools, description) are mapped
    - Instructions are preserved in agent body
    - No data loss during transformation
    
    FAILURE MODES:
    - Deployment errors: Check permissions and paths
    - Parsing errors: Validate JSON template syntax
    - Missing fields: Review field mapping logic
    - Empty content: Check template loading
    
    PERFORMANCE EXPECTATIONS:
    - Total execution time: < 2 seconds
    - Per-agent validation: < 100ms
    - Memory usage: < 50MB
    """
    print("Testing agent deployment and schema compliance...\n")
    
    # Create a temporary deployment directory
    with tempfile.TemporaryDirectory() as temp_dir:
        target_dir = Path(temp_dir) / ".claude" / "agents"
        
        # Initialize deployment service
        deployment_service = AgentDeploymentService()
        
        # Deploy agents
        print(f"Deploying agents to: {target_dir}")
        results = deployment_service.deploy_agents(target_dir=target_dir, force_rebuild=True)
        
        print(f"\nDeployment results:")
        print(f"  - Deployed: {len(results['deployed'])}")
        print(f"  - Updated: {len(results['updated'])}")
        print(f"  - Skipped: {len(results['skipped'])}")
        print(f"  - Errors: {len(results['errors'])}")
        
        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")
        
        # Verify deployed agents
        print("\n\nVerifying deployed agents against schema...")
        print("-" * 50)
        
        # Check specific agents
        agents_to_check = ['qa', 'engineer']
        
        for agent_name in agents_to_check:
            agent_file = target_dir / f"{agent_name}.md"
            
            if not agent_file.exists():
                print(f"\n❌ {agent_name}.md not found!")
                continue
            
            print(f"\n✅ Found {agent_name}.md")
            
            # Read the deployed content
            content = agent_file.read_text()
            
            # Parse YAML frontmatter
            frontmatter = parse_yaml_frontmatter(content)
            
            # Read the original template
            template_path = deployment_service.templates_dir / f"{agent_name}.json"
            if template_path.exists():
                template_data = json.loads(template_path.read_text())
                
                print(f"\nComparing {agent_name} template vs deployed:")
                print("-" * 30)
                
                # Check tools mapping
                template_tools = template_data.get('capabilities', {}).get('tools', [])
                deployed_tools = frontmatter.get('tools', [])
                
                print(f"Tools:")
                print(f"  Template: {template_tools}")
                print(f"  Deployed: {deployed_tools}")
                print(f"  Match: {'✅' if template_tools == deployed_tools else '❌'}")
                
                # Check other capabilities
                capabilities = template_data.get('capabilities', {})
                
                # Check model (note: model is not in frontmatter by default)
                print(f"\nModel:")
                print(f"  Template: {capabilities.get('model', 'Not specified')}")
                print(f"  Deployed: Not in frontmatter (expected)")
                
                # Check temperature (note: temperature is not in frontmatter by default)
                print(f"\nTemperature:")
                print(f"  Template: {capabilities.get('temperature', 'Not specified')}")
                print(f"  Deployed: Not in frontmatter (expected)")
                
                # Check description
                template_desc = template_data.get('metadata', {}).get('description', '')
                deployed_desc = frontmatter.get('description', '')
                
                print(f"\nDescription:")
                print(f"  Template: {template_desc}")
                print(f"  Deployed: {deployed_desc}")
                print(f"  Match: {'✅' if template_desc == deployed_desc else '❌'}")
                
                # Check tags
                template_tags = template_data.get('metadata', {}).get('tags', [])
                deployed_tags = frontmatter.get('tags', [])
                
                print(f"\nTags:")
                print(f"  Template: {template_tags}")
                print(f"  Deployed: {deployed_tags}")
                print(f"  Match: {'✅' if template_tags == deployed_tags else '❌'}")
                
                # Check instructions
                template_instructions = template_data.get('instructions', '')
                # Extract instructions from content (after frontmatter)
                instructions_start = content.find('---', 3) + 3
                deployed_instructions = content[instructions_start:].strip()
                
                print(f"\nInstructions:")
                print(f"  Template length: {len(template_instructions)} chars")
                print(f"  Deployed length: {len(deployed_instructions)} chars")
                print(f"  Instructions present: {'✅' if len(deployed_instructions) > 100 else '❌'}")
                
                # Show a snippet of the deployed content
                print(f"\nDeployed content snippet:")
                print("-" * 30)
                print(content[:500] + "..." if len(content) > 500 else content)

if __name__ == "__main__":
    main()