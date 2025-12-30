#!/usr/bin/env python3
"""
Invert skill_to_agent_mapping.yaml to generate agent → skills mappings.

This script reads the static YAML mapping and outputs which skills each agent should have
in their frontmatter.
"""

import yaml
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set

def load_mapping(yaml_path: Path) -> Dict:
    """Load the skill mapping YAML file."""
    with open(yaml_path) as f:
        return yaml.safe_load(f)

def convert_skill_path_to_name(skill_path: str) -> str:
    """Convert skill path to hyphen-separated name.

    Examples:
        toolchains/python/frameworks/django -> toolchains-python-frameworks-django
        universal/debugging/systematic-debugging -> universal-debugging-systematic-debugging
    """
    return skill_path.replace('/', '-')

def invert_mapping(config: Dict) -> Dict[str, List[str]]:
    """Invert the mapping from skill → agents to agent → skills.

    Returns:
        Dict mapping agent_id to list of skill names (hyphen-separated format)
    """
    agent_skills = defaultdict(set)

    # Get skill mappings
    skill_mappings = config.get('skill_mappings', {})
    all_agents_list = config.get('all_agents_list', [])

    for skill_path, agents in skill_mappings.items():
        skill_name = convert_skill_path_to_name(skill_path)

        # Handle ALL_AGENTS marker
        if agents == ['ALL_AGENTS']:
            for agent in all_agents_list:
                agent_skills[agent].add(skill_name)
        else:
            for agent in agents:
                agent_skills[agent].add(skill_name)

    # Convert sets to sorted lists
    return {
        agent: sorted(skills)
        for agent, skills in sorted(agent_skills.items())
    }

def main():
    """Generate and print the inverted mapping."""
    yaml_path = Path(__file__).parent.parent / 'src/claude_mpm/config/skill_to_agent_mapping.yaml'

    print(f"Reading mapping from: {yaml_path}\n")

    config = load_mapping(yaml_path)
    inverted = invert_mapping(config)

    print("=" * 80)
    print("AGENT → SKILLS MAPPING")
    print("=" * 80)
    print()

    total_agents = len(inverted)
    total_skills_assigned = sum(len(skills) for skills in inverted.values())

    for agent, skills in inverted.items():
        print(f"{agent}:")
        print(f"  Skills count: {len(skills)}")
        if len(skills) <= 10:
            # Show all skills if count is small
            for skill in skills:
                print(f"    - {skill}")
        else:
            # Show first 5 and last 5 if count is large
            for skill in skills[:5]:
                print(f"    - {skill}")
            print(f"    ... ({len(skills) - 10} more) ...")
            for skill in skills[-5:]:
                print(f"    - {skill}")
        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total agents: {total_agents}")
    print(f"Total skill assignments: {total_skills_assigned}")
    print(f"Average skills per agent: {total_skills_assigned / total_agents:.1f}")
    print()

    # Find agents with most/least skills
    max_agent = max(inverted.items(), key=lambda x: len(x[1]))
    min_agent = min(inverted.items(), key=lambda x: len(x[1]))

    print(f"Agent with most skills: {max_agent[0]} ({len(max_agent[1])} skills)")
    print(f"Agent with least skills: {min_agent[0]} ({len(min_agent[1])} skills)")
    print()

    # Generate YAML output for reference
    output_path = Path(__file__).parent.parent / 'agent_skill_mappings.yaml'
    with open(output_path, 'w') as f:
        yaml.dump(inverted, f, default_flow_style=False, sort_keys=True)

    print(f"Full mapping written to: {output_path}")

if __name__ == '__main__':
    main()
