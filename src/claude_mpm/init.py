"""Initialization module for claude-mpm.

Handles creation of necessary directories and configuration files.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import json

from claude_mpm.core.logger import get_logger


class ProjectInitializer:
    """Handles initialization of claude-mpm directories and configuration."""
    
    def __init__(self):
        self.logger = get_logger("initializer")
        self.user_dir = Path.home() / ".claude-mpm"
        self.project_dir = None
        
    def initialize_user_directory(self) -> bool:
        """Initialize user-level .claude-mpm directory structure.
        
        Creates:
        - ~/.claude-mpm/
          - agents/
            - user-defined/
          - config/
          - logs/
          - templates/
        """
        try:
            # Create main user directory
            self.user_dir.mkdir(exist_ok=True)
            
            # Create subdirectories
            directories = [
                self.user_dir / "agents" / "user-defined",
                self.user_dir / "config",
                self.user_dir / "logs",
                self.user_dir / "templates",
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
            
            # Create default configuration if it doesn't exist
            config_file = self.user_dir / "config" / "settings.json"
            if not config_file.exists():
                self._create_default_config(config_file)
            
            # Copy agent templates if they don't exist
            self._copy_agent_templates()
            
            self.logger.info(f"Initialized user directory at {self.user_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize user directory: {e}")
            return False
    
    def initialize_project_directory(self, project_path: Optional[Path] = None) -> bool:
        """Initialize project-level .claude-mpm directory structure.
        
        Creates:
        - .claude-mpm/
          - agents/
            - project-specific/
          - config/
          - logs/
        """
        try:
            # Find project root
            if project_path:
                self.project_dir = project_path / ".claude-mpm"
            else:
                project_root = self._find_project_root()
                if not project_root:
                    project_root = Path.cwd()
                self.project_dir = project_root / ".claude-mpm"
            
            # Create project directory
            self.project_dir.mkdir(exist_ok=True)
            
            # Create subdirectories
            directories = [
                self.project_dir / "agents" / "project-specific",
                self.project_dir / "config",
                self.project_dir / "logs",
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
            
            # Create project configuration
            config_file = self.project_dir / "config" / "project.json"
            if not config_file.exists():
                self._create_project_config(config_file)
            
            # Create .gitignore for project directory
            gitignore = self.project_dir / ".gitignore"
            if not gitignore.exists():
                gitignore.write_text("logs/\n*.log\n*.pyc\n__pycache__/\n")
            
            self.logger.info(f"Initialized project directory at {self.project_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize project directory: {e}")
            return False
    
    def _find_project_root(self) -> Optional[Path]:
        """Find project root by looking for .git or other project markers."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            if (current / "pyproject.toml").exists():
                return current
            if (current / "setup.py").exists():
                return current
            current = current.parent
        return None
    
    def _create_default_config(self, config_file: Path):
        """Create default user configuration."""
        default_config = {
            "version": "1.0",
            "hooks": {
                "enabled": True,
                "port_range": [8080, 8099]
            },
            "logging": {
                "level": "INFO",
                "max_size_mb": 100,
                "retention_days": 30
            },
            "agents": {
                "auto_discover": True,
                "precedence": ["project", "user", "system"]
            },
            "orchestration": {
                "default_mode": "subprocess",
                "enable_todo_hijacking": False
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
    
    def _create_project_config(self, config_file: Path):
        """Create default project configuration."""
        project_config = {
            "version": "1.0",
            "project_name": Path.cwd().name,
            "agents": {
                "enabled": True
            },
            "tickets": {
                "auto_create": True,
                "prefix": "TSK"
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(project_config, f, indent=2)
    
    def _copy_agent_templates(self):
        """Copy agent templates to user directory."""
        # Get the package directory
        package_dir = Path(__file__).parent
        templates_src = package_dir / "agents" / "templates"
        templates_dst = self.user_dir / "templates"
        
        if templates_src.exists():
            for template_file in templates_src.glob("*.md"):
                dst_file = templates_dst / template_file.name
                if not dst_file.exists():
                    shutil.copy2(template_file, dst_file)
    
    def validate_dependencies(self) -> Dict[str, bool]:
        """Validate that all required dependencies are available."""
        dependencies = {}
        
        # Check Python version
        import sys
        dependencies['python'] = sys.version_info >= (3, 8)
        
        # Check Claude CLI
        dependencies['claude_cli'] = shutil.which("claude") is not None
        
        # Check required Python packages
        required_packages = [
            'ai_trackdown_pytools',
            'yaml',
            'dotenv',
            'rich',
            'click',
            'pexpect',
            'psutil',
            'requests',
            'flask',
            'watchdog',
            'tree_sitter'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                dependencies[package] = True
            except ImportError:
                dependencies[package] = False
        
        return dependencies
    
    def ensure_initialized(self) -> bool:
        """Ensure both user and project directories are initialized."""
        user_ok = self.initialize_user_directory()
        project_ok = self.initialize_project_directory()
        return user_ok and project_ok


def ensure_directories():
    """Convenience function to ensure directories are initialized."""
    initializer = ProjectInitializer()
    return initializer.ensure_initialized()


def validate_installation():
    """Validate that claude-mpm is properly installed."""
    initializer = ProjectInitializer()
    deps = initializer.validate_dependencies()
    
    all_ok = all(deps.values())
    
    if not all_ok:
        print("❌ Missing dependencies:")
        for dep, status in deps.items():
            if not status:
                print(f"  - {dep}")
    else:
        print("✅ All dependencies are installed")
    
    return all_ok