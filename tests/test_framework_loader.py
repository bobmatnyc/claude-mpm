"""Tests for framework loader functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from claude_mpm.core.framework_loader import FrameworkLoader


class TestFrameworkLoader:
    """Test the FrameworkLoader class."""
    
    def test_init_with_explicit_path(self, tmp_path):
        """Test initialization with explicit framework path."""
        # Create mock framework structure
        framework_dir = tmp_path / "test-framework"
        framework_dir.mkdir()
        (framework_dir / "framework").mkdir()
        
        # Create agents directory with at least one agent file
        agents_dir = framework_dir / "src" / "claude_mpm" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test_agent.md").write_text("# Test Agent")
        
        # Create mock INSTRUCTIONS.md (or CLAUDE.md for legacy)
        instructions_md = framework_dir / "framework" / "INSTRUCTIONS.md"
        instructions_md.write_text("# Test Framework")
        
        loader = FrameworkLoader(framework_path=framework_dir)
        assert loader.framework_path == framework_dir
        assert loader.framework_content['loaded'] is True
        # Framework content might be empty if no working directory INSTRUCTIONS.md
    
    def test_auto_detect_framework(self, tmp_path, monkeypatch):
        """Test auto-detection of framework path."""
        # Create mock framework in home directory
        mock_home = tmp_path / "home"
        mock_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: mock_home)
        
        framework_dir = mock_home / "Projects" / "claude-multiagent-pm"
        framework_dir.mkdir(parents=True)
        (framework_dir / "framework").mkdir()
        
        # Create agents directory
        agents_dir = framework_dir / "src" / "claude_mpm" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test_agent.md").write_text("# Test Agent")
        
        (framework_dir / "framework" / "INSTRUCTIONS.md").write_text("# Auto Detected")
        
        loader = FrameworkLoader()
        assert loader.framework_path == framework_dir
        # Framework content might be empty if no working directory INSTRUCTIONS.md
    
    def test_no_framework_found(self, tmp_path, monkeypatch):
        """Test behavior when no framework is found."""
        # Mock empty home directory
        mock_home = tmp_path / "empty_home"
        mock_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: mock_home)
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        
        loader = FrameworkLoader()
        assert loader.framework_path is None
        assert loader.framework_content['loaded'] is False
    
    def test_load_agent_definitions(self, tmp_path):
        """Test loading agent definitions."""
        # Create framework with agents
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        (framework_dir / "framework").mkdir()
        (framework_dir / "framework" / "CLAUDE.md").write_text("# Framework")
        
        # Create agent definitions
        agents_dir = framework_dir / "framework" / "agent-roles"
        agents_dir.mkdir()
        (agents_dir / "engineer.md").write_text("# Engineer Agent")
        (agents_dir / "qa.md").write_text("# QA Agent")
        
        loader = FrameworkLoader(framework_path=framework_dir)
        assert "engineer" in loader.framework_content['agents']
        assert "qa" in loader.framework_content['agents']
        assert "Engineer Agent" in loader.framework_content['agents']['engineer']
    
    def test_load_version(self, tmp_path):
        """Test loading framework version."""
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        (framework_dir / "framework").mkdir()
        (framework_dir / "framework" / "CLAUDE.md").write_text("# Framework")
        (framework_dir / "framework" / "VERSION").write_text("015")
        
        loader = FrameworkLoader(framework_path=framework_dir)
        assert loader.framework_content['version'] == "015"
    
    def test_get_framework_instructions_full(self, tmp_path):
        """Test getting full framework instructions."""
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        (framework_dir / "framework").mkdir()
        (framework_dir / "framework" / "CLAUDE.md").write_text("# Full Framework Instructions")
        (framework_dir / "framework" / "VERSION").write_text("016")
        
        loader = FrameworkLoader(framework_path=framework_dir)
        instructions = loader.get_framework_instructions()
        
        assert "Full Framework Instructions" in instructions
        assert "Version: 016" in instructions
        assert "Framework injected by Claude MPM" in instructions
    
    def test_get_framework_instructions_minimal(self):
        """Test getting minimal framework instructions when no framework found."""
        loader = FrameworkLoader(framework_path=None)
        instructions = loader.get_framework_instructions()
        
        assert "Claude PM Framework Instructions" in instructions
        assert "multi-agent orchestrator" in instructions
        assert "Core Agents" in instructions
        assert "Important Rules" in instructions
    
    def test_get_agent_list(self, tmp_path):
        """Test getting list of available agents."""
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        (framework_dir / "framework").mkdir()
        (framework_dir / "framework" / "CLAUDE.md").write_text("# Framework")
        
        agents_dir = framework_dir / "framework" / "agent-roles"
        agents_dir.mkdir()
        (agents_dir / "engineer.md").write_text("# Engineer")
        (agents_dir / "qa.md").write_text("# QA")
        (agents_dir / "researcher.md").write_text("# Researcher")
        
        loader = FrameworkLoader(framework_path=framework_dir)
        agent_list = loader.get_agent_list()
        
        assert len(agent_list) == 3
        assert "engineer" in agent_list
        assert "qa" in agent_list
        assert "researcher" in agent_list
    
    def test_get_agent_definition(self, tmp_path):
        """Test getting specific agent definition."""
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        (framework_dir / "framework").mkdir()
        (framework_dir / "framework" / "CLAUDE.md").write_text("# Framework")
        
        agents_dir = framework_dir / "framework" / "agent-roles"
        agents_dir.mkdir()
        (agents_dir / "engineer.md").write_text("# Engineer Agent\nImplements code")
        
        loader = FrameworkLoader(framework_path=framework_dir)
        
        # Test existing agent
        engineer_def = loader.get_agent_definition("engineer")
        assert engineer_def is not None
        assert "Engineer Agent" in engineer_def
        assert "Implements code" in engineer_def
        
        # Test non-existing agent
        assert loader.get_agent_definition("nonexistent") is None
    
    @patch('subprocess.run')
    def test_npm_global_path_detection(self, mock_run, tmp_path):
        """Test npm global path detection."""
        # Mock npm command output
        npm_root = tmp_path / "npm" / "global"
        npm_root.mkdir(parents=True)
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=str(npm_root) + "\n"
        )
        
        # Create framework in npm global location
        framework_dir = npm_root / "@bobmatnyc" / "claude-multiagent-pm"
        framework_dir.mkdir(parents=True)
        (framework_dir / "framework").mkdir()
        (framework_dir / "framework" / "CLAUDE.md").write_text("# NPM Framework")
        
        loader = FrameworkLoader()
        npm_path = loader._get_npm_global_path()
        
        assert npm_path is not None
        assert "@bobmatnyc" in str(npm_path)
    
    def test_error_handling_corrupt_files(self, tmp_path, caplog):
        """Test handling of corrupt or inaccessible files."""
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        (framework_dir / "framework").mkdir()
        
        # Create unreadable file (simulate permission error)
        claude_md = framework_dir / "framework" / "CLAUDE.md"
        claude_md.write_text("test")
        
        # Mock read_text to raise exception
        with patch.object(Path, 'read_text', side_effect=PermissionError("Access denied")):
            loader = FrameworkLoader(framework_path=framework_dir)
            assert loader.framework_content['loaded'] is False
            assert "Failed to load CLAUDE.md" in caplog.text