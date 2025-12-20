"""Tests for ToolchainDetector service.

Tests toolchain detection from file patterns:
- Language detection (8 languages)
- Framework detection (6 frameworks)
- Build tool detection (4 tools)
- Agent recommendation mapping
- Edge cases and error handling
"""

from pathlib import Path

import pytest

from src.claude_mpm.services.agents.toolchain_detector import ToolchainDetector


class TestLanguageDetection:
    """Test language detection from file extensions and config files."""

    def test_detect_python_project(self, tmp_path: Path):
        """Test detecting Python project with multiple files."""
        # Create Python files
        (tmp_path / "main.py").touch()
        (tmp_path / "utils.py").touch()
        (tmp_path / "pyproject.toml").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        languages = detector.detect_languages(scanned_files, tmp_path)

        assert "python" in languages

    def test_detect_javascript_project(self, tmp_path: Path):
        """Test detecting JavaScript project."""
        (tmp_path / "index.js").touch()
        (tmp_path / "package.json").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        languages = detector.detect_languages(scanned_files, tmp_path)

        assert "javascript" in languages

    def test_detect_typescript_project(self, tmp_path: Path):
        """Test detecting TypeScript project."""
        (tmp_path / "app.ts").touch()
        (tmp_path / "tsconfig.json").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        languages = detector.detect_languages(scanned_files, tmp_path)

        assert "typescript" in languages

    def test_detect_go_project(self, tmp_path: Path):
        """Test detecting Go project."""
        (tmp_path / "main.go").touch()
        (tmp_path / "go.mod").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        languages = detector.detect_languages(scanned_files, tmp_path)

        assert "go" in languages

    def test_detect_rust_project(self, tmp_path: Path):
        """Test detecting Rust project."""
        (tmp_path / "main.rs").touch()
        (tmp_path / "Cargo.toml").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        languages = detector.detect_languages(scanned_files, tmp_path)

        assert "rust" in languages

    def test_detect_java_project(self, tmp_path: Path):
        """Test detecting Java project."""
        (tmp_path / "Main.java").touch()
        (tmp_path / "pom.xml").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        languages = detector.detect_languages(scanned_files, tmp_path)

        assert "java" in languages

    def test_detect_ruby_project(self, tmp_path: Path):
        """Test detecting Ruby project."""
        (tmp_path / "app.rb").touch()
        (tmp_path / "Gemfile").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        languages = detector.detect_languages(scanned_files, tmp_path)

        assert "ruby" in languages

    def test_detect_php_project(self, tmp_path: Path):
        """Test detecting PHP project."""
        (tmp_path / "index.php").touch()
        (tmp_path / "composer.json").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        languages = detector.detect_languages(scanned_files, tmp_path)

        assert "php" in languages

    def test_detect_multiple_languages(self, tmp_path: Path):
        """Test detecting project with multiple languages."""
        (tmp_path / "app.py").touch()
        (tmp_path / "frontend.js").touch()
        (tmp_path / "pyproject.toml").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        languages = detector.detect_languages(scanned_files, tmp_path)

        assert "python" in languages
        assert "javascript" in languages
        # May also detect typescript if package.json present
        assert len(languages) >= 2


class TestFrameworkDetection:
    """Test framework detection from config files and content markers."""

    def test_detect_fastapi_framework(self, tmp_path: Path):
        """Test detecting FastAPI framework."""
        # Create pyproject.toml with fastapi dependency
        (tmp_path / "pyproject.toml").write_text(
            """
[tool.poetry.dependencies]
python = "^3.9"
fastapi = "^0.95.0"
"""
        )

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        frameworks = detector.detect_frameworks(scanned_files, tmp_path)

        assert "fastapi" in frameworks

    def test_detect_django_framework(self, tmp_path: Path):
        """Test detecting Django framework."""
        (tmp_path / "manage.py").touch()
        (tmp_path / "settings.py").write_text(
            "DJANGO_SETTINGS_MODULE = 'myapp.settings'"
        )

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        frameworks = detector.detect_frameworks(scanned_files, tmp_path)

        assert "django" in frameworks

    def test_detect_react_framework(self, tmp_path: Path):
        """Test detecting React framework."""
        (tmp_path / "package.json").write_text(
            """
{
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
"""
        )

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        frameworks = detector.detect_frameworks(scanned_files, tmp_path)

        assert "react" in frameworks

    def test_detect_nextjs_framework(self, tmp_path: Path):
        """Test detecting Next.js framework."""
        (tmp_path / "next.config.js").touch()
        (tmp_path / "package.json").write_text(
            """
{
  "dependencies": {
    "next": "^13.0.0"
  }
}
"""
        )

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        frameworks = detector.detect_frameworks(scanned_files, tmp_path)

        assert "nextjs" in frameworks

    def test_detect_express_framework(self, tmp_path: Path):
        """Test detecting Express framework."""
        (tmp_path / "package.json").write_text(
            """
{
  "dependencies": {
    "express": "^4.18.0"
  }
}
"""
        )

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        frameworks = detector.detect_frameworks(scanned_files, tmp_path)

        assert "express" in frameworks

    def test_detect_spring_framework(self, tmp_path: Path):
        """Test detecting Spring Boot framework."""
        (tmp_path / "pom.xml").write_text(
            """
<project>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter</artifactId>
    </dependency>
  </dependencies>
</project>
"""
        )

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        frameworks = detector.detect_frameworks(scanned_files, tmp_path)

        assert "spring" in frameworks


class TestBuildToolDetection:
    """Test build tool detection from config files."""

    def test_detect_makefile(self, tmp_path: Path):
        """Test detecting Makefile."""
        (tmp_path / "Makefile").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        tools = detector.detect_build_tools(scanned_files, tmp_path)

        assert "make" in tools

    def test_detect_docker(self, tmp_path: Path):
        """Test detecting Docker."""
        (tmp_path / "Dockerfile").touch()
        (tmp_path / "docker-compose.yml").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        tools = detector.detect_build_tools(scanned_files, tmp_path)

        assert "docker" in tools

    def test_detect_npm(self, tmp_path: Path):
        """Test detecting npm."""
        (tmp_path / "package.json").touch()
        (tmp_path / "package-lock.json").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        tools = detector.detect_build_tools(scanned_files, tmp_path)

        assert "npm" in tools

    def test_detect_pip(self, tmp_path: Path):
        """Test detecting pip/Python packaging."""
        (tmp_path / "requirements.txt").touch()
        (tmp_path / "pyproject.toml").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        tools = detector.detect_build_tools(scanned_files, tmp_path)

        assert "pip" in tools


class TestFullToolchainDetection:
    """Test complete toolchain detection workflow."""

    def test_detect_python_fastapi_project(self, tmp_path: Path):
        """Test detecting Python + FastAPI + Docker project."""
        # Python files
        (tmp_path / "main.py").touch()
        (tmp_path / "pyproject.toml").write_text(
            """
[tool.poetry.dependencies]
fastapi = "^0.95.0"
"""
        )

        # Docker
        (tmp_path / "Dockerfile").touch()
        (tmp_path / "Makefile").touch()

        detector = ToolchainDetector()
        toolchain = detector.detect_toolchain(tmp_path)

        assert "python" in toolchain["languages"]
        assert "fastapi" in toolchain["frameworks"]
        assert "docker" in toolchain["build_tools"]
        assert "make" in toolchain["build_tools"]

    def test_detect_javascript_react_project(self, tmp_path: Path):
        """Test detecting JavaScript + React + npm project."""
        (tmp_path / "App.jsx").touch()
        (tmp_path / "package.json").write_text(
            """
{
  "dependencies": {
    "react": "^18.0.0"
  }
}
"""
        )

        detector = ToolchainDetector()
        toolchain = detector.detect_toolchain(tmp_path)

        assert "javascript" in toolchain["languages"]
        assert "react" in toolchain["frameworks"]
        assert "npm" in toolchain["build_tools"]

    def test_detect_empty_project(self, tmp_path: Path):
        """Test detecting project with no toolchain."""
        # Empty project
        detector = ToolchainDetector()
        toolchain = detector.detect_toolchain(tmp_path)

        assert len(toolchain["languages"]) == 0
        assert len(toolchain["frameworks"]) == 0
        assert len(toolchain["build_tools"]) == 0


class TestAgentRecommendation:
    """Test agent recommendation from toolchain."""

    def test_recommend_agents_python_project(self):
        """Test agent recommendations for Python project."""
        detector = ToolchainDetector()
        toolchain = {
            "languages": ["python"],
            "frameworks": [],
            "build_tools": ["pip"],
        }

        agents = detector.recommend_agents(toolchain)

        assert "python-engineer" in agents
        # Core agents should always be included
        assert "qa-agent" in agents
        assert "research-agent" in agents
        assert "documentation-agent" in agents
        assert "memory-manager-agent" in agents
        assert "local-ops-agent" in agents
        assert "security-agent" in agents

    def test_recommend_agents_python_fastapi_docker(self):
        """Test recommendations for Python + FastAPI + Docker."""
        detector = ToolchainDetector()
        toolchain = {
            "languages": ["python"],
            "frameworks": ["fastapi"],
            "build_tools": ["docker", "make"],
        }

        agents = detector.recommend_agents(toolchain)

        assert "python-engineer" in agents
        assert "ops" in agents or "local-ops-agent" in agents
        # Core agents
        assert "qa-agent" in agents
        assert "research-agent" in agents
        assert "documentation-agent" in agents
        assert "memory-manager-agent" in agents
        assert "local-ops-agent" in agents
        assert "security-agent" in agents

    def test_recommend_agents_javascript_react(self):
        """Test recommendations for JavaScript + React."""
        detector = ToolchainDetector()
        toolchain = {
            "languages": ["javascript"],
            "frameworks": ["react"],
            "build_tools": ["npm"],
        }

        agents = detector.recommend_agents(toolchain)

        assert "react-engineer" in agents
        # Core agents
        assert "qa-agent" in agents
        assert "research-agent" in agents

    def test_recommend_agents_no_toolchain(self):
        """Test recommendations for project with no detected toolchain."""
        detector = ToolchainDetector()
        toolchain = {
            "languages": [],
            "frameworks": [],
            "build_tools": [],
        }

        agents = detector.recommend_agents(toolchain)

        # Should fall back to generic engineer
        assert "engineer" in agents
        # Core agents should still be included
        assert "qa-agent" in agents
        assert "research-agent" in agents

    def test_recommend_agents_multi_language(self):
        """Test recommendations for multi-language project."""
        detector = ToolchainDetector()
        toolchain = {
            "languages": ["python", "javascript"],
            "frameworks": [],
            "build_tools": [],
        }

        agents = detector.recommend_agents(toolchain)

        assert "python-engineer" in agents
        assert "javascript-engineer-agent" in agents
        # No duplicates
        assert len(agents) == len(set(agents))


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_detect_nonexistent_path(self):
        """Test detection on nonexistent path."""
        detector = ToolchainDetector()
        toolchain = detector.detect_toolchain(Path("/nonexistent/path"))

        assert len(toolchain["languages"]) == 0
        assert len(toolchain["frameworks"]) == 0
        assert len(toolchain["build_tools"]) == 0

    def test_detect_file_instead_of_directory(self, tmp_path: Path):
        """Test detection on file instead of directory."""
        test_file = tmp_path / "test.py"
        test_file.touch()

        detector = ToolchainDetector()
        toolchain = detector.detect_toolchain(test_file)

        assert len(toolchain["languages"]) == 0
        assert len(toolchain["frameworks"]) == 0
        assert len(toolchain["build_tools"]) == 0

    def test_scan_respects_max_depth(self, tmp_path: Path):
        """Test that file scanning respects max_depth."""
        # Create nested directory structure
        deep_dir = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep.py").touch()

        # Scan with depth 2 (should not reach deep.py)
        detector = ToolchainDetector(max_scan_depth=2)
        scanned_files = detector._scan_files(tmp_path)

        assert all(len(f.relative_to(tmp_path).parts) <= 3 for f in scanned_files)

    def test_scan_excludes_common_directories(self, tmp_path: Path):
        """Test that common directories are excluded from scanning."""
        # Create excluded directories
        excluded_dirs = [".git", "node_modules", "venv", "__pycache__"]
        for dirname in excluded_dirs:
            excluded_dir = tmp_path / dirname
            excluded_dir.mkdir()
            (excluded_dir / "test.py").touch()

        # Create non-excluded file
        (tmp_path / "main.py").touch()

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)

        # Only main.py should be scanned
        assert len([f for f in scanned_files if f.name == "test.py"]) == 0
        assert len([f for f in scanned_files if f.name == "main.py"]) == 1

    def test_framework_detection_invalid_json(self, tmp_path: Path):
        """Test framework detection with invalid JSON in config file."""
        (tmp_path / "package.json").write_text("invalid json {")

        detector = ToolchainDetector()
        scanned_files = detector._scan_files(tmp_path)
        # Should not crash, just return empty frameworks
        frameworks = detector.detect_frameworks(scanned_files, tmp_path)

        # Should gracefully handle error and not detect any frameworks
        assert isinstance(frameworks, list)

    def test_repr_method(self):
        """Test __repr__ method."""
        detector = ToolchainDetector(max_scan_depth=5)
        repr_str = repr(detector)

        assert "ToolchainDetector" in repr_str
        assert "5" in repr_str


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_workflow_python_project(self, tmp_path: Path):
        """Test complete workflow from detection to recommendation."""
        # Create Python FastAPI project structure
        (tmp_path / "main.py").touch()
        (tmp_path / "api").mkdir()
        (tmp_path / "api" / "routes.py").touch()
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").touch()

        (tmp_path / "pyproject.toml").write_text(
            """
[tool.poetry.dependencies]
python = "^3.9"
fastapi = "^0.95.0"
uvicorn = "^0.21.0"
"""
        )

        (tmp_path / "Dockerfile").touch()
        (tmp_path / "Makefile").touch()

        # Run detection
        detector = ToolchainDetector()
        toolchain = detector.detect_toolchain(tmp_path)

        # Verify detection
        assert "python" in toolchain["languages"]
        assert "fastapi" in toolchain["frameworks"]
        assert "docker" in toolchain["build_tools"]
        assert "make" in toolchain["build_tools"]

        # Get recommendations
        agents = detector.recommend_agents(toolchain)

        # Verify recommendations include specialized agents
        assert "python-engineer" in agents
        assert any(agent in agents for agent in ["ops", "local-ops-agent"])

        # Verify core agents included
        for core_agent in ["qa-agent", "research-agent", "documentation-agent",
                          "memory-manager-agent", "local-ops-agent", "security-agent"]:
            assert core_agent in agents

    def test_full_workflow_javascript_project(self, tmp_path: Path):
        """Test complete workflow for JavaScript/React project."""
        # Create React project structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "App.jsx").touch()
        (tmp_path / "src" / "index.js").touch()

        (tmp_path / "package.json").write_text(
            """
{
  "name": "my-app",
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
"""
        )

        (tmp_path / "package-lock.json").touch()

        # Run detection
        detector = ToolchainDetector()
        toolchain = detector.detect_toolchain(tmp_path)

        # Verify detection
        assert "javascript" in toolchain["languages"]
        assert "react" in toolchain["frameworks"]
        assert "npm" in toolchain["build_tools"]

        # Get recommendations
        agents = detector.recommend_agents(toolchain)

        # Verify recommendations
        assert "react-engineer" in agents
        assert "qa-agent" in agents
        assert "research-agent" in agents
