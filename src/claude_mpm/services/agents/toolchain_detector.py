"""Toolchain detection service for auto-configuring agent deployment.

WHY: Automatically detect project toolchain (languages, frameworks, build tools)
to recommend appropriate agents. This eliminates manual agent selection and
ensures projects get the right agents for their technology stack.

Design Decision: File Pattern-Based Detection

Instead of AST parsing or dependency analysis, we use simple file pattern
matching. This is fast, reliable, and works across all languages without
requiring language-specific parsers.

Trade-offs:
- Speed: O(n) directory scan vs. O(n²) dependency graph analysis
- Simplicity: Pattern matching vs. complex AST parsing
- Reliability: File presence is more stable than version-specific APIs
- Coverage: May miss some edge cases but handles 95% of projects

Example Patterns:
- Python: *.py files, pyproject.toml, requirements.txt
- JavaScript/TypeScript: *.js, *.ts, package.json
- FastAPI: pyproject.toml with [tool.poetry.dependencies.fastapi]
- Docker: Dockerfile, docker-compose.yml

Performance:
- Time Complexity: O(n) where n = number of files scanned
- Space Complexity: O(1) for detection state
- Max Depth: Configurable (default: 3) to avoid deep recursion
- Exclusions: .git/, venv/, node_modules/, __pycache__/ ignored
"""

import logging
from pathlib import Path
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class ToolchainDetector:
    """Detect project toolchain from file patterns.

    Scans project directory to identify:
    - Languages (Python, JavaScript, Go, Rust, Java, Ruby, PHP)
    - Frameworks (FastAPI, Django, React, Next.js, Express, Spring)
    - Build Tools (Make, Docker, npm, pip)

    Then maps detected toolchain to recommended agents.

    Usage:
        >>> detector = ToolchainDetector()
        >>> toolchain = detector.detect_toolchain(Path("/project"))
        >>> agents = detector.recommend_agents(toolchain)
        >>> print(agents)
        ['python-engineer', 'ops', 'qa', 'research', 'documentation', 'ticketing']
    """

    # Language detection patterns (file extensions and config files)
    LANGUAGE_PATTERNS = {
        "python": {
            "extensions": [".py", ".pyi"],
            "config_files": [
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "requirements.txt",
            ],
        },
        "javascript": {
            "extensions": [".js", ".jsx", ".mjs"],
            "config_files": ["package.json", ".eslintrc.js"],
        },
        "typescript": {
            "extensions": [".ts", ".tsx"],
            "config_files": ["tsconfig.json", "package.json"],
        },
        "go": {
            "extensions": [".go"],
            "config_files": ["go.mod", "go.sum"],
        },
        "rust": {
            "extensions": [".rs"],
            "config_files": ["Cargo.toml", "Cargo.lock"],
        },
        "java": {
            "extensions": [".java"],
            "config_files": ["pom.xml", "build.gradle", "build.gradle.kts"],
        },
        "ruby": {
            "extensions": [".rb"],
            "config_files": ["Gemfile", "Rakefile"],
        },
        "php": {
            "extensions": [".php"],
            "config_files": ["composer.json", "composer.lock"],
        },
    }

    # Framework detection patterns (config files and content markers)
    FRAMEWORK_PATTERNS = {
        "fastapi": {
            "files": ["pyproject.toml", "requirements.txt"],
            "keywords": ["fastapi"],
        },
        "django": {
            "files": ["manage.py", "settings.py", "wsgi.py"],
            "keywords": ["django"],
        },
        "react": {
            "files": ["package.json"],
            "keywords": ["react"],
        },
        "nextjs": {
            "files": ["next.config.js", "next.config.ts", "package.json"],
            "keywords": ["next"],
        },
        "express": {
            "files": ["package.json"],
            "keywords": ["express"],
        },
        "spring": {
            "files": ["pom.xml", "build.gradle"],
            "keywords": ["spring-boot", "spring-framework"],
        },
    }

    # Build tool detection patterns
    BUILD_TOOL_PATTERNS = {
        "make": ["Makefile"],
        "docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
        "npm": ["package.json", "package-lock.json"],
        "pip": ["requirements.txt", "pyproject.toml", "Pipfile"],
        "gradle": ["build.gradle", "build.gradle.kts", "gradlew"],
        "maven": ["pom.xml", "mvnw"],
    }

    # Toolchain to agent mapping
    TOOLCHAIN_TO_AGENTS = {
        # Language-specific engineers
        "python": ["python-engineer"],
        "javascript": ["javascript-engineer-agent"],
        "typescript": ["typescript-engineer"],
        "go": ["golang-engineer"],
        "rust": ["rust-engineer"],
        "java": ["java-engineer"],
        "ruby": ["ruby-engineer"],
        "php": ["php-engineer"],
        # Framework-specific engineers (these may override language defaults)
        "fastapi": ["python-engineer"],
        "django": ["python-engineer"],
        "react": ["react-engineer"],
        "nextjs": ["nextjs-engineer"],
        "express": ["javascript-engineer-agent"],
        "spring": ["java-engineer"],
        # Ops agents based on tools
        "docker": ["ops", "local-ops-agent"],
        "vercel": ["vercel-ops-agent"],
        "gcp": ["gcp-ops-agent"],
        "make": ["ops"],
    }

    # Core agents always included (use exact agent IDs from repository)
    CORE_AGENTS = [
        "engineer",
        "qa-agent",
        "memory-manager-agent",
        "local-ops-agent",
        "research-agent",
        "documentation-agent",
        "security-agent",
    ]

    # Directories to exclude from scanning
    EXCLUDED_DIRS = {
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        "node_modules",
        "venv",
        ".venv",
        "env",
        ".env",
        "virtualenv",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "target",  # Maven/Gradle
        "vendor",  # Ruby/PHP
    }

    def __init__(self, max_scan_depth: int = 3):
        """Initialize toolchain detector.

        Args:
            max_scan_depth: Maximum directory depth to scan (default: 3)
                           Deeper projects may need higher values, but
                           scanning is limited to prevent performance issues.
        """
        self.max_scan_depth = max_scan_depth
        logger.debug(f"ToolchainDetector initialized (max_depth={max_scan_depth})")

    def detect_toolchain(self, project_path: Path) -> Dict[str, List[str]]:
        """Detect complete project toolchain.

        Scans project directory to identify languages, frameworks, and build tools.

        Args:
            project_path: Path to project root directory

        Returns:
            Dictionary with detected toolchain:
            {
                "languages": ["python", "javascript"],
                "frameworks": ["fastapi", "react"],
                "build_tools": ["docker", "make"]
            }

        Example:
            >>> detector = ToolchainDetector()
            >>> toolchain = detector.detect_toolchain(Path("/my-project"))
            >>> print(toolchain)
            {
                "languages": ["python"],
                "frameworks": ["fastapi"],
                "build_tools": ["docker", "make"]
            }
        """
        if not project_path.exists():
            logger.warning(f"Project path does not exist: {project_path}")
            return {"languages": [], "frameworks": [], "build_tools": []}

        if not project_path.is_dir():
            logger.warning(f"Project path is not a directory: {project_path}")
            return {"languages": [], "frameworks": [], "build_tools": []}

        logger.info(f"Detecting toolchain in {project_path}")

        # Scan project files
        scanned_files = self._scan_files(project_path)
        logger.debug(f"Scanned {len(scanned_files)} files")

        # Detect each component
        languages = self.detect_languages(scanned_files, project_path)
        frameworks = self.detect_frameworks(scanned_files, project_path)
        build_tools = self.detect_build_tools(scanned_files, project_path)

        toolchain = {
            "languages": languages,
            "frameworks": frameworks,
            "build_tools": build_tools,
        }

        logger.info(
            f"Detected toolchain: {len(languages)} languages, "
            f"{len(frameworks)} frameworks, {len(build_tools)} build tools"
        )

        return toolchain

    def detect_languages(
        self, scanned_files: List[Path], project_path: Path
    ) -> List[str]:
        """Detect programming languages from file extensions and config files.

        Args:
            scanned_files: List of files from project scan
            project_path: Project root path

        Returns:
            List of detected language names (e.g., ["python", "javascript"])
        """
        detected_languages: Set[str] = set()

        # Check each language pattern
        for language, patterns in self.LANGUAGE_PATTERNS.items():
            # Check file extensions
            for file_path in scanned_files:
                if file_path.suffix in patterns["extensions"]:
                    detected_languages.add(language)
                    logger.debug(
                        f"Detected {language} from extension: {file_path.name}"
                    )
                    break  # Found this language, move to next

            # Check config files (relative to project root)
            for config_file in patterns["config_files"]:
                if (project_path / config_file).exists():
                    detected_languages.add(language)
                    logger.debug(f"Detected {language} from config: {config_file}")
                    break

        return sorted(detected_languages)

    def detect_frameworks(
        self, scanned_files: List[Path], project_path: Path
    ) -> List[str]:
        """Detect frameworks from config files and content markers.

        Args:
            scanned_files: List of files from project scan
            project_path: Project root path

        Returns:
            List of detected framework names (e.g., ["fastapi", "react"])
        """
        detected_frameworks: Set[str] = set()

        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            # Check if required files exist
            framework_files_exist = any(
                (project_path / file_name).exists() for file_name in patterns["files"]
            )

            if not framework_files_exist:
                continue

            # Check for keyword markers in config files
            for config_file in patterns["files"]:
                config_path = project_path / config_file
                if not config_path.exists():
                    continue

                try:
                    content = config_path.read_text(encoding="utf-8", errors="ignore")
                    content_lower = content.lower()

                    # Check if any keyword is present
                    if any(
                        keyword in content_lower for keyword in patterns["keywords"]
                    ):
                        detected_frameworks.add(framework)
                        logger.debug(
                            f"Detected {framework} from keywords in {config_file}"
                        )
                        break

                except Exception as e:
                    logger.debug(f"Failed to read {config_path}: {e}")

        return sorted(detected_frameworks)

    def detect_build_tools(
        self, scanned_files: List[Path], project_path: Path
    ) -> List[str]:
        """Detect build tools from config files.

        Args:
            scanned_files: List of files from project scan
            project_path: Project root path

        Returns:
            List of detected build tool names (e.g., ["docker", "make"])
        """
        detected_tools: Set[str] = set()

        for tool, config_files in self.BUILD_TOOL_PATTERNS.items():
            for config_file in config_files:
                if (project_path / config_file).exists():
                    detected_tools.add(tool)
                    logger.debug(f"Detected {tool} from {config_file}")
                    break  # Found this tool, move to next

        return sorted(detected_tools)

    def recommend_agents(self, toolchain: Dict[str, List[str]]) -> List[str]:
        """Map detected toolchain to recommended agents.

        Combines language-specific, framework-specific, and ops agents with
        core agents (engineer, qa-agent, memory-manager-agent, local-ops-agent, research-agent,
        documentation-agent, security-agent).

        Args:
            toolchain: Detected toolchain dictionary with languages, frameworks, tools

        Returns:
            List of recommended agent IDs, deduplicated

        Example:
            >>> toolchain = {
            ...     "languages": ["python"],
            ...     "frameworks": ["fastapi"],
            ...     "build_tools": ["docker", "make"]
            ... }
            >>> agents = detector.recommend_agents(toolchain)
            >>> print(agents)
            ['python-engineer', 'ops', 'local-ops-agent', 'qa', 'research',
             'documentation', 'ticketing']
        """
        recommended: Set[str] = set()

        # Add core agents (always included)
        recommended.update(self.CORE_AGENTS)

        # Map languages to agents
        for language in toolchain.get("languages", []):
            if language in self.TOOLCHAIN_TO_AGENTS:
                recommended.update(self.TOOLCHAIN_TO_AGENTS[language])
                logger.debug(
                    f"Mapped language '{language}' to agents: "
                    f"{self.TOOLCHAIN_TO_AGENTS[language]}"
                )

        # Map frameworks to agents (may override language defaults)
        for framework in toolchain.get("frameworks", []):
            if framework in self.TOOLCHAIN_TO_AGENTS:
                recommended.update(self.TOOLCHAIN_TO_AGENTS[framework])
                logger.debug(
                    f"Mapped framework '{framework}' to agents: "
                    f"{self.TOOLCHAIN_TO_AGENTS[framework]}"
                )

        # Map build tools to agents
        for tool in toolchain.get("build_tools", []):
            if tool in self.TOOLCHAIN_TO_AGENTS:
                recommended.update(self.TOOLCHAIN_TO_AGENTS[tool])
                logger.debug(
                    f"Mapped build tool '{tool}' to agents: "
                    f"{self.TOOLCHAIN_TO_AGENTS[tool]}"
                )

        # Always include generic engineer as fallback
        if not any(
            agent.endswith("-engineer") or agent == "engineer" for agent in recommended
        ):
            recommended.add("engineer")
            logger.debug("Added generic 'engineer' as fallback")

        agents_list = sorted(recommended)
        logger.info(f"Recommended {len(agents_list)} agents: {agents_list}")
        return agents_list

    def _scan_files(self, project_path: Path) -> List[Path]:
        """Scan project files up to max_scan_depth.

        Excludes common non-source directories (.git/, venv/, node_modules/, etc.)

        Args:
            project_path: Project root directory

        Returns:
            List of file paths within scan depth

        Performance:
        - Iterative BFS to avoid recursion stack limits
        - Early termination on depth limit
        - Directory exclusion to skip irrelevant paths
        """
        files: List[Path] = []
        to_scan: List[tuple[Path, int]] = [(project_path, 0)]  # (path, depth)

        while to_scan:
            current_path, depth = to_scan.pop(0)

            # Stop at max depth
            if depth > self.max_scan_depth:
                continue

            try:
                for item in current_path.iterdir():
                    # Skip excluded directories
                    if item.is_dir():
                        if item.name not in self.EXCLUDED_DIRS:
                            to_scan.append((item, depth + 1))
                    elif item.is_file():
                        files.append(item)

            except PermissionError:
                logger.debug(f"Permission denied: {current_path}")
            except Exception as e:
                logger.debug(f"Error scanning {current_path}: {e}")

        return files

    def __repr__(self) -> str:
        """Return string representation."""
        return f"ToolchainDetector(max_scan_depth={self.max_scan_depth})"
