"""
Project Management Services Module
==================================

This module contains all project-related services including
project analysis and registry management.

Part of TSK-0046: Service Layer Architecture Reorganization
Part of TSK-0054: Auto-Configuration Feature - Phase 2

Services:
- ProjectAnalyzer: Analyzes project structure and metadata
- ProjectRegistry: Manages project registration and discovery
- ToolchainAnalyzerService: Analyzes project toolchains for auto-configuration

Detection Strategies:
- NodeJSDetectionStrategy: Detects Node.js projects
- PythonDetectionStrategy: Detects Python projects
- RustDetectionStrategy: Detects Rust projects
- GoDetectionStrategy: Detects Go projects
- IToolchainDetectionStrategy: Base interface for detection strategies
"""

from .analyzer import ProjectAnalyzer
from .detection_strategies import (
    GoDetectionStrategy,
    IToolchainDetectionStrategy,
    NodeJSDetectionStrategy,
    PythonDetectionStrategy,
    RustDetectionStrategy,
)
from .registry import ProjectRegistry
from .toolchain_analyzer import ToolchainAnalyzerService

__all__ = [
    "GoDetectionStrategy",
    "IToolchainDetectionStrategy",
    "NodeJSDetectionStrategy",
    "ProjectAnalyzer",
    "ProjectRegistry",
    "PythonDetectionStrategy",
    "RustDetectionStrategy",
    "ToolchainAnalyzerService",
]
