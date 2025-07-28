#!/usr/bin/env python3
"""Test QA agent script access permissions"""

import os
import sys
import yaml
import json

def test_qa_agent_permissions():
    """Test that QA agent has proper script access permissions"""
    
    # Load QA agent YAML configuration
    qa_yaml_path = os.path.join(os.path.dirname(__file__), '..', '.claude', 'agents', 'qa.yaml')
    
    if not os.path.exists(qa_yaml_path):
        print(f"❌ QA agent YAML not found at {qa_yaml_path}")
        return False
        
    with open(qa_yaml_path, 'r') as f:
        content = f.read()
        
    # Split by --- to get front matter
    parts = content.split('---')
    if len(parts) < 3:  # Should have at least 3 parts: front matter, separator, content
        print("❌ Invalid YAML format")
        return False
        
    # Parse the front matter (second part after first ---)
    try:
        config = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        print(f"❌ Failed to parse YAML: {e}")
        return False
        
    # Check for allowed_tools
    if 'allowed_tools' not in config:
        print("❌ No allowed_tools configuration found")
        return False
        
    allowed_tools = config['allowed_tools']
    
    # Parse the JSON-formatted allowed_tools
    if isinstance(allowed_tools, str):
        try:
            allowed_tools = json.loads(allowed_tools)
        except json.JSONDecodeError:
            print("❌ Failed to parse allowed_tools JSON")
            return False
            
    print("✅ QA Agent allowed_tools configuration:")
    
    # Check Edit permissions
    if 'Edit' in allowed_tools:
        print("\n📝 Edit permissions:")
        for pattern in allowed_tools['Edit']:
            print(f"  - {pattern}")
            
        # Verify scripts patterns are present
        script_patterns = [p for p in allowed_tools['Edit'] if 'scripts/' in p]
        if script_patterns:
            print(f"\n✅ QA agent can edit {len(script_patterns)} script patterns")
        else:
            print("\n❌ QA agent cannot edit scripts")
            
    # Check Write permissions
    if 'Write' in allowed_tools:
        print("\n✏️  Write permissions:")
        for pattern in allowed_tools['Write']:
            print(f"  - {pattern}")
            
        # Verify scripts patterns are present
        script_patterns = [p for p in allowed_tools['Write'] if 'scripts/' in p]
        if script_patterns:
            print(f"\n✅ QA agent can write {len(script_patterns)} script patterns")
        else:
            print("\n❌ QA agent cannot write scripts")
            
    # Check file_access write_paths in JSON template
    qa_json_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'claude_mpm', 'agents', 'templates', 'qa.json')
    
    if os.path.exists(qa_json_path):
        with open(qa_json_path, 'r') as f:
            qa_template = json.load(f)
            
        if 'capabilities' in qa_template and 'file_access' in qa_template['capabilities']:
            write_paths = qa_template['capabilities']['file_access'].get('write_paths', [])
            print(f"\n📁 File access write paths from JSON template:")
            for path in write_paths:
                print(f"  - {path}")
                
            if './scripts/' in write_paths:
                print("\n✅ QA agent has scripts directory write access")
            else:
                print("\n❌ QA agent lacks scripts directory write access")
                
    return True


if __name__ == "__main__":
    print("Testing QA agent script access permissions...\n")
    
    if test_qa_agent_permissions():
        print("\n✅ QA agent configuration test passed!")
        sys.exit(0)
    else:
        print("\n❌ QA agent configuration test failed!")
        sys.exit(1)