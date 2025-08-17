#!/usr/bin/env python3
"""
Script to move test files from scripts/ to tests/ directory with proper organization.
"""

import shutil
from pathlib import Path

# Define the mapping of test files to their new locations
TEST_FILE_MAPPING = {
    # Agent-related tests
    'test_agent_deployment.py': 'tests/integration/agents/',
    'test_agent_deployment_fix.py': 'tests/integration/agents/',
    'test_agent_capabilities_fix.py': 'tests/integration/agents/',
    'test_agent_exclusion.py': 'tests/integration/agents/',
    'test_agent_id_comparison.py': 'tests/integration/agents/',
    'test_agent_id_fix.py': 'tests/integration/agents/',
    'test_agent_names_fix.py': 'tests/integration/agents/',
    'test_comprehensive_agent_exclusion.py': 'tests/integration/agents/',
    
    # Memory-related tests
    'test_memory_guardian.py': 'tests/integration/memory/',
    'test_memory_guardian_e2e.py': 'tests/integration/memory/',
    'test_memory_warning.py': 'tests/integration/memory/',
    'test_run_guarded_experimental.py': 'tests/integration/memory/',
    
    # MCP-related tests
    'test_mcp_cli.py': 'tests/integration/mcp/',
    'test_mcp_client_integration.py': 'tests/integration/mcp/',
    'test_mcp_server.py': 'tests/integration/mcp/',
    'test_mcp_standards_compliance.py': 'tests/integration/mcp/',
    
    # Infrastructure tests
    'test_activity_logging.py': 'tests/integration/infrastructure/',
    'test_response_logging.py': 'tests/integration/infrastructure/',
    'test_response_logging_debug.py': 'tests/integration/infrastructure/',
    'test_response_logging_edge_cases.py': 'tests/integration/infrastructure/',
    'test_response_logging_health.py': 'tests/integration/infrastructure/',
    'test_response_logging_interactive.py': 'tests/integration/infrastructure/',
    'test_socketio_refactor.py': 'tests/integration/infrastructure/',
    'test_hook_debug_mode.py': 'tests/integration/infrastructure/',
    'test_file_events.py': 'tests/integration/infrastructure/',
    
    # Miscellaneous tests
    'test_audit_basic.py': 'tests/integration/misc/',
    'test_capabilities_update.py': 'tests/integration/misc/',
    'test_cleanup_fix.py': 'tests/integration/misc/',
    'test_cleanup_input.py': 'tests/integration/misc/',
    'test_cleanup_interactive.py': 'tests/integration/misc/',
    'test_cli_fixes.py': 'tests/integration/misc/',
    'test_dashboard_file_viewer.py': 'tests/integration/misc/',
    'test_delegation_tracking_fix.py': 'tests/integration/misc/',
    'test_dependency_system.py': 'tests/integration/misc/',
    'test_hello_world_tool.py': 'tests/integration/misc/',
    'test_individual_deps.py': 'tests/integration/misc/',
    'test_metadata_stripping.py': 'tests/integration/misc/',
    'test_no_html_comments.py': 'tests/integration/misc/',
    'test_path_resolution.py': 'tests/integration/misc/',
    'test_smart_dependency_checking.py': 'tests/integration/misc/',
    'test_ticketing_instructions.py': 'tests/integration/misc/',
    'test_user_directory_scenario.py': 'tests/integration/misc/',
}

def move_test_files():
    """Move test files from scripts/ to tests/ with proper organization."""
    scripts_dir = Path('scripts')
    
    moved_files = []
    failed_files = []
    
    for test_file, target_dir in TEST_FILE_MAPPING.items():
        source_path = scripts_dir / test_file
        target_path = Path(target_dir) / test_file
        
        if source_path.exists():
            try:
                # Ensure target directory exists
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move the file
                shutil.move(str(source_path), str(target_path))
                moved_files.append((source_path, target_path))
                print(f"✓ Moved {source_path} -> {target_path}")
                
            except Exception as e:
                failed_files.append((source_path, str(e)))
                print(f"✗ Failed to move {source_path}: {e}")
        else:
            print(f"⚠ File not found: {source_path}")
    
    print(f"\nSummary:")
    print(f"  Moved: {len(moved_files)} files")
    print(f"  Failed: {len(failed_files)} files")
    
    if failed_files:
        print(f"\nFailed files:")
        for file_path, error in failed_files:
            print(f"  {file_path}: {error}")

if __name__ == '__main__':
    move_test_files()
