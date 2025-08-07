#!/usr/bin/env python3
"""Setup script for claude-mpm."""

from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
import os
import sys
import shutil
from pathlib import Path

# Read version from VERSION file - single source of truth
version_file = Path(__file__).parent / "VERSION"
if version_file.exists():
    __version__ = version_file.read_text().strip()
else:
    # Default version if VERSION file is missing
    __version__ = "0.0.0"
    print("WARNING: VERSION file not found, using default version 0.0.0", file=sys.stderr)


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        self.execute(self._post_install, [], msg="Running post-installation setup...")

    def _post_install(self):
        """Create necessary directories and install ticket alias."""
        # Create user .claude-mpm directory
        user_dir = Path.home() / ".claude-mpm"
        user_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (user_dir / "agents" / "user-defined").mkdir(parents=True, exist_ok=True)
        (user_dir / "logs").mkdir(exist_ok=True)
        (user_dir / "config").mkdir(exist_ok=True)
        
        # Install ticket command
        self._install_ticket_command()
    
    def _install_ticket_command(self):
        """Install ticket command wrapper."""
        import site
        
        # Get the scripts directory
        if hasattr(site, 'USER_BASE'):
            scripts_dir = Path(site.USER_BASE) / "bin"
        else:
            scripts_dir = Path(sys.prefix) / "bin"
        
        scripts_dir.mkdir(exist_ok=True)
        
        # Create ticket wrapper script
        ticket_script = scripts_dir / "ticket"
        ticket_content = '''#!/usr/bin/env python3
"""Ticket command wrapper for claude-mpm."""
import sys
from claude_mpm.ticket_wrapper import main

if __name__ == "__main__":
    sys.exit(main())
'''
        ticket_script.write_text(ticket_content)
        ticket_script.chmod(0o755)


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        develop.run(self)
        self.execute(self._post_develop, [], msg="Running post-development setup...")

    def _post_develop(self):
        """Create necessary directories for development."""
        PostInstallCommand._post_install(self)


def read_requirements():
    """Read requirements from requirements.txt if it exists."""
    req_file = Path(__file__).parent / "requirements.txt"
    if req_file.exists():
        with open(req_file, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []


setup(
    name="claude-mpm",
    version=__version__,
    description="Claude Multi-Agent Project Manager - Orchestrate Claude with agent delegation and ticket tracking",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Bob Matsuoka",
    author_email="bob@matsuoka.com",
    url="https://github.com/bobmatnyc/claude-mpm",
    license="MIT",
    python_requires=">=3.8",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    install_requires=read_requirements() or [
        "ai-trackdown-pytools>=1.4.0",
        "pyyaml>=6.0",
        "python-dotenv>=0.19.0",
        "rich>=13.0.0",
        "click>=8.0.0",
        "pexpect>=4.8.0",
        "psutil>=5.9.0",
        "requests>=2.25.0",
        "flask>=3.0.0",
        "flask-cors>=4.0.0",
        "watchdog>=3.0.0",
        "tree-sitter>=0.21.0",
        "tree-sitter-language-pack>=0.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ],
        "ui": [
            "rich>=13.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "claude-mpm=claude_mpm.cli:main",
            "ticket=claude_mpm.ticket_wrapper:main",
        ],
    },
    cmdclass={
        'install': PostInstallCommand,
        'develop': PostDevelopCommand,
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="claude ai orchestration multi-agent project-management",
)