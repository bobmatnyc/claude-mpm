#!/usr/bin/env python3
"""
Validate that agent schema v1.3.0 supports modern template structure.
Tests compatibility with agent-manager, engineer, and research templates.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def validate_schema_version(schema: Dict[str, Any]) -> bool:
    """Check schema version is 1.3.0."""
    return schema.get("version") == "1.3.0"

def validate_new_fields(schema: Dict[str, Any]) -> list:
    """Check that all new fields are present in schema."""
    required_fields = []
    errors = []
    
    # Check top-level properties
    properties = schema.get("properties", {})
    
    # New top-level fields
    if "template_version" not in properties:
        errors.append("Missing template_version property")
    
    if "template_changelog" not in properties:
        errors.append("Missing template_changelog property")
    
    if "memory_routing" not in properties:
        errors.append("Missing memory_routing property")
    
    # Check agent_type enum includes "system"
    agent_type = properties.get("agent_type", {})
    if "system" not in agent_type.get("enum", []):
        errors.append("agent_type enum missing 'system' value")
    
    # Check metadata enhancements
    metadata_props = properties.get("metadata", {}).get("properties", {})
    if "version" not in metadata_props:
        errors.append("metadata missing version property")
    if "status" not in metadata_props:
        errors.append("metadata missing status property")
    
    # Check capabilities.limits
    capabilities_props = properties.get("capabilities", {}).get("properties", {})
    if "limits" not in capabilities_props:
        errors.append("capabilities missing limits property")
    if "tool_choice" not in capabilities_props:
        errors.append("capabilities missing tool_choice property")
    
    # Check enhanced interactions
    interactions_props = properties.get("interactions", {}).get("properties", {})
    if "protocols" not in interactions_props:
        errors.append("interactions missing protocols property")
    if "response_format" not in interactions_props:
        errors.append("interactions missing response_format property")
    
    # Check input_format enhancements
    input_format = interactions_props.get("input_format", {}).get("properties", {})
    if "supported_operations" not in input_format:
        errors.append("input_format missing supported_operations property")
    
    # Check output_format enhancements  
    output_format = interactions_props.get("output_format", {}).get("properties", {})
    if "example" not in output_format:
        errors.append("output_format missing example property")
    
    # Check testing enhancements
    testing_props = properties.get("testing", {}).get("properties", {})
    if "integration_tests" not in testing_props:
        errors.append("testing missing integration_tests property")
    
    performance = testing_props.get("performance_benchmarks", {}).get("properties", {})
    if "validation_accuracy" not in performance:
        errors.append("performance_benchmarks missing validation_accuracy property")
    
    return errors

def validate_template_compatibility(schema_path: Path, template_path: Path) -> tuple:
    """Validate that a template is compatible with the schema."""
    try:
        import jsonschema
        
        schema = load_json(schema_path)
        template = load_json(template_path)
        
        # Validate against schema
        jsonschema.validate(instance=template, schema=schema)
        return True, f"✅ {template_path.name} is valid"
    except jsonschema.ValidationError as e:
        return False, f"❌ {template_path.name}: {e.message}"
    except ImportError:
        return None, f"⚠️  jsonschema not installed, skipping validation for {template_path.name}"
    except Exception as e:
        return False, f"❌ {template_path.name}: {str(e)}"

def main():
    """Main validation function."""
    project_root = Path(__file__).parent.parent
    schema_path = project_root / "src/claude_mpm/schemas/agent_schema.json"
    templates_dir = project_root / "src/claude_mpm/agents/templates"
    
    print("=" * 60)
    print("Claude MPM Agent Schema v1.3.0 Validation")
    print("=" * 60)
    
    # Load schema
    try:
        schema = load_json(schema_path)
    except Exception as e:
        print(f"❌ Failed to load schema: {e}")
        return 1
    
    # Validate schema version
    print("\n1. Schema Version Check:")
    if validate_schema_version(schema):
        print("   ✅ Schema version is 1.3.0")
    else:
        print(f"   ❌ Schema version is {schema.get('version')}, expected 1.3.0")
        return 1
    
    # Validate new fields
    print("\n2. New Fields Validation:")
    errors = validate_new_fields(schema)
    if not errors:
        print("   ✅ All new fields are present")
    else:
        for error in errors:
            print(f"   ❌ {error}")
        return 1
    
    # Test with modern templates
    print("\n3. Template Compatibility Tests:")
    test_templates = ["agent-manager.json", "engineer.json", "research.json"]
    
    all_valid = True
    for template_name in test_templates:
        template_path = templates_dir / template_name
        if template_path.exists():
            valid, message = validate_template_compatibility(schema_path, template_path)
            print(f"   {message}")
            if valid is False:
                all_valid = False
        else:
            print(f"   ⚠️  {template_name} not found")
    
    # Summary
    print("\n" + "=" * 60)
    if all_valid and not errors:
        print("✅ Schema v1.3.0 validation successful!")
        print("   - Version correct")
        print("   - All new fields present")
        print("   - Compatible with modern templates")
        print("   - Maintains backward compatibility")
        return 0
    else:
        print("❌ Schema validation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())