#!/usr/bin/env python3
"""Detailed debug script to understand memory initialization"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Add the project source to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import the classes directly to test them
from claude_mpm.core.config import Config
from claude_mpm.services.agent_memory_manager import AgentMemoryManager

def test_memory_manager_directly():
    """Test the AgentMemoryManager class directly"""
    print("=== Testing AgentMemoryManager directly ===")
    
    # Create a temporary test directory
    test_dir = tempfile.mkdtemp(prefix="debug_memory_direct_")
    print(f"Test directory: {test_dir}")
    
    # Change to test directory
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    print(f"Current working directory: {os.getcwd()}")
    
    try:
        # Create memory manager
        config = Config()
        print(f"Creating AgentMemoryManager with working_directory={Path(test_dir)}")
        memory_manager = AgentMemoryManager(config, Path(test_dir))
        
        print(f"Memory manager working_directory: {memory_manager.working_directory}")
        print(f"Memory manager memories_dir: {memory_manager.memories_dir}")
        print(f"Memory directory exists: {memory_manager.memories_dir.exists()}")
        
        # List contents of test directory
        print(f"\nContents of test directory {test_dir}:")
        for item in Path(test_dir).iterdir():
            print(f"  {item}")
            if item.is_dir():
                for subitem in item.iterdir():
                    print(f"    {subitem}")
                    if subitem.is_dir():
                        for subsubitem in subitem.iterdir():
                            print(f"      {subsubitem}")
        
        # Check if memory directory was created in project root
        project_memory_dir = project_root / ".claude-mpm" / "memories"
        print(f"\nProject memory dir exists: {project_memory_dir.exists()}")
        if project_memory_dir.exists():
            print(f"Project memory dir path: {project_memory_dir}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        os.chdir(original_cwd)
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)

def test_cli_command():
    """Test via CLI command"""
    print("\n=== Testing via CLI command ===")
    
    # Create a temporary test directory
    test_dir = tempfile.mkdtemp(prefix="debug_memory_cli_")
    print(f"Test directory: {test_dir}")
    
    original_cwd = os.getcwd()
    os.chdir(test_dir)
    print(f"Current working directory: {os.getcwd()}")
    
    try:
        # Get the mpm command path
        mpm_cmd = str(project_root / "claude-mpm")
        print(f"MPM command: {mpm_cmd}")
        
        # Run memory init
        cmd = [mpm_cmd, "memory", "init"]
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check what was created
        print(f"\nContents of test directory {test_dir}:")
        for item in Path(test_dir).iterdir():
            print(f"  {item}")
            if item.is_dir():
                for subitem in item.iterdir():
                    print(f"    {subitem}")
                    if subitem.is_dir():
                        for subsubitem in subitem.iterdir():
                            print(f"      {subsubitem}")
        
        # Check project root
        project_memory_dir = project_root / ".claude-mpm" / "memories"
        print(f"\nProject memory dir exists: {project_memory_dir.exists()}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        os.chdir(original_cwd)
        import shutil
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    print("Starting detailed memory initialization debugging...")
    print("=" * 60)
    
    success1 = test_memory_manager_directly()
    success2 = test_cli_command()
    
    print(f"\nResults:")
    print(f"Direct test: {'PASS' if success1 else 'FAIL'}")
    print(f"CLI test: {'PASS' if success2 else 'FAIL'}")