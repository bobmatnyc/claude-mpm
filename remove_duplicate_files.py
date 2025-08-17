#!/usr/bin/env python3
"""
Script to remove confirmed duplicate files from the codebase.
"""

import os
import sys
import shutil
from pathlib import Path

def remove_duplicate_socketio_file():
    """Remove the duplicate socketio file."""
    # The two files are identical:
    # - src/claude_mpm/services/socketio_client_manager.py
    # - src/claude_mpm/services/communication/websocket.py
    
    # Keep the one in the more logical location (services/socketio_client_manager.py)
    # Remove the one in communication/websocket.py
    
    duplicate_file = Path("src/claude_mpm/services/communication/websocket.py")
    
    if duplicate_file.exists():
        print(f"Removing duplicate file: {duplicate_file}")
        duplicate_file.unlink()
        print("✓ Removed duplicate websocket.py")
        
        # Check if communication directory is now empty
        comm_dir = duplicate_file.parent
        if comm_dir.exists() and not any(comm_dir.iterdir()):
            print(f"Removing empty directory: {comm_dir}")
            comm_dir.rmdir()
            print("✓ Removed empty communication directory")
    else:
        print(f"File not found: {duplicate_file}")

def update_imports():
    """Update any imports that might reference the removed file."""
    # Search for imports of the removed file
    import_patterns = [
        "from claude_mpm.services.communication.websocket",
        "from .communication.websocket",
        "import claude_mpm.services.communication.websocket"
    ]
    
    # Find Python files that might import the removed module
    for py_file in Path("src").rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Replace imports
            for pattern in import_patterns:
                if pattern in content:
                    print(f"Found import in {py_file}: {pattern}")
                    # Replace with correct import
                    content = content.replace(
                        "from claude_mpm.services.communication.websocket",
                        "from claude_mpm.services.socketio_client_manager"
                    )
                    content = content.replace(
                        "from .communication.websocket",
                        "from .socketio_client_manager"
                    )
                    content = content.replace(
                        "import claude_mpm.services.communication.websocket",
                        "import claude_mpm.services.socketio_client_manager"
                    )
            
            # Write back if changed
            if content != original_content:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✓ Updated imports in {py_file}")
                
        except Exception as e:
            print(f"Error processing {py_file}: {e}")

def remove_obsolete_documentation():
    """Remove obsolete documentation files."""
    obsolete_docs = [
        "docs/api/claude_mpm.services.ticket_manager_di.rst",
        "docs/api/claude_mpm.services.ticketing_service_original.rst"
    ]
    
    for doc_file in obsolete_docs:
        doc_path = Path(doc_file)
        if doc_path.exists():
            print(f"Removing obsolete documentation: {doc_path}")
            doc_path.unlink()
            print(f"✓ Removed {doc_path}")
        else:
            print(f"Documentation file not found: {doc_path}")

def clean_empty_init_files():
    """Clean up minimal __init__.py files that only have imports."""
    minimal_inits = [
        "src/claude_mpm/hooks/__init__.py",
        "src/claude_mpm/generators/__init__.py", 
        "src/claude_mpm/validation/__init__.py",
        "src/claude_mpm/hooks/claude_hooks/__init__.py"
    ]
    
    for init_file in minimal_inits:
        init_path = Path(init_file)
        if init_path.exists():
            try:
                with open(init_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # Check if it's truly minimal (just imports and comments)
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                non_trivial = [line for line in lines if not line.startswith('#') and not line.startswith('"""') and not line.startswith("'''")]
                
                if len(non_trivial) <= 1:  # Just one import or empty
                    print(f"Found minimal __init__.py: {init_path} ({len(non_trivial)} non-trivial lines)")
                    # Don't remove, just note it
                    
            except Exception as e:
                print(f"Error checking {init_path}: {e}")

def main():
    """Main cleanup function."""
    print("Starting codebase cleanup...")
    print("=" * 50)
    
    # Change to project root
    if not Path("src/claude_mpm").exists():
        print("Error: Not in project root directory")
        sys.exit(1)
    
    # Remove duplicate files
    print("\n1. Removing duplicate files...")
    remove_duplicate_socketio_file()
    
    # Update imports
    print("\n2. Updating imports...")
    update_imports()
    
    # Remove obsolete documentation
    print("\n3. Removing obsolete documentation...")
    remove_obsolete_documentation()
    
    # Check minimal init files
    print("\n4. Checking minimal __init__.py files...")
    clean_empty_init_files()
    
    print("\n" + "=" * 50)
    print("Cleanup complete!")
    print("\nRecommendations for further cleanup:")
    print("- Consider splitting large files (>1000 lines)")
    print("- Review and remove unused imports")
    print("- Refactor monolithic functions (>100 lines)")

if __name__ == "__main__":
    main()
