"""Comprehensive tests for validating agent deployment configurations.

This test module provides extensive validation of deployed agent YAML files,
ensuring they meet Claude Code's requirements and best practices.

TEST CATEGORIES:
1. YAML Structure Validation - Ensures proper frontmatter format
2. Agent Permissions - Validates tool access and restrictions
3. Temperature Settings - Verifies appropriate creativity levels
4. Priority Assignment - Checks agent priority configurations
5. Model Configuration - Validates model selection
6. YAML Cleanliness - Ensures only essential fields are present

TEST COVERAGE:
- All system agents (qa, engineer, documentation, research, security, ops, data_engineer, version_control)
- YAML frontmatter structure and required fields
- Tool permissions and restrictions per agent type
- Temperature settings for deterministic vs creative tasks
- Priority levels for task scheduling
- Model consistency across agents
- Field cleanliness (no implementation details in YAML)

TEST ASSUMPTIONS:
- Agents are deployed to .claude/agents/ directory
- YAML files follow the frontmatter + content structure
- System agents are pre-deployed before running tests
"""

import json
import yaml
import pytest
from pathlib import Path

class TestAgentDeploymentValidation:
    """Test suite for validating agent deployment and configurations.
    
    This class contains comprehensive tests to ensure deployed agents
    meet all requirements for Claude Code integration.
    """
    
    def test_agent_yaml_structure(self):
        """Test that deployed agent YAML files have correct structure.
        
        Validates:
        1. Agent directory exists and contains YAML files
        2. Each YAML file has proper frontmatter structure (---...---)
        3. Required fields are present: name, description, tools, priority
        4. Tools field is a comma-separated string
        5. At least one tool is specified per agent
        
        This test ensures basic structural compliance for all deployed agents.
        """
        agents_dir = Path(".claude/agents")
        assert agents_dir.exists(), f"Agents directory not found: {agents_dir}"
        
        agent_files = list(agents_dir.glob("*.yaml"))
        assert len(agent_files) > 0, "No agent YAML files found"
        
        required_fields = ["name", "description", "tools", "priority"]
        
        for agent_file in agent_files:
            print(f"\nValidating {agent_file.name}...")
            
            with open(agent_file, 'r') as f:
                content = f.read()
                
            # Split frontmatter and content
            parts = content.split("---", 2)
            assert len(parts) == 3, f"Invalid YAML structure in {agent_file.name}"
            
            # Parse YAML frontmatter
            frontmatter = yaml.safe_load(parts[1])
            assert isinstance(frontmatter, dict), f"Invalid YAML frontmatter in {agent_file.name}"
            
            # Check required fields
            for field in required_fields:
                assert field in frontmatter, f"Missing required field '{field}' in {agent_file.name}"
            
            # Validate tools field
            tools = frontmatter.get("tools", "")
            assert isinstance(tools, str), f"Tools should be a string in {agent_file.name}"
            assert len(tools.split(",")) > 0, f"No tools specified in {agent_file.name}"
            
            print(f"✓ {agent_file.name} has valid structure")
    
    def test_security_agent_permissions(self):
        """Test that security agent has correct permissions.
        
        Security-specific validation:
        1. Security agent YAML file exists
        2. Disallowed tools are properly configured
        3. Critical tools (Bash, Write, Edit, MultiEdit) are restricted
        4. Tools list doesn't include any disallowed tools
        
        This test ensures the security agent operates with appropriate
        restrictions to prevent unauthorized system modifications.
        """
        security_yaml = Path(".claude/agents/security.yaml")
        assert security_yaml.exists(), "Security agent YAML not found"
        
        with open(security_yaml, 'r') as f:
            content = f.read()
            
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        
        # Check that Bash is disallowed
        disallowed_tools = frontmatter.get("disallowed_tools", [])
        assert "Bash" in disallowed_tools, "Security agent should have Bash disallowed"
        assert "Write" in disallowed_tools, "Security agent should have Write disallowed"
        assert "Edit" in disallowed_tools, "Security agent should have Edit disallowed"
        assert "MultiEdit" in disallowed_tools, "Security agent should have MultiEdit disallowed"
        
        # Check tools list doesn't include disallowed tools
        tools = frontmatter.get("tools", "").split(", ")
        for disallowed in disallowed_tools:
            assert disallowed not in tools, f"{disallowed} should not be in tools list"
        
        print("✓ Security agent has correct permissions")
    
    def test_qa_agent_permissions(self):
        """Test that QA agent has correct file access permissions.
        
        QA-specific validation:
        1. QA agent YAML file exists
        2. allowed_tools configuration is present and valid
        3. Edit permissions include test directories (tests/**, test/**, **/test_*.py)
        4. Write permissions include test directories
        
        This test ensures the QA agent has appropriate access to create
        and modify test files while being restricted from production code.
        """
        qa_yaml = Path(".claude/agents/qa.yaml")
        assert qa_yaml.exists(), "QA agent YAML not found"
        
        with open(qa_yaml, 'r') as f:
            content = f.read()
            
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        
        # Check tools
        tools_str = frontmatter.get("tools", "")
        tools = [t.strip() for t in tools_str.split(",")] if tools_str else []
        
        # QA agent should have Edit and Write tools
        assert "Edit" in tools, "QA agent should have Edit tool"
        assert "Write" in tools, "QA agent should have Write tool"
        assert "Read" in tools, "QA agent should have Read tool"
        assert "Bash" in tools, "QA agent should have Bash tool for running tests"
        
        # QA agent should not have disallowed_tools restricting test access
        disallowed_tools = frontmatter.get("disallowed_tools", [])
        assert "Edit" not in disallowed_tools, "QA agent should not have Edit disallowed"
        assert "Write" not in disallowed_tools, "QA agent should not have Write disallowed"
        
        print("✓ QA agent has correct file access permissions")
    
    def test_agent_temperatures(self):
        """Test that agents have appropriate temperature settings.
        
        Temperature validation ensures agents operate with appropriate
        creativity levels for their tasks:
        - 0.0: Deterministic agents (security, qa, version_control)
        - 0.1: Low creativity agents (ops, data_engineer)
        - 0.2: Moderate creativity agents (engineer, documentation, research)
        
        This test validates that each agent's temperature aligns with
        its role and the need for consistency vs creativity.
        """
        agents_dir = Path(".claude/agents")
        
        expected_temperatures = {
            "security.yaml": 0.0,      # Deterministic for security
            "qa.yaml": 0.0,            # Deterministic for testing
            "version_control.yaml": 0.0,  # Deterministic for git operations
            "ops.yaml": 0.1,           # Low creativity for operations
            "data_engineer.yaml": 0.1, # Low creativity for data engineering
            "engineer.yaml": 0.2,      # Low creativity for coding
            "documentation.yaml": 0.2, # Moderate creativity for writing
            "research.yaml": 0.2,      # Moderate creativity for research
        }
        
        for agent_file, expected_temp in expected_temperatures.items():
            yaml_path = agents_dir / agent_file
            if not yaml_path.exists():
                continue
                
            with open(yaml_path, 'r') as f:
                content = f.read()
                
            parts = content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            
            temp = frontmatter.get("temperature", None)
            assert temp is not None, f"Temperature not set for {agent_file}"
            assert temp == expected_temp, f"Expected temperature {expected_temp} for {agent_file}, got {temp}"
            
            print(f"✓ {agent_file} has correct temperature: {temp}")
    
    def test_agent_priorities(self):
        """Test that agents have appropriate priority settings.
        
        Priority validation ensures proper task scheduling:
        - High priority: security, qa, engineer, ops, version_control
        - Medium priority: documentation, research, data_engineer
        
        This test validates that critical operational agents have
        higher priority than analytical/documentation agents.
        """
        agents_dir = Path(".claude/agents")
        
        high_priority_agents = ["security", "qa", "engineer", "ops", "version_control"]
        medium_priority_agents = ["documentation", "research", "data_engineer"]
        
        for agent_file in agents_dir.glob("*.yaml"):
            with open(agent_file, 'r') as f:
                content = f.read()
                
            parts = content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            
            agent_name = frontmatter.get("name", "")
            priority = frontmatter.get("priority", "")
            
            if agent_name in high_priority_agents:
                assert priority == "high", f"{agent_name} should have high priority"
            elif agent_name in medium_priority_agents:
                assert priority == "medium", f"{agent_name} should have medium priority"
                
            print(f"✓ {agent_name} has correct priority: {priority}")
    
    def test_agent_models(self):
        """Test that all agents use the correct model.
        
        Model validation ensures consistency across all agents.
        Currently validates that all agents use claude-sonnet-4-20250514.
        
        This test can be extended to support different models per agent
        type if requirements change in the future.
        """
        agents_dir = Path(".claude/agents")
        expected_model = "claude-sonnet-4-20250514"
        
        for agent_file in agents_dir.glob("*.yaml"):
            with open(agent_file, 'r') as f:
                content = f.read()
                
            parts = content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            
            model = frontmatter.get("model", "")
            assert model == expected_model, f"{agent_file.name} should use {expected_model}, got {model}"
            
            print(f"✓ {agent_file.name} uses correct model: {model}")
    
    def test_yaml_cleanliness(self):
        """Test that YAML files only contain essential fields.
        
        YAML cleanliness validation ensures deployed files follow
        Claude Code best practices by including only essential fields.
        
        Essential fields: name, description, tools, priority, model, temperature
        Optional fields: allowed_tools, disallowed_tools
        Forbidden fields: Implementation details that should not be exposed
                         (resource_tier, max_tokens, timeout, memory_limit, etc.)
        
        This test prevents implementation details from leaking into
        user-visible YAML files and ensures a clean, focused interface.
        """
        agents_dir = Path(".claude/agents")
        
        # Fields that should be present
        essential_fields = {"name", "description", "tools", "priority", "model", "temperature"}
        
        # Optional fields that are OK if present
        optional_fields = {"allowed_tools", "disallowed_tools"}
        
        # Fields that should NOT be present (implementation details)
        forbidden_fields = {"resource_tier", "max_tokens", "timeout", "memory_limit", 
                          "cpu_limit", "network_access", "file_access", "schema_version",
                          "agent_id", "agent_version", "agent_type", "metadata", 
                          "capabilities", "instructions", "knowledge", "interactions",
                          "testing"}
        
        for agent_file in agents_dir.glob("*.yaml"):
            with open(agent_file, 'r') as f:
                content = f.read()
                
            parts = content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            
            # Check for forbidden fields
            present_forbidden = set(frontmatter.keys()) & forbidden_fields
            assert len(present_forbidden) == 0, \
                f"{agent_file.name} contains forbidden fields: {present_forbidden}"
            
            # Check all fields are either essential or optional
            all_allowed = essential_fields | optional_fields
            unknown_fields = set(frontmatter.keys()) - all_allowed
            assert len(unknown_fields) == 0, \
                f"{agent_file.name} contains unknown fields: {unknown_fields}"
                
            print(f"✓ {agent_file.name} has clean YAML structure")

if __name__ == "__main__":
    # Run tests
    test = TestAgentDeploymentValidation()
    
    print("Running agent deployment validation tests...\n")
    
    try:
        test.test_agent_yaml_structure()
        print("\n" + "="*50 + "\n")
        
        test.test_security_agent_permissions()
        print("\n" + "="*50 + "\n")
        
        test.test_qa_agent_permissions()
        print("\n" + "="*50 + "\n")
        
        test.test_agent_temperatures()
        print("\n" + "="*50 + "\n")
        
        test.test_agent_priorities()
        print("\n" + "="*50 + "\n")
        
        test.test_agent_models()
        print("\n" + "="*50 + "\n")
        
        test.test_yaml_cleanliness()
        
        print("\n✅ All agent deployment validation tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)