"""Environmental awareness detector for PM command routing.

Detects the execution environment and writes environment.md to .claude-mpm/
so the PM agent knows the correct commands to use (e.g., uv run pytest vs pytest).
"""

import logging
import os
import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class EnvironmentDetector:
    """Detects and documents the execution environment for PM command awareness.

    Generates .claude-mpm/environment.md with command routing tables so the PM
    agent never issues bare `pip` or `pytest` when `uv pip` / `uv run pytest`
    are required.

    Usage:
        detector = EnvironmentDetector(project_root)
        env_file = detector.detect_and_write(force=True)
    """

    STALENESS_DAYS = 7
    MAX_FILE_SIZE_BYTES = 10_000  # ~2000 tokens

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.claude_mpm_dir = project_root / ".claude-mpm"
        self.environment_file = self.claude_mpm_dir / "environment.md"

    def is_stale(self) -> bool:
        """Return True if environment.md does not exist or is older than STALENESS_DAYS."""
        if not self.environment_file.exists():
            return True
        try:
            mtime = self.environment_file.stat().st_mtime
            age_seconds = datetime.now(UTC).timestamp() - mtime
            return age_seconds > self.STALENESS_DAYS * 86400
        except Exception:
            return True

    def detect_and_write(self, force: bool = False) -> Path | None:
        """Run detection and write environment.md.

        Args:
            force: Write even if not stale.

        Returns:
            Path to written file, or None if skipped.
        """
        if not force and not self.is_stale():
            return None
        try:
            content = self._generate_content()
            # Truncate if too large
            if len(content.encode("utf-8")) > self.MAX_FILE_SIZE_BYTES:
                content = content[: self.MAX_FILE_SIZE_BYTES].rsplit("\n", 1)[0]
                content += "\n\n<!-- truncated to stay within token budget -->\n"
            self.claude_mpm_dir.mkdir(parents=True, exist_ok=True)
            self.environment_file.write_text(content, encoding="utf-8")
            return self.environment_file
        except Exception as e:
            logger.warning(f"Environment detection failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_content(self) -> str:
        """Generate the environment.md markdown content."""
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        python_info = self._detect_python_info()
        pkg_mgr = self._detect_package_manager()
        installation = self._detect_installation_method()
        test_runner = self._detect_test_runner()
        toolchain = self._detect_toolchain()

        os_info = self._detect_os_info()
        shell = os.environ.get("SHELL", os.environ.get("COMSPEC", "unknown"))
        context = self._detect_context()

        lines = [
            "# Environment Configuration",
            "",
            f"Generated: {now}",
            f"Project: {self.project_root}",
            "",
            "## System",
            f"- OS: {os_info}",
            f"- Python: {python_info.get('version', 'unknown')} at {python_info.get('executable', 'unknown')}",
            f"- Shell: {shell}",
            f"- Context: {context}",
            "",
            "## Installation",
            f"- Method: {installation}",
            f"- claude-mpm: {sys.executable}",
            "",
            "## Package Manager Commands",
            "Use these EXACT commands — do not substitute alternatives:",
        ]

        for label, cmd in pkg_mgr.get("commands", {}).items():
            lines.append(f"- {label}: `{cmd}`")

        lines += [
            "",
            "## Project Toolchain",
        ]
        for k, v in toolchain.items():
            if isinstance(v, list):
                lines.append(f"- {k}: {', '.join(v) if v else 'none detected'}")
            else:
                lines.append(f"- {k}: {v}")

        lines += [
            f"- Test runner: {test_runner}",
            "",
            "## Command Routing (CRITICAL)",
        ]

        routing = self._build_routing_table(pkg_mgr, test_runner)
        if routing:
            lines.append("| Wrong command | Correct command |")
            lines.append("|---------------|-----------------|")
            for wrong, correct in routing:
                lines.append(f"| `{wrong}` | `{correct}` |")

        notes = pkg_mgr.get("notes", [])
        if notes:
            lines += ["", "## Notes"]
            for note in notes:
                lines.append(f"- {note}")

        lines.append("")
        return "\n".join(lines)

    def _detect_os_info(self) -> str:
        try:
            system = platform.system()
            if system == "Darwin":
                ver = platform.mac_ver()[0]
                return f"macOS {ver} (Darwin)"
            if system == "Linux":
                return f"Linux {platform.release()}"
            if system == "Windows":
                return f"Windows {platform.release()}"
            return f"{system} {platform.release()}"
        except Exception:
            return "unknown"

    def _detect_context(self) -> str:
        try:
            is_tty = sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False
            ci_vars = [
                "CI",
                "GITHUB_ACTIONS",
                "GITLAB_CI",
                "JENKINS",
                "TRAVIS",
                "CIRCLECI",
                "BUILDKITE",
            ]
            is_ci = any(os.environ.get(v) for v in ci_vars)
            if is_ci:
                return "CI/CD"
            return "interactive (TTY)" if is_tty else "non-interactive"
        except Exception:
            return "unknown"

    def _detect_installation_method(self) -> str:
        """Detect how claude-mpm was installed."""
        try:
            exe = sys.executable
            if "uv/tools" in exe or ".local/share/uv" in exe:
                return "uv tool"
            if "pipx/venvs" in exe:
                return "pipx"
            if "homebrew" in exe.lower() or "cellar" in exe.lower():
                return "homebrew"
            if "venv" in exe or ".venv" in exe:
                return "virtualenv"
            # Check if installed as editable / dev
            try:
                import importlib.metadata

                importlib.metadata.version("claude-mpm")
                return "pip install"
            except Exception:
                pass
            return "unknown"
        except Exception:
            return "unknown"

    def _detect_package_manager(self) -> dict:
        """Detect available package managers and return command mappings."""
        exe = sys.executable

        # uv-tool install: executable is inside uv tools dir
        is_uv_tool = "uv/tools" in exe or ".local/share/uv" in exe
        has_uv = shutil.which("uv") is not None
        has_uv_lock = (self.project_root / "uv.lock").exists()
        has_uv_config = self._pyproject_has_tool_uv()

        # pipx
        is_pipx = "pipx/venvs" in exe

        if is_uv_tool or (has_uv and (has_uv_lock or has_uv_config)):
            return {
                "name": "uv",
                "commands": {
                    "Install packages": "uv pip install <package>",
                    "Run Python": "uv run python",
                    "Run tests": "uv run pytest",
                    "Run scripts": "uv run <script>",
                    "Upgrade pip": "uv pip install --upgrade pip",
                },
                "notes": [
                    "This project uses `uv` for package management (PEP 668 compliant)",
                    "Always prefix pytest/python commands with `uv run`",
                    "Never use bare `pip` on this system",
                ],
            }
        if is_pipx:
            return {
                "name": "pipx",
                "commands": {
                    "Install packages": "pip install <package>",
                    "Run Python": "python",
                    "Run tests": "pytest",
                    "Run scripts": "python <script>",
                    "Upgrade pip": "pip install --upgrade pip",
                },
                "notes": [
                    "This tool is installed via pipx — use pip within the pipx venv",
                ],
            }
        # Plain venv or system Python
        return {
            "name": "pip",
            "commands": {
                "Install packages": "pip install <package>",
                "Run Python": "python",
                "Run tests": "pytest",
                "Run scripts": "python <script>",
                "Upgrade pip": "pip install --upgrade pip",
            },
            "notes": [],
        }

    def _pyproject_has_tool_uv(self) -> bool:
        """Return True if pyproject.toml contains [tool.uv] section."""
        pyproject = self.project_root / "pyproject.toml"
        if not pyproject.exists():
            return False
        try:
            content = pyproject.read_text(encoding="utf-8")
            return "[tool.uv]" in content
        except Exception:
            return False

    def _detect_python_info(self) -> dict:
        """Detect Python version and executable path."""
        try:
            version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            return {"version": version, "executable": sys.executable}
        except Exception:
            return {"version": "unknown", "executable": "unknown"}

    def _detect_test_runner(self) -> str:
        """Detect the correct test runner command."""
        try:
            root = self.project_root
            has_uv_lock = (root / "uv.lock").exists()
            has_uv_config = self._pyproject_has_tool_uv()
            has_uv = shutil.which("uv") is not None

            if (
                has_uv_lock
                or has_uv_config
                or (has_uv and "uv/tools" in sys.executable)
            ):
                return "uv run pytest"

            if (root / "package.json").exists():
                return "npm test"
            if (root / "Cargo.toml").exists():
                return "cargo test"
            if (root / "go.mod").exists():
                return "go test ./..."

            # Check Makefile for pytest target
            makefile = root / "Makefile"
            if makefile.exists():
                try:
                    content = makefile.read_text(encoding="utf-8")
                    if "uv run pytest" in content:
                        return "uv run pytest"
                    if "pytest" in content:
                        return "pytest"
                except Exception:
                    pass

            return "pytest"
        except Exception:
            return "pytest"

    def _detect_toolchain(self) -> dict:
        """Detect project toolchain (languages, frameworks, build tools)."""
        try:
            root = self.project_root
            languages = []
            frameworks = []
            build_tools = []

            # Languages
            if list(root.glob("**/*.py"))[:1]:
                languages.append("python")
            if list(root.glob("**/*.js"))[:1] or list(root.glob("**/*.ts"))[:1]:
                languages.append("javascript/typescript")
            if (root / "go.mod").exists():
                languages.append("go")
            if (root / "Cargo.toml").exists():
                languages.append("rust")

            # Frameworks (check pyproject.toml / requirements.txt)
            pyproject = root / "pyproject.toml"
            requirements = root / "requirements.txt"
            for fpath in [pyproject, requirements]:
                if fpath.exists():
                    try:
                        content = fpath.read_text(encoding="utf-8").lower()
                        if "fastapi" in content:
                            frameworks.append("fastapi")
                        if "django" in content:
                            frameworks.append("django")
                        if "flask" in content:
                            frameworks.append("flask")
                    except Exception:
                        pass

            if (root / "package.json").exists():
                try:
                    import json

                    pkg = json.loads((root / "package.json").read_text())
                    deps = {
                        **pkg.get("dependencies", {}),
                        **pkg.get("devDependencies", {}),
                    }
                    for fw in ("react", "next", "vue", "angular", "express"):
                        if any(fw in k for k in deps):
                            frameworks.append(fw)
                except Exception:
                    pass

            # Build tools
            if (root / "Makefile").exists():
                build_tools.append("make")
            if (root / "Dockerfile").exists() or (root / "docker-compose.yml").exists():
                build_tools.append("docker")
            if (root / "uv.lock").exists():
                build_tools.append("uv")
            elif (root / "requirements.txt").exists():
                build_tools.append("pip")

            return {
                "Languages": languages or ["unknown"],
                "Frameworks": frameworks,
                "Build tools": build_tools,
            }
        except Exception:
            return {"Languages": ["unknown"], "Frameworks": [], "Build tools": []}

    def _build_routing_table(self, pkg_mgr: dict, test_runner: str) -> list:
        """Build the wrong→correct command routing table."""
        name = pkg_mgr.get("name", "pip")
        rows = []
        if name == "uv":
            rows = [
                ("pip install", "uv pip install"),
                ("pip3 install", "uv pip install"),
                ("python -m pip", "uv pip"),
                ("pytest", "uv run pytest"),
                ("python", "uv run python"),
                ("python3", "uv run python"),
            ]
        elif name == "pipx":
            rows = [
                ("uv pip install", "pip install"),
                ("uv run pytest", "pytest"),
                ("uv run python", "python"),
            ]
        return rows
