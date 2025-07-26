#!/usr/bin/env python3
"""Integration test for agent loader fix."""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.agents.agent_loader import (
    get_agent_prompt,
    get_qa_agent_prompt,
    list_available_agents,
    validate_agent_files
)


def test_agent_loading():
    """Test that agent loading works with JSON templates."""
    print("=== Testing Agent Loader Integration ===\n")
    
    # Test 1: List available agents
    print("1. Available agents:")
    agents = list_available_agents()
    for name, info in agents.items():
        print(f"   - {name}: {'✓' if info['has_template'] else '✗'} {info.get('json_file', 'N/A')}")
    print()
    
    # Test 2: Validate agent files
    print("2. Validating agent files:")
    validation = validate_agent_files()
    all_valid = True
    for name, result in validation.items():
        exists = result['template_exists']
        print(f"   - {name}: {'✓' if exists else '✗'}")
        if not exists:
            all_valid = False
    print(f"   All templates exist: {'✓' if all_valid else '✗'}")
    print()
    
    # Test 3: Load specific agents
    print("3. Loading specific agents:")
    test_agents = ['qa', 'research', 'engineer', 'documentation']
    
    for agent_name in test_agents:
        try:
            prompt = get_agent_prompt(agent_name)
            if prompt:
                # Check for expected content
                has_header = '#' in prompt
                has_content = len(prompt) > 100
                print(f"   - {agent_name}: ✓ (length: {len(prompt)}, has_header: {has_header})")
            else:
                print(f"   - {agent_name}: ✗ (no content)")
        except Exception as e:
            print(f"   - {agent_name}: ✗ (error: {e})")
    print()
    
    # Test 4: Test backward-compatible functions
    print("4. Testing backward-compatible functions:")
    try:
        qa_prompt = get_qa_agent_prompt()
        print(f"   - get_qa_agent_prompt(): ✓ (length: {len(qa_prompt)})")
    except Exception as e:
        print(f"   - get_qa_agent_prompt(): ✗ (error: {e})")
    print()
    
    # Test 5: Test with model info
    print("5. Testing model selection:")
    try:
        prompt, model, config = get_agent_prompt('qa', return_model_info=True)
        print(f"   - Agent: qa")
        print(f"   - Model: {model}")
        print(f"   - Selection method: {config.get('selection_method', 'unknown')}")
    except Exception as e:
        print(f"   - Error: {e}")
    print()
    
    # Test 6: Check specific content from templates
    print("6. Verifying content extraction:")
    try:
        # Load QA agent and check for expected content
        qa_prompt = get_agent_prompt('qa')
        
        # Check for content that should be in the QA agent prompt
        expected_phrases = [
            "QA Agent",
            "quality",
            "testing",
            "validation"
        ]
        
        found_phrases = []
        missing_phrases = []
        
        for phrase in expected_phrases:
            if phrase.lower() in qa_prompt.lower():
                found_phrases.append(phrase)
            else:
                missing_phrases.append(phrase)
        
        print(f"   - Found phrases: {', '.join(found_phrases) if found_phrases else 'None'}")
        print(f"   - Missing phrases: {', '.join(missing_phrases) if missing_phrases else 'None'}")
        print(f"   - Content extraction: {'✓' if not missing_phrases else '✗'}")
    except Exception as e:
        print(f"   - Error checking content: {e}")
    
    print("\n=== Integration Test Complete ===")


if __name__ == "__main__":
    test_agent_loading()