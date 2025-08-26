#!/usr/bin/env python3
"""Test that the TUI module imports correctly after fixing Screen to Container."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    # Test that classes are now Container subclasses, not Screen
    from textual.containers import Container
    from textual.screen import Screen

    from claude_mpm.cli.commands.configure_tui import (
        AgentManagementScreen,
        BehaviorFilesScreen,
        ConfigureTUI,
        SettingsScreen,
        SimpleAgentManager,
        TemplateEditingScreen,
    )

    # Create test instances to verify they work
    config_dir = Path.home() / ".claude-mpm"
    agent_manager = SimpleAgentManager(config_dir)

    # These should now be Container subclasses
    agent_screen = AgentManagementScreen(agent_manager)
    template_screen = TemplateEditingScreen(agent_manager, "project", Path.cwd())
    behavior_screen = BehaviorFilesScreen("project", Path.cwd())
    settings_screen = SettingsScreen("project", Path.cwd())

    # Verify they are Container instances
    assert isinstance(
        agent_screen, Container
    ), f"AgentManagementScreen should be a Container, got {type(agent_screen)}"
    assert isinstance(
        template_screen, Container
    ), f"TemplateEditingScreen should be a Container, got {type(template_screen)}"
    assert isinstance(
        behavior_screen, Container
    ), f"BehaviorFilesScreen should be a Container, got {type(behavior_screen)}"
    assert isinstance(
        settings_screen, Container
    ), f"SettingsScreen should be a Container, got {type(settings_screen)}"

    # Verify they are NOT Screen instances
    assert not isinstance(
        agent_screen, Screen
    ), "AgentManagementScreen should NOT be a Screen"
    assert not isinstance(
        template_screen, Screen
    ), "TemplateEditingScreen should NOT be a Screen"
    assert not isinstance(
        behavior_screen, Screen
    ), "BehaviorFilesScreen should NOT be a Screen"
    assert not isinstance(
        settings_screen, Screen
    ), "SettingsScreen should NOT be a Screen"

    print("✅ All screens are now Container subclasses (not Screen)")
    print("✅ This should fix the blank screen issue with ContentSwitcher")
    print(
        "\nThe fix is complete! The screens should now work properly with ContentSwitcher."
    )

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except AssertionError as e:
    print(f"❌ Assertion error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
