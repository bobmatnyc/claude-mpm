#!/usr/bin/env python3
"""Check which agents were filtered out."""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.core.config import Config
from claude_mpm.services.agents.deployment.agent_discovery_service import AgentDiscoveryService

def main():
    config = Config()
    templates_dir = Path("src/claude_mpm/agents/templates")
    discovery_service = AgentDiscoveryService(templates_dir)
    
    # Get all templates and MPM templates
    all_templates = discovery_service.get_filtered_templates([], config, filter_non_mpm=False)
    mpm_templates = discovery_service.get_filtered_templates([], config, filter_non_mpm=True)
    
    # Find which ones were filtered
    all_names = {t.stem for t in all_templates}
    mpm_names = {t.stem for t in mpm_templates}
    filtered_names = all_names - mmp_names
    
    print("Agents filtered out (non-MPM):")
    for name in sorted(filtered_names):
        template_path = templates_dir / f"{name}.json"
        is_mpm = discovery_service._is_mpm_agent(template_path, config)
        print(f"  - {name} (verified non-MPM: {not is_mpm})")

if __name__ == "__main__":
    main()