#!/usr/bin/env python3
"""Test edge cases for agent loader fix."""

import sys
import os
import json
import tempfile

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.agents.agent_loader import load_agent_prompt_from_md


def test_edge_cases():
    """Test edge cases and error scenarios."""
    print("=== Testing Agent Loader Edge Cases ===\n")
    
    # Test 1: Non-existent agent
    print("1. Testing non-existent agent:")
    try:
        content = load_agent_prompt_from_md("non_existent_agent")
        print(f"   Result: {content}")
        print(f"   Status: {'✓' if content is None else '✗'} (should be None)")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Test 2: Malformed JSON
    print("2. Testing malformed JSON:")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create malformed JSON
        bad_json_path = os.path.join(tmpdir, "bad_agent.json")
        with open(bad_json_path, 'w') as f:
            f.write('{ "invalid": json content }')
        
        # Mock the loader
        import claude_mpm.agents.agent_loader as loader
        original_mappings = loader.AGENT_MAPPINGS
        original_dir = loader.AGENT_TEMPLATES_DIR
        
        try:
            loader.AGENT_MAPPINGS = {"bad": "bad_agent.json"}
            loader.AGENT_TEMPLATES_DIR = tmpdir
            
            content = load_agent_prompt_from_md("bad", force_reload=True)
            print(f"   Result: {content}")
            print(f"   Status: ✓ (gracefully handled)")
        except Exception as e:
            print(f"   Error: {e}")
            print(f"   Status: ✓ (error caught)")
        finally:
            loader.AGENT_MAPPINGS = original_mappings
            loader.AGENT_TEMPLATES_DIR = original_dir
    print()
    
    # Test 3: Empty JSON file
    print("3. Testing empty JSON file:")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty JSON
        empty_json_path = os.path.join(tmpdir, "empty_agent.json")
        with open(empty_json_path, 'w') as f:
            json.dump({}, f)
        
        # Mock the loader
        import claude_mpm.agents.agent_loader as loader
        original_mappings = loader.AGENT_MAPPINGS
        original_dir = loader.AGENT_TEMPLATES_DIR
        
        try:
            loader.AGENT_MAPPINGS = {"empty": "empty_agent.json"}
            loader.AGENT_TEMPLATES_DIR = tmpdir
            
            content = load_agent_prompt_from_md("empty", force_reload=True)
            print(f"   Result: {content}")
            print(f"   Status: {'✓' if content is None else '✗'} (should be None)")
        finally:
            loader.AGENT_MAPPINGS = original_mappings
            loader.AGENT_TEMPLATES_DIR = original_dir
    print()
    
    # Test 4: Nested narrative_fields with missing instructions
    print("4. Testing nested narrative_fields without instructions:")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create JSON with narrative_fields but no instructions
        test_json = {
            "narrative_fields": {
                "when_to_use": ["test"],
                "specialized_knowledge": ["test"]
                # No instructions field
            }
        }
        
        json_path = os.path.join(tmpdir, "no_instructions.json")
        with open(json_path, 'w') as f:
            json.dump(test_json, f)
        
        # Mock the loader
        import claude_mpm.agents.agent_loader as loader
        original_mappings = loader.AGENT_MAPPINGS
        original_dir = loader.AGENT_TEMPLATES_DIR
        
        try:
            loader.AGENT_MAPPINGS = {"no_instructions": "no_instructions.json"}
            loader.AGENT_TEMPLATES_DIR = tmpdir
            
            content = load_agent_prompt_from_md("no_instructions", force_reload=True)
            print(f"   Result: {content}")
            print(f"   Status: {'✓' if content is None else '✗'} (should be None)")
        finally:
            loader.AGENT_MAPPINGS = original_mappings
            loader.AGENT_TEMPLATES_DIR = original_dir
    print()
    
    # Test 5: Empty string content
    print("5. Testing empty string content:")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create JSON with empty string content
        test_json = {
            "narrative_fields": {
                "instructions": ""  # Empty string
            }
        }
        
        json_path = os.path.join(tmpdir, "empty_string.json")
        with open(json_path, 'w') as f:
            json.dump(test_json, f)
        
        # Mock the loader
        import claude_mpm.agents.agent_loader as loader
        original_mappings = loader.AGENT_MAPPINGS
        original_dir = loader.AGENT_TEMPLATES_DIR
        
        try:
            loader.AGENT_MAPPINGS = {"empty_string": "empty_string.json"}
            loader.AGENT_TEMPLATES_DIR = tmpdir
            
            content = load_agent_prompt_from_md("empty_string", force_reload=True)
            print(f"   Result: '{content}'")
            print(f"   Status: {'✓' if content is None else '✗'} (should be None for empty string)")
        finally:
            loader.AGENT_MAPPINGS = original_mappings
            loader.AGENT_TEMPLATES_DIR = original_dir
    print()
    
    # Test 6: Unicode content
    print("6. Testing Unicode content:")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create JSON with Unicode content
        test_json = {
            "narrative_fields": {
                "instructions": "# Test Agent 🚀\n\nThis agent handles Unicode: ñ, é, 中文, 日本語"
            }
        }
        
        json_path = os.path.join(tmpdir, "unicode.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(test_json, f, ensure_ascii=False)
        
        # Mock the loader
        import claude_mpm.agents.agent_loader as loader
        original_mappings = loader.AGENT_MAPPINGS
        original_dir = loader.AGENT_TEMPLATES_DIR
        
        try:
            loader.AGENT_MAPPINGS = {"unicode": "unicode.json"}
            loader.AGENT_TEMPLATES_DIR = tmpdir
            
            content = load_agent_prompt_from_md("unicode", force_reload=True)
            print(f"   Result length: {len(content) if content else 0}")
            print(f"   Contains emoji: {'🚀' in content if content else False}")
            print(f"   Contains Chinese: {'中文' in content if content else False}")
            print(f"   Status: {'✓' if content and '🚀' in content else '✗'}")
        finally:
            loader.AGENT_MAPPINGS = original_mappings
            loader.AGENT_TEMPLATES_DIR = original_dir
    
    print("\n=== Edge Case Testing Complete ===")


if __name__ == "__main__":
    test_edge_cases()