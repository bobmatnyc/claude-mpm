#!/usr/bin/env python3
"""Test registry integration for ConfigScreenV2."""

import sys
import tempfile
import yaml
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.manager.discovery import InstallationDiscovery
from claude_mpm.services.project_registry import ProjectRegistry


def test_installation_discovery():
    """Test installation discovery functionality."""
    print("Testing Installation Discovery...")
    
    discovery = InstallationDiscovery()
    
    # Test finding installations
    print("Discovering installations...")
    installations = discovery.find_installations(use_cache=False)
    
    print(f"Found {len(installations)} installations:")
    for inst in installations:
        print(f"  - {inst.display_name} at {inst.path}")
        print(f"    Type: {inst.type}, Git: {inst.git_enabled}")
        if inst.toolchains:
            print(f"    Toolchains: {', '.join(inst.toolchains)}")
    
    # Test categorization
    global_installs = [i for i in installations if i.is_global]
    registry_installs = [i for i in installations if hasattr(i, 'from_registry') and i.from_registry]
    local_installs = [i for i in installations if not i.is_global and not getattr(i, 'from_registry', False)]
    
    print(f"\nCategorization:")
    print(f"  Global: {len(global_installs)}")
    print(f"  Registry: {len(registry_installs)}")
    print(f"  Local: {len(local_installs)}")
    
    print("Installation discovery test completed!\n")
    return installations


def test_project_registry():
    """Test project registry functionality."""
    print("Testing Project Registry...")
    
    registry = ProjectRegistry()
    
    # Test getting projects
    print("Getting projects from registry...")
    projects = registry.list_projects()
    
    print(f"Found {len(projects)} projects in registry:")
    for project_info in projects:
        project_name = project_info.get('project', {}).get('name', 'Unknown')
        project_type = project_info.get('project', {}).get('type', 'Unknown')
        project_path = project_info.get('project', {}).get('path', 'Unknown')
        
        print(f"  - {project_name}")
        print(f"    Type: {project_type}")
        print(f"    Path: {project_path}")
    
    print("Project registry test completed!\n")
    return projects


def test_config_screen_integration():
    """Test ConfigScreenV2 integration with registry."""
    print("Testing ConfigScreenV2 Registry Integration...")
    
    # Import ConfigScreenV2 safely
    try:
        from claude_mpm.manager.screens.config_screen_v2 import ConfigScreenV2
        print("✓ ConfigScreenV2 imported successfully")
        
        # Test initialization (without app for now)
        class MockApp:
            def show_dialog(self, title, content): pass
            def close_dialog(self): pass
        
        print("Creating ConfigScreenV2 instance...")
        config_screen = ConfigScreenV2(MockApp())
        print("✓ ConfigScreenV2 created successfully")
        
        # Test that services are initialized
        assert config_screen.discovery is not None, "InstallationDiscovery should be initialized"
        assert config_screen.registry is not None, "ProjectRegistry should be initialized"
        assert config_screen.agent_service is not None, "AgentDeploymentService should be initialized"
        print("✓ All services initialized")
        
        # Test installation refresh
        print("Testing installation refresh...")
        config_screen.refresh_installations()
        print(f"✓ Found {len(config_screen.installations)} installations")
        
        # Test widget building
        print("Testing widget building...")
        widget = config_screen.build_widget()
        assert widget is not None, "Widget should be built"
        print("✓ Widget built successfully")
        
        print("ConfigScreenV2 registry integration test completed!\n")
        
    except Exception as e:
        print(f"ConfigScreenV2 integration test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def test_edge_cases():
    """Test edge cases for registry integration."""
    print("Testing Edge Cases...")
    
    # Test with empty paths parameter
    discovery = InstallationDiscovery()
    
    print("Testing empty paths discovery...")
    installations = discovery.find_installations(paths=[], use_cache=False)
    print(f"✓ Empty paths handled: {len(installations)} installations found")
    
    # Test error handling with non-existent paths
    print("Testing non-existent path handling...")
    try:
        installations = discovery.find_installations(paths=[Path("/nonexistent/path")], use_cache=False)
        print(f"✓ Non-existent paths handled: {len(installations)} installations found")
    except Exception as e:
        print(f"✓ Error handled gracefully: {e}")
    
    # Test with temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        print("Testing empty workspace discovery...")
        installations = discovery.find_installations(paths=[temp_path], use_cache=False)
        print(f"✓ Empty workspace handled: {len(installations)} installations found")
    
    print("Edge cases test completed!\n")


def main():
    """Run all registry integration tests."""
    print("=== ConfigScreenV2 Registry Integration Tests ===\n")
    
    try:
        installations = test_installation_discovery()
        projects = test_project_registry()
        test_config_screen_integration()
        test_edge_cases()
        
        print("=== REGISTRY INTEGRATION TESTS PASSED ===")
        
        # Summary
        print(f"\nSummary:")
        print(f"  Installations found: {len(installations)}")
        print(f"  Registry projects: {len(projects)}")
        print(f"  Integration: ✓ Working")
        
        return 0
        
    except Exception as e:
        print(f"=== REGISTRY INTEGRATION TESTS FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())