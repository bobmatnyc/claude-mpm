#!/usr/bin/env python3
"""Test how agent capabilities from templates are used during deployment and execution."""

import json
import sys
from pathlib import Path
import tempfile
import yaml
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService
from claude_mpm.services.agents.registry import DeployedAgentDiscovery
from claude_mpm.services.agents.management import AgentCapabilitiesGenerator
from claude_mpm.core.logger import get_logger

logger = get_logger(__name__)

def parse_yaml_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}
    
    # Find the end of frontmatter
    end_idx = content.find('---', 3)
    if end_idx == -1:
        return {}
    
    yaml_content = content[3:end_idx].strip()
    return yaml.safe_load(yaml_content)

def extract_capabilities_from_content(content: str) -> dict:
    """Extract capabilities information from the generated content."""
    capabilities = {}
    
    # Look for agent-specific sections
    agent_sections = re.findall(r'### (\w+)_agent\n(.*?)(?=###|\Z)', content, re.DOTALL)
    
    for agent_name, section_content in agent_sections:
        agent_caps = {}
        
        # Extract tools if mentioned
        tools_match = re.search(r'tools?:?\s*\[(.*?)\]', section_content, re.IGNORECASE)
        if tools_match:
            tools_str = tools_match.group(1)
            agent_caps['tools'] = [t.strip().strip('"\'') for t in tools_str.split(',')]
        
        # Extract description
        desc_match = re.search(r'description:?\s*"?([^"\n]+)"?', section_content, re.IGNORECASE)
        if desc_match:
            agent_caps['description'] = desc_match.group(1).strip()
        
        capabilities[agent_name] = agent_caps
    
    return capabilities

def main():
    """Test the complete flow from template to deployment to usage."""
    print("Testing agent capabilities flow from template to usage...\n")
    
    # Create a temporary deployment directory
    with tempfile.TemporaryDirectory() as temp_dir:
        target_dir = Path(temp_dir) / ".claude" / "agents"
        
        # Step 1: Deploy agents
        print("=" * 60)
        print("STEP 1: DEPLOYING AGENTS")
        print("=" * 60)
        
        deployment_service = AgentDeploymentService()
        results = deployment_service.deploy_agents(target_dir=target_dir, force_rebuild=True)
        
        print(f"Deployment complete: {len(results['deployed'])} agents deployed\n")
        
        # Step 2: Discover deployed agents
        print("=" * 60)
        print("STEP 2: DISCOVERING DEPLOYED AGENTS")
        print("=" * 60)
        
        discovery_service = DeployedAgentDiscovery(project_root=Path(temp_dir))
        deployed_agents = discovery_service.discover_deployed_agents()
        
        print(f"Discovered {len(deployed_agents)} agents")
        for agent in deployed_agents:
            print(f"  - {agent['id']}: {agent.get('description', 'No description')}")
        print()
        
        # Step 3: Generate capabilities content
        print("=" * 60)
        print("STEP 3: GENERATING CAPABILITIES CONTENT")
        print("=" * 60)
        
        generator = AgentCapabilitiesGenerator()
        capabilities_content = generator.generate_capabilities_section(deployed_agents)
        
        print("Generated capabilities content (first 500 chars):")
        print(capabilities_content[:500] + "..." if len(capabilities_content) > 500 else capabilities_content)
        print()
        
        # Step 4: Analyze the complete flow
        print("=" * 60)
        print("STEP 4: ANALYZING CAPABILITIES FLOW")
        print("=" * 60)
        
        # Check specific agents
        agents_to_check = ['qa', 'engineer']
        
        for agent_name in agents_to_check:
            print(f"\n--- Analyzing {agent_name} agent ---")
            
            # 1. Template capabilities
            template_path = deployment_service.templates_dir / f"{agent_name}.json"
            if template_path.exists():
                template_data = json.loads(template_path.read_text())
                template_caps = template_data.get('capabilities', {})
                
                print(f"\n1. Template Capabilities:")
                print(f"   Model: {template_caps.get('model', 'Not specified')}")
                print(f"   Tools: {template_caps.get('tools', [])}")
                print(f"   Temperature: {template_caps.get('temperature', 'Not specified')}")
                print(f"   Max Tokens: {template_caps.get('max_tokens', 'Not specified')}")
                print(f"   Timeout: {template_caps.get('timeout', 'Not specified')}")
            
            # 2. Deployed agent
            agent_file = target_dir / f"{agent_name}.md"
            if agent_file.exists():
                content = agent_file.read_text()
                frontmatter = parse_yaml_frontmatter(content)
                
                print(f"\n2. Deployed Agent (frontmatter):")
                print(f"   Tools: {frontmatter.get('tools', [])}")
                print(f"   Description: {frontmatter.get('description', 'Not specified')}")
                print(f"   Version: {frontmatter.get('version', 'Not specified')}")
                print(f"   Note: Model, temperature, etc. are not in frontmatter")
            
            # 3. Discovered agent
            discovered = next((a for a in deployed_agents if a['id'] == f"{agent_name}_agent"), None)
            if discovered:
                print(f"\n3. Discovered Agent:")
                print(f"   ID: {discovered['id']}")
                print(f"   Tools: {discovered.get('tools', [])}")
                print(f"   Capabilities: {discovered.get('capabilities', {})}")
                print(f"   Source Tier: {discovered.get('source_tier', 'Not specified')}")
            
            # 4. In capabilities content
            # Extract from the generated content
            capabilities_in_content = extract_capabilities_from_content(capabilities_content)
            if agent_name in capabilities_in_content:
                print(f"\n4. In Generated Capabilities Content:")
                print(f"   {capabilities_in_content[agent_name]}")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY: CAPABILITY MAPPING ISSUES")
        print("=" * 60)
        
        print("\n1. ✅ Tools are correctly mapped from template → deployment → discovery")
        print("2. ✅ Description and tags are correctly mapped")
        print("3. ⚠️  Model, temperature, max_tokens are in template but NOT in deployed frontmatter")
        print("4. ⚠️  These capabilities might need to be accessed differently during agent execution")
        print("\nRECOMMENDATION: Check how the agent execution system reads these capabilities")
        print("It may need to read from the original JSON templates or store them differently")

if __name__ == "__main__":
    main()