#!/usr/bin/env python3
"""
Script to reorganize the scripts directory by moving utilities to tools/
and keeping only legitimate build/deployment scripts in scripts/.
"""

import shutil
from pathlib import Path

# Files that should STAY in scripts/ (legitimate build/deployment scripts)
KEEP_IN_SCRIPTS = {
    # Build and deployment scripts
    'install.sh',
    'install_dev.sh', 
    'install_build_hook.sh',
    'install_git_hook.sh',
    'uninstall.sh',
    'deploy_local.sh',
    'setup_local_mcp.sh',
    'pre-commit-build.sh',
    'publish.sh',
    'release.py',
    'increment_build.py',
    'manage_version.py',
    
    # Test runner scripts
    'run_all_tests.sh',
    'run_e2e_tests.sh',
    'test_docs_build.sh',
    'test_memory_guardian_suite.sh',
    'test_startup_initialization.sh',
    'test_agent_commands.sh',
    'test_agent_response_logging.sh',
    
    # Package management
    'package-lock.json',
    'postinstall.js',
    
    # CLI wrappers
    'claude-mpm',
    'claude-mpm-socketio',
    'ticket',
    'ticket.py',
    
    # Essential monitoring
    'monitor_memory.sh',
    'sync_tickets_github.sh',
}

# Mapping of files to move to tools/ subdirectories
MOVE_TO_TOOLS = {
    # Development utilities -> tools/dev/
    'debug_*.py': 'tools/dev/',
    'analyze_*.py': 'tools/dev/',
    'audit_documentation.py': 'tools/dev/',
    'check_*.py': 'tools/dev/',
    'validate_*.py': 'tools/dev/',
    'verify_*.py': 'tools/dev/',
    'standardize_imports.py': 'tools/dev/',
    'trace_deployment.py': 'tools/dev/',
    'show_pm_system_prompt.py': 'tools/dev/',
    'find_websocket_port.py': 'tools/dev/',
    'generate_comprehensive_test_report.py': 'tools/dev/',
    
    # Migration utilities -> tools/migration/
    'fix_*.py': 'tools/migration/',
    'migrate_*.py': 'tools/migration/',
    'update_*.py': 'tools/migration/',
    'convert_*.py': 'tools/migration/',
    'remove_*.py': 'tools/migration/',
    'add_agent_versioning.py': 'tools/migration/',
    'aggregate_agent_dependencies.py': 'tools/migration/',
    
    # Administrative tools -> tools/admin/
    'cleanup_*.py': 'tools/admin/',
    'monitor_*.py': 'tools/admin/',
    'monitoring_*.py': 'tools/admin/',
    'readthedocs_api.py': 'tools/admin/',
    'socketio_server_manager.py': 'tools/admin/',
    
    # Demo and example scripts -> tools/dev/examples/
    'demo_*.py': 'tools/dev/examples/',
    'example_*.py': 'tools/dev/examples/',
    'hello_*.py': 'tools/dev/examples/',
    'flask_*.py': 'tools/dev/examples/',
    'simple_*.py': 'tools/dev/examples/',
    'final_*.py': 'tools/dev/examples/',
    'mpm_test.py': 'tools/dev/examples/',
    
    # Diagnostic tools -> tools/dev/diagnostics/
    'diagnostic_*.py': 'tools/dev/diagnostics/',
    'run_socketio_diagnostics.py': 'tools/dev/diagnostics/',
    'run_mcp_tests.py': 'tools/dev/diagnostics/',
    'run_performance_validation_suite.py': 'tools/dev/diagnostics/',
    'run_all_socketio_tests.py': 'tools/dev/diagnostics/',
    
    # Launcher utilities -> tools/dev/launchers/
    'launch_*.py': 'tools/dev/launchers/',
    'start_*.py': 'tools/dev/launchers/',
    'install_*.py': 'tools/dev/launchers/',
    'register_*.py': 'tools/dev/launchers/',
    'trigger_*.py': 'tools/dev/launchers/',
    'deploy_project_agents.py': 'tools/dev/launchers/',
    'run_mpm.py': 'tools/dev/launchers/',
    'interactive_wrapper.py': 'tools/dev/launchers/',
    'simulate_pipx_install.py': 'tools/dev/launchers/',
    
    # Consolidation utilities -> tools/migration/
    'consolidate_services.py': 'tools/migration/',
}

def matches_pattern(filename, pattern):
    """Check if filename matches a glob-like pattern."""
    if '*' in pattern:
        prefix, suffix = pattern.split('*', 1)
        return filename.startswith(prefix) and filename.endswith(suffix)
    return filename == pattern

def get_target_directory(filename):
    """Determine target directory for a file."""
    # Check if file should stay in scripts
    if filename in KEEP_IN_SCRIPTS:
        return None
    
    # Check patterns for tools migration
    for pattern, target_dir in MOVE_TO_TOOLS.items():
        if matches_pattern(filename, pattern):
            return target_dir
    
    # Default: move to tools/dev/misc/
    return 'tools/dev/misc/'

def reorganize_scripts():
    """Reorganize the scripts directory."""
    scripts_dir = Path('scripts')
    
    # Create necessary directories
    tool_dirs = [
        'tools/dev/examples',
        'tools/dev/diagnostics', 
        'tools/dev/launchers',
        'tools/dev/misc',
        'tools/migration',
        'tools/admin'
    ]
    
    for dir_path in tool_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    moved_files = []
    kept_files = []
    failed_files = []
    
    # Process Python files
    for py_file in scripts_dir.glob('*.py'):
        filename = py_file.name
        target_dir = get_target_directory(filename)
        
        if target_dir is None:
            kept_files.append(filename)
            continue
        
        try:
            target_path = Path(target_dir) / filename
            shutil.move(str(py_file), str(target_path))
            moved_files.append((filename, target_dir))
            print(f"✓ Moved {filename} -> {target_dir}")
        except Exception as e:
            failed_files.append((filename, str(e)))
            print(f"✗ Failed to move {filename}: {e}")
    
    # Process shell scripts (keep most in scripts, move some to tools)
    shell_scripts_to_move = {
        'demo_hook_behavior.sh': 'tools/dev/examples/',
        'demo_hook_debug_behavior.sh': 'tools/dev/examples/',
        'run_flask_app.sh': 'tools/dev/examples/',
    }
    
    for sh_file in scripts_dir.glob('*.sh'):
        filename = sh_file.name
        if filename in shell_scripts_to_move:
            target_dir = shell_scripts_to_move[filename]
            try:
                target_path = Path(target_dir) / filename
                shutil.move(str(sh_file), str(target_path))
                moved_files.append((filename, target_dir))
                print(f"✓ Moved {filename} -> {target_dir}")
            except Exception as e:
                failed_files.append((filename, str(e)))
                print(f"✗ Failed to move {filename}: {e}")
        else:
            kept_files.append(filename)
    
    # Move HTML files to tools/dev/misc/
    for html_file in scripts_dir.glob('*.html'):
        filename = html_file.name
        try:
            target_path = Path('tools/dev/misc') / filename
            shutil.move(str(html_file), str(target_path))
            moved_files.append((filename, 'tools/dev/misc/'))
            print(f"✓ Moved {filename} -> tools/dev/misc/")
        except Exception as e:
            failed_files.append((filename, str(e)))
            print(f"✗ Failed to move {filename}: {e}")
    
    # Clean up empty directories and cache
    try:
        shutil.rmtree(scripts_dir / '__pycache__', ignore_errors=True)
        shutil.rmtree(scripts_dir / 'logs', ignore_errors=True)
        shutil.rmtree(scripts_dir / 'demo', ignore_errors=True)
        print("✓ Cleaned up cache and log directories")
    except Exception as e:
        print(f"⚠ Warning: Could not clean up directories: {e}")
    
    print(f"\nSummary:")
    print(f"  Moved: {len(moved_files)} files")
    print(f"  Kept in scripts/: {len(kept_files)} files")
    print(f"  Failed: {len(failed_files)} files")
    
    if kept_files:
        print(f"\nFiles kept in scripts/:")
        for filename in sorted(kept_files):
            print(f"  {filename}")
    
    if failed_files:
        print(f"\nFailed files:")
        for filename, error in failed_files:
            print(f"  {filename}: {error}")

if __name__ == '__main__':
    reorganize_scripts()
