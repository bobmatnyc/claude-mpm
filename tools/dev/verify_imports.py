#!/usr/bin/env python3
"""
Verify that all imports in the codebase follow the standards.
"""

import ast
import sys
from pathlib import Path
from typing import List


class ImportVerifier:
    """Verify imports follow project standards."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_path = project_root / "src"
        self.issues = []

    def verify_file(self, file_path: Path) -> List[str]:
        """Verify imports in a single file."""
        issues = []

        try:
            content = file_path.read_text()

            # Check for relative imports
            if "from ." in content or "import ." in content:
                issues.append("Contains relative imports")

            # Check for try/except imports
            if "except ImportError:" in content and (
                "from " in content or "import " in content
            ):
                # More precise check
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if "except ImportError:" in line:
                        # Check previous lines for import in try block
                        for j in range(max(0, i - 5), i):
                            if lines[j].strip().startswith(("from ", "import ")):
                                issues.append(
                                    f"Line {j + 1}: Import inside try/except block"
                                )
                                break

            # Parse AST to check imports
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.level > 0:  # Relative import
                        issues.append(
                            f"Line {node.lineno}: Relative import with level {node.level}"
                        )
                    elif node.module and not node.module.startswith("claude_mpm"):
                        # Check if it's a standard library or third-party import
                        if not self._is_standard_or_third_party(node.module):
                            issues.append(
                                f"Line {node.lineno}: Import not from claude_mpm: {node.module}"
                            )

        except Exception as e:
            issues.append(f"Error parsing file: {e}")

        return issues

    def _is_standard_or_third_party(self, module: str) -> bool:
        """Check if module is standard library or known third-party."""
        standard_modules = {
            "os",
            "sys",
            "pathlib",
            "json",
            "typing",
            "asyncio",
            "subprocess",
            "datetime",
            "time",
            "logging",
            "unittest",
            "pytest",
            "re",
            "collections",
            "itertools",
            "functools",
            "contextlib",
            "tempfile",
            "shutil",
            "uuid",
            "hashlib",
            "random",
            "math",
            "socket",
            "threading",
            "multiprocessing",
            "signal",
            "atexit",
            "abc",
            "enum",
            "dataclasses",
            "warnings",
            "copy",
            "io",
            "csv",
            "configparser",
            "argparse",
            "platform",
            "importlib",
            "traceback",
            "inspect",
            "ast",
            "textwrap",
            "pprint",
            "weakref",
            "concurrent",
            "queue",
            "sqlite3",
            "pickle",
            "base64",
            "urllib",
            "http",
            "email",
            "ftplib",
            "tarfile",
            "zipfile",
            "gzip",
            "bz2",
            "lzma",
            "statistics",
            "bisect",
            "heapq",
            "decimal",
            "fractions",
        }

        third_party_modules = {
            "pytest",
            "numpy",
            "pandas",
            "requests",
            "flask",
            "django",
            "sqlalchemy",
            "pydantic",
            "click",
            "tqdm",
            "matplotlib",
            "scipy",
            "sklearn",
            "tensorflow",
            "torch",
            "PIL",
            "cv2",
            "yaml",
            "toml",
            "jinja2",
            "beautifulsoup4",
            "selenium",
            "paramiko",
            "cryptography",
            "jwt",
            "redis",
            "celery",
            "aiogram",
            "aiohttp",
            "fastapi",
            "uvicorn",
            "starlette",
            "httpx",
            "anthropic",
            "openai",
            "langchain",
            "chromadb",
            "pinecone",
            "weaviate",
            "qdrant",
            "ai_trackdown_pytools",
            "psutil",
            "tomllib",
            "tomli",
        }

        # Check module root
        root = module.split(".", maxsplit=1)[0]
        return root in standard_modules or root in third_party_modules

    def run(self) -> None:
        """Run import verification."""
        python_files = list(self.src_path.rglob("*.py"))

        # Filter out unwanted directories
        python_files = [
            f
            for f in python_files
            if not any(
                part in f.parts
                for part in [
                    "__pycache__",
                    ".pytest_cache",
                    "build",
                    "dist",
                    "venv",
                    ".venv",
                ]
            )
        ]

        print(f"Verifying imports in {len(python_files)} files...\n")

        files_with_issues = 0
        total_issues = 0

        for file_path in python_files:
            issues = self.verify_file(file_path)
            if issues:
                files_with_issues += 1
                total_issues += len(issues)
                print(f"\n{file_path.relative_to(self.project_root)}:")
                for issue in issues:
                    print(f"  - {issue}")

        print(f"\n{'=' * 60}")
        print("Verification Summary:")
        print(f"  Total files checked: {len(python_files)}")
        print(f"  Files with issues: {files_with_issues}")
        print(f"  Total issues found: {total_issues}")

        if files_with_issues == 0:
            print("\n✅ All imports follow the project standards!")
            sys.exit(0)
        else:
            print(
                "\n❌ Import issues found. Run scripts/fix_all_imports.py to fix them."
            )
            sys.exit(1)


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    verifier = ImportVerifier(project_root)
    verifier.run()


if __name__ == "__main__":
    main()
