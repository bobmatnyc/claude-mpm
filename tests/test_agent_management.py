#!/usr/bin/env python3
"""Test agent management functionality for ConfigScreenV2."""

import shutil
import sys
import tempfile
from pathlib import Path

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# NOTE: Manager module and ConfigScreenV2 were removed from the codebase
# These tests are for legacy UI functionality that no longer exists
import pytest

pytest.skip(
    "Manager module and ConfigScreenV2 UI components were removed",
    allow_module_level=True,
)

# Original imports (no longer available):
# from claude_mpm.manager.discovery import Installation
# from claude_mpm.manager.screens.config_screen_v2 import ConfigScreenV2
from claude_mpm.services.agents.deployment import AgentDeploymentService


class MockApp:
    """Mock application for testing."""

    def __init__(self):
        self.dialogs = []
        self.dialog_responses = {}

    def show_dialog(self, title, content):
        self.dialogs.append({"title": title, "content": content})
        print(f"Dialog shown: {title}")

    def close_dialog(self):
        if self.dialogs:
            dialog = self.dialogs.pop()
            print(f"Dialog closed: {dialog['title']}")


def test_agent_deployment_service():
    """Test the agent deployment service functionality."""
    print("Testing Agent Deployment Service...")

    service = AgentDeploymentService()

    # Test listing available agents
    print("Listing available agents...")
    available_agents = service.list_available_agents()

    print(f"Found {len(available_agents)} available agents:")
    for agent_info in available_agents:
        agent_name = agent_info.get("name", "unknown")
        description = agent_info.get("description", "No description")
        print(f"  - {agent_name}: {description}")

    assert len(available_agents) > 0, "Should find some available agents"
    print("✓ Agent listing successful")

    # Test with temporary directory
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)

        # Deploy an agent (if available)
        if available_agents:
            first_agent = available_agents[0]
            agent_name = first_agent.get("name", "unknown")

            print(f"Testing deployment of agent: {agent_name}")

            try:
                result = service.deploy_agent(agent_name, temp_path)
                print(f"✓ Agent deployment result: {result}")

                # Check if agent file was created
                agents_dir = temp_path / ".claude" / "agents"
                if agents_dir.exists():
                    agent_files = (
                        list(agents_dir.glob("*.json"))
                        + list(agents_dir.glob("*.yaml"))
                        + list(agents_dir.glob("*.yml"))
                    )
                    print(f"✓ Found {len(agent_files)} agent files after deployment")
                else:
                    print("! No .claude/agents directory created")

            except Exception as e:
                print(f"Agent deployment failed (expected for some environments): {e}")

    print("Agent deployment service test completed!\n")


def test_install_agents_dialog():
    """Test the install agents dialog functionality."""
    print("Testing Install Agents Dialog...")

    app = MockApp()
    config_screen = ConfigScreenV2(app)
    config_screen.build_widget()  # Initialize main_content

    # Create test installation
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)

        installation = Installation(
            path=temp_path, config={"project": {"name": "test"}}, name=temp_path.name
        )

        config_screen.current_installation = installation

        print("Testing install agents dialog creation...")

        # This should show the install agents dialog
        config_screen._show_agent_install_dialog()

        # Check if dialog was shown
        assert len(app.dialogs) > 0, "Install agents dialog should be shown"
        print("✓ Install agents dialog created")

        # Check dialog content
        dialog = app.dialogs[0]
        assert dialog["title"] == "Install Agents", "Dialog should have correct title"
        print("✓ Dialog has correct title")

    print("Install agents dialog test completed!\n")


def test_import_agents_dialog():
    """Test the import agents dialog functionality."""
    print("Testing Import Agents Dialog...")

    app = MockApp()
    config_screen = ConfigScreenV2(app)
    config_screen.build_widget()  # Initialize main_content

    # Create test installation
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)

        installation = Installation(
            path=temp_path, config={"project": {"name": "test"}}, name=temp_path.name
        )

        config_screen.current_installation = installation

        print("Testing import agents dialog creation...")

        # This should show the import agents dialog
        config_screen._show_agent_import_dialog()

        # Check if dialog was shown
        assert len(app.dialogs) > 0, "Import agents dialog should be shown"
        print("✓ Import agents dialog created")

        # Check dialog content
        dialog = app.dialogs[0]
        assert dialog["title"] == "Import Agent", "Dialog should have correct title"
        print("✓ Dialog has correct title")

    print("Import agents dialog test completed!\n")


def test_agent_import_functionality():
    """Test actual agent import functionality."""
    print("Testing Agent Import Functionality...")

    # Create a temporary agent file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as temp_file:
        test_agent = {
            "name": "test-agent",
            "description": "Test agent for import testing",
            "instructions": "This is a test agent",
        }
        yaml.dump(test_agent, temp_file)
        temp_agent_path = Path(temp_file.name)

    try:
        # Test import to temporary project
        with tmp_path as temp_dir:
            temp_path = Path(temp_dir)

            installation = Installation(
                path=temp_path,
                config={"project": {"name": "test"}},
                name=temp_path.name,
            )

            print(f"Importing agent from: {temp_agent_path}")

            # Manual import test (simulating what the dialog would do)
            target_dir = installation.path / ".claude" / "agents"
            target_dir.mkdir(parents=True, exist_ok=True)

            # Copy agent file
            shutil.copy2(temp_agent_path, target_dir)

            # Verify import
            imported_files = list(target_dir.glob("*.yaml"))
            assert len(imported_files) > 0, "Agent file should be imported"
            print("✓ Agent file imported successfully")

            # Verify content
            with open(imported_files[0]) as f:
                imported_agent = yaml.safe_load(f)

            assert imported_agent["name"] == "test-agent", (
                "Agent content should be preserved"
            )
            print("✓ Agent content preserved during import")

    finally:
        # Clean up temporary agent file
        temp_agent_path.unlink()

    print("Agent import functionality test completed!\n")


def test_error_handling():
    """Test error handling in agent management."""
    print("Testing Error Handling...")

    app = MockApp()
    config_screen = ConfigScreenV2(app)
    config_screen.build_widget()

    class MockButton:
        pass

    button = MockButton()

    # Test without installation selected
    print("Testing error handling without installation...")
    config_screen.current_installation = None

    config_screen._on_install_agents(button)
    config_screen._on_import_agents(button)

    # Should handle gracefully without crashing
    print("✓ Handled missing installation gracefully")

    # Test with global installation
    print("Testing error handling with global installation...")
    global_installation = Installation(
        path=Path("/fake/path"), config={}, name="global", is_global=True
    )

    config_screen.current_installation = global_installation

    config_screen._on_install_agents(button)
    config_screen._on_import_agents(button)

    # Should handle gracefully without crashing
    print("✓ Handled global installation restriction gracefully")

    # Test import with non-existent file
    print("Testing import with non-existent file...")

    # Create non-global installation
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)

        installation = Installation(
            path=temp_path, config={"project": {"name": "test"}}, name=temp_path.name
        )

        config_screen.current_installation = installation

        # This would normally be handled by dialog interaction
        # but we can test the underlying logic
        try:
            non_existent_path = Path("/nonexistent/agent.yaml")
            target_dir = installation.path / ".claude" / "agents"
            target_dir.mkdir(parents=True, exist_ok=True)

            # This should fail gracefully
            if non_existent_path.exists():
                shutil.copy2(non_existent_path, target_dir)
            else:
                print("✓ Non-existent file handled correctly")

        except Exception as e:
            print(f"✓ Exception handled gracefully: {type(e).__name__}")

    print("Error handling test completed!\n")


def main():
    """Run all agent management tests."""
    print("=== ConfigScreenV2 Agent Management Tests ===\n")

    try:
        test_agent_deployment_service()
        test_install_agents_dialog()
        test_import_agents_dialog()
        test_agent_import_functionality()
        test_error_handling()

        print("=== AGENT MANAGEMENT TESTS PASSED ===")

        print("\nSummary:")
        print("  Agent deployment service: ✓ Working")
        print("  Install agents dialog: ✓ Working")
        print("  Import agents dialog: ✓ Working")
        print("  Agent import functionality: ✓ Working")
        print("  Error handling: ✓ Working")

        return 0

    except Exception as e:
        print("=== AGENT MANAGEMENT TESTS FAILED ===")
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
