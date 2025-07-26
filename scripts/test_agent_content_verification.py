#!/usr/bin/env python3
"""Verify agent content is properly loaded from JSON templates."""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.agents import (
    get_qa_agent_prompt,
    get_research_agent_prompt,
    get_engineer_agent_prompt,
    get_documentation_agent_prompt,
    get_version_control_agent_prompt,
    get_ops_agent_prompt,
    get_security_agent_prompt,
    get_data_engineer_agent_prompt
)


def verify_agent_content():
    """Verify each agent loads with expected content."""
    print("=== Verifying Agent Content from JSON Templates ===\n")
    
    agents = {
        'QA': (get_qa_agent_prompt, ['QA Agent', 'testing', 'quality', 'validation']),
        'Research': (get_research_agent_prompt, ['Research Agent', 'information', 'data', 'analysis']),
        'Engineer': (get_engineer_agent_prompt, ['Engineer Agent', 'implementation', 'code', 'development']),
        'Documentation': (get_documentation_agent_prompt, ['Documentation Agent', 'documentation', 'guide', 'clarity']),
        'Version Control': (get_version_control_agent_prompt, ['Version Control Agent', 'git', 'commit', 'branch']),
        'Ops': (get_ops_agent_prompt, ['Ops Agent', 'deployment', 'infrastructure', 'monitoring']),
        'Security': (get_security_agent_prompt, ['Security Agent', 'security', 'vulnerability', 'protection']),
        'Data Engineer': (get_data_engineer_agent_prompt, ['Data Engineer Agent', 'data', 'pipeline', 'etl'])
    }
    
    all_passed = True
    
    for agent_name, (loader_func, expected_terms) in agents.items():
        print(f"Testing {agent_name} Agent:")
        try:
            # Load agent prompt
            prompt = loader_func()
            
            # Check basic validity
            if not prompt:
                print(f"  ✗ No content returned")
                all_passed = False
                continue
                
            print(f"  ✓ Loaded successfully (length: {len(prompt)})")
            
            # Check for expected terms
            missing_terms = []
            for term in expected_terms:
                if term.lower() not in prompt.lower():
                    missing_terms.append(term)
            
            if missing_terms:
                print(f"  ✗ Missing expected terms: {', '.join(missing_terms)}")
                all_passed = False
            else:
                print(f"  ✓ Contains all expected terms")
                
            # Extract a snippet to verify content
            lines = prompt.split('\n')
            content_lines = [line for line in lines if line.strip() and not line.startswith('<!--')]
            if content_lines:
                snippet = content_lines[0][:80] + '...' if len(content_lines[0]) > 80 else content_lines[0]
                print(f"  • First line: {snippet}")
            
        except Exception as e:
            print(f"  ✗ Error loading agent: {e}")
            all_passed = False
        
        print()
    
    print("=== Summary ===")
    print(f"All agents loaded successfully: {'✓' if all_passed else '✗'}")
    return all_passed


if __name__ == "__main__":
    success = verify_agent_content()
    sys.exit(0 if success else 1)