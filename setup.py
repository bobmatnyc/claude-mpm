#!/usr/bin/env python3
"""Setup script for claude-mpm."""

from setuptools import setup, find_packages
import os
import sys

# Add src to path to import version
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from claude_mpm._version import __version__

setup(
    name="claude-mpm",
    version=__version__,
    description="Claude Multi-Agent Project Manager - Orchestrate Claude with agent delegation and ticket tracking",
    author="Claude MPM Team",
    python_requires=">=3.8",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "ai-trackdown-pytools>=0.1.0",
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
        "tree-sitter-language-pack>=0.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ]
    },
    entry_points={
        "console_scripts": [
            "claude-mpm=claude_mpm.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)