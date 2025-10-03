"""Simple directory listing API with proper filtering to match main code explorer"""

from pathlib import Path

from aiohttp import web

# Import GitignoreManager from the proper package location
from claude_mpm.tools.code_tree_analyzer import GitignoreManager

# Code extensions from main explorer
CODE_EXTENSIONS = {
    # Programming Languages
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".r",
    ".m",
    ".mm",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".bat",
    ".cmd",
    ".sql",
    # Web & Data
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".xml",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    # Documentation
    ".md",
    ".rst",
    ".txt",
}

# Directories to always skip
SKIP_DIRS = {
    "node_modules",
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "dist",
    "build",
    ".tox",
    "htmlcov",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
    ".idea",
    ".vscode",
    "env",
    ".coverage",
    "__MACOSX",
    ".ipynb_checkpoints",
}

# Dotfiles that are allowed to be shown
DOTFILE_EXCEPTIONS = {
    ".env.example",
    ".env.sample",
    ".gitlab-ci.yml",
    ".travis.yml",
    ".dockerignore",
    ".editorconfig",
    ".eslintrc",
    ".prettierrc",
    ".gitignore",
}


def has_code_files(directory_path, max_depth=5, current_depth=0):
    """Check if a directory contains code files (matching main explorer logic)"""
    if current_depth >= max_depth:
        return False

    try:
        for item in list(Path(directory_path).iterdir()):
            # Skip hidden files/dirs unless in exceptions
            if item.startswith(".") and item not in DOTFILE_EXCEPTIONS:
                continue

            item_path = Path(directory_path) / item

            if Path(item_path).is_file():
                # Check if it's a code file
                ext = Path(item).suffix.lower()
                if ext in CODE_EXTENSIONS:
                    return True
            elif Path(item_path).is_dir():
                # Skip certain directories
                if item in SKIP_DIRS or item.endswith(".egg-info"):
                    continue
                # Recursively check subdirectories
                if has_code_files(item_path, max_depth, current_depth + 1):
                    return True
    except (PermissionError, OSError):
        pass

    return False


def should_show_item(item_name, item_path, is_directory):
    """Determine if an item should be shown based on filtering rules"""
    # Always hide system files
    if item_name in {".DS_Store", "Thumbs.db", "desktop.ini"}:
        return False

    # Hide files with certain extensions
    if item_name.endswith((".pyc", ".pyo", ".pyd")):
        return False

    # Handle dotfiles
    if item_name.startswith("."):
        # Only show specific dotfile exceptions
        return item_name in DOTFILE_EXCEPTIONS

    if is_directory:
        # Skip certain directories
        if item_name in SKIP_DIRS or item_name.endswith(".egg-info"):
            return False

        # Only show directories that have code files or subdirectories
        if not has_code_files(item_path, max_depth=3):
            # Check if it has any visible subdirectories
            try:
                for subitem in list(Path(item_path).iterdir()):
                    subitem_path = Path(item_path) / subitem
                    if Path(subitem_path).is_dir():
                        if not subitem.startswith(".") and subitem not in SKIP_DIRS:
                            return True
                return False
            except (PermissionError, OSError):
                return False
    else:
        # For files, check if it's a code file or documentation
        ext = Path(item_name).suffix.lower()
        if ext in CODE_EXTENSIONS:
            return True

        # Show certain config files even without extensions
        base_name = item_name.lower()
        if base_name in {
            "makefile",
            "dockerfile",
            "jenkinsfile",
            "rakefile",
            "gemfile",
        }:
            return True

        # Hide other non-code files
        return False

    return True


async def list_directory(request):
    """Directory listing with filtering to match main code explorer"""
    path = request.query.get("path", ".")

    # Convert to absolute path
    abs_path = Path(Path(path).resolve().expanduser())

    result = {
        "path": abs_path,
        "exists": Path(abs_path).exists(),
        "is_directory": Path(abs_path).is_dir(),
        "contents": [],
        "filtered": True,  # Indicate that filtering is applied
        "filter_info": "Showing only code files and directories with code",
    }

    if result["exists"] and result["is_directory"]:
        try:
            # Initialize gitignore manager for this directory
            gitignore_mgr = GitignoreManager()

            # List all items
            items = list(Path(abs_path).iterdir())

            for item in items:
                item_path = Path(abs_path) / item
                is_directory = Path(item_path).is_dir()

                # Check if item should be ignored by gitignore
                if gitignore_mgr.should_ignore(Path(item_path), Path(abs_path)):
                    continue

                # Apply additional filtering rules
                if not should_show_item(item, item_path, is_directory):
                    continue

                # Add to results
                result["contents"].append(
                    {
                        "name": item,
                        "path": item_path,
                        "is_directory": is_directory,
                        "is_file": Path(item_path).is_file(),
                        "is_code_file": not is_directory
                        and any(item.endswith(ext) for ext in CODE_EXTENSIONS),
                    }
                )

            # Sort: directories first, then files
            result["contents"].sort(
                key=lambda x: (not x["is_directory"], x["name"].lower())
            )

            # Add summary statistics
            dir_count = sum(1 for x in result["contents"] if x["is_directory"])
            file_count = len(result["contents"]) - dir_count
            code_file_count = sum(
                1 for x in result["contents"] if x.get("is_code_file", False)
            )

            result["summary"] = {
                "total_items": len(result["contents"]),
                "directories": dir_count,
                "files": file_count,
                "code_files": code_file_count,
            }

        except Exception as e:
            result["error"] = str(e)

    return web.json_response(result)


def register_routes(app):
    """Register simple directory routes with the aiohttp app"""
    app.router.add_get("/api/directory/list", list_directory)
