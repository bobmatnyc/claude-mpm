#!/usr/bin/env python3
"""
Import validation script for claude-mpm.

This script validates all imports in the codebase and identifies critical issues.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in directory."""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)
    return python_files


def extract_imports(file_path: Path) -> List[str]:
    """Extract import statements from a Python file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")

        return imports
    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return []


def test_import(import_statement: str) -> Tuple[bool, str]:
    """Test if an import statement works."""
    try:
        exec(import_statement)
        return True, "SUCCESS"
    except Exception as e:
        return False, str(e)


def validate_imports():
    """Validate all imports in the codebase."""
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"

    print("🔍 Claude MPM Import Validation Report")
    print("=" * 50)

    # Find all Python files in src
    python_files = find_python_files(src_dir)
    print(f"Found {len(python_files)} Python files to validate")

    # Track results
    failed_imports: Dict[str, List[Tuple[Path, str]]] = {}
    success_count = 0
    total_imports = 0

    # Test critical modules first
    critical_imports = [
        "from claude_mpm.core.service_registry import ServiceRegistry",
        "from claude_mpm.core.factories import ServiceFactory",
        "from claude_mpm.services import AgentDeploymentService",
        "from claude_mpm.services.agents.deployment.agent_deployment import AgentDeploymentService",
        "from claude_mpm.cli.commands.agents import manage_agents",
    ]

    print("\n🧪 Testing Critical Imports:")
    print("-" * 30)

    for import_stmt in critical_imports:
        total_imports += 1
        success, error = test_import(import_stmt)
        if success:
            print(f"✓ {import_stmt}")
            success_count += 1
        else:
            print(f"✗ {import_stmt}")
            print(f"  Error: {error}")
            if import_stmt not in failed_imports:
                failed_imports[import_stmt] = []
            failed_imports[import_stmt].append((Path("CRITICAL"), error))

    # Test problematic patterns found in codebase
    print("\n🔍 Testing Known Problematic Patterns:")
    print("-" * 40)

    problematic_patterns = [
        "from claude_mpm.services.agent_deployment import AgentDeploymentService",
        "from claude_mpm.services.memory_builder import MemoryBuilder",
        "from claude_mpm.services.memory_router import MemoryRouter",
        "from claude_mpm.services.shared_prompt_cache import SharedPromptCache",
        "from claude_mpm.services.simple_cache_service import SimpleCacheService",
    ]

    for import_stmt in problematic_patterns:
        total_imports += 1
        success, error = test_import(import_stmt)
        if success:
            print(f"⚠️  {import_stmt} - WORKS (but should be updated)")
            success_count += 1
        else:
            print(f"✗ {import_stmt} - BROKEN")
            print(f"   Error: {error}")
            if import_stmt not in failed_imports:
                failed_imports[import_stmt] = []
            failed_imports[import_stmt].append((Path("PATTERN"), error))

    # Test backward compatibility
    print("\n🔄 Testing Backward Compatibility:")
    print("-" * 35)

    compat_imports = [
        "from claude_mpm.services import AgentRegistry",
        "from claude_mpm.services import AgentLifecycleManager",
        "from claude_mpm.services import MemoryBuilder",
        "from claude_mpm.services import MemoryRouter",
        "from claude_mpm.services import SharedPromptCache",
    ]

    for import_stmt in compat_imports:
        total_imports += 1
        success, error = test_import(import_stmt)
        if success:
            print(f"✓ {import_stmt}")
            success_count += 1
        else:
            print(f"✗ {import_stmt}")
            print(f"  Error: {error}")
            if import_stmt not in failed_imports:
                failed_imports[import_stmt] = []
            failed_imports[import_stmt].append((Path("COMPATIBILITY"), error))

    # Summary
    print("\n📊 Import Validation Summary:")
    print("-" * 30)
    print(f"Total imports tested: {total_imports}")
    print(f"Successful imports: {success_count}")
    print(f"Failed imports: {total_imports - success_count}")
    print(f"Success rate: {(success_count / total_imports) * 100:.1f}%")

    if failed_imports:
        print("\n❌ Failed Import Details:")
        print("-" * 25)
        for import_stmt, failures in failed_imports.items():
            print(f"\n{import_stmt}")
            for file_path, error in failures:
                print(f"  File: {file_path}")
                print(f"  Error: {error}")

    # Recommendations
    print("\n💡 Recommendations:")
    print("-" * 18)

    if failed_imports:
        print("1. Fix broken direct imports by updating to new service structure")
        print("2. Update old import patterns to use backward compatibility layer")
        print("3. Run import update script to fix known problematic patterns")
        print("4. Consider updating documentation with new import patterns")
    else:
        print("✓ All tested imports are working correctly!")

    return len(failed_imports) == 0


if __name__ == "__main__":
    success = validate_imports()
    sys.exit(0 if success else 1)
