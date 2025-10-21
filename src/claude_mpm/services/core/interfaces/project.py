"""
Project Analysis Interfaces for Claude MPM Framework
====================================================

WHY: This module contains interfaces for project analysis, toolchain detection,
and technology stack identification. These interfaces enable the auto-configuration
system to intelligently recommend agents based on detected project characteristics.

DESIGN DECISION: Project analysis interfaces are separated because they deal
with understanding the codebase structure, dependencies, and toolchain setup,
which requires different patterns than other service types.

Part of TSK-0054: Auto-Configuration Feature - Phase 1
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from ..models.toolchain import (
    DeploymentTarget,
    Framework,
    LanguageDetection,
    ToolchainAnalysis,
)


class IToolchainAnalyzer(ABC):
    """Interface for toolchain analysis operations.

    WHY: Understanding project toolchain is essential for recommending appropriate
    agents. This interface abstracts toolchain analysis to support different
    project types, languages, and frameworks.

    DESIGN DECISION: Separates language, framework, and deployment detection
    into distinct methods to enable granular analysis and caching of results.
    Each analysis type can be run independently based on needs.
    """

    @abstractmethod
    def analyze_toolchain(self, project_path: Path) -> ToolchainAnalysis:
        """Analyze project toolchain and dependencies.

        Performs comprehensive analysis of the project's technical stack including:
        - Primary and secondary programming languages
        - Framework and library dependencies
        - Build and deployment configuration
        - Development environment requirements

        Args:
            project_path: Path to the project root directory

        Returns:
            ToolchainAnalysis: Complete analysis result with confidence scores

        Raises:
            FileNotFoundError: If project_path does not exist
            PermissionError: If project_path is not readable
        """

    @abstractmethod
    def detect_language(self, project_path: Path) -> LanguageDetection:
        """Detect primary and secondary languages used in the project.

        Analyzes source files to determine:
        - Primary programming language (highest code volume)
        - Secondary languages (supporting code, scripts)
        - Language versions if detectable
        - Confidence level for each detection

        Args:
            project_path: Path to the project root directory

        Returns:
            LanguageDetection: Detected languages with confidence scores

        Raises:
            FileNotFoundError: If project_path does not exist
        """

    @abstractmethod
    def detect_frameworks(self, project_path: Path) -> List[Framework]:
        """Detect frameworks and their versions.

        Identifies frameworks by analyzing:
        - Dependency files (package.json, requirements.txt, etc.)
        - Import statements in source code
        - Configuration files specific to frameworks
        - Project structure patterns

        Args:
            project_path: Path to the project root directory

        Returns:
            List[Framework]: List of detected frameworks with versions and types

        Raises:
            FileNotFoundError: If project_path does not exist
        """

    @abstractmethod
    def detect_deployment_target(
        self, project_path: Path
    ) -> Optional[DeploymentTarget]:
        """Detect intended deployment environment.

        Analyzes configuration to identify deployment targets:
        - Cloud platforms (AWS, GCP, Azure)
        - Container orchestration (Kubernetes, Docker)
        - Serverless platforms (Lambda, Cloud Functions)
        - Traditional hosting (VPS, dedicated servers)

        Args:
            project_path: Path to the project root directory

        Returns:
            Optional[DeploymentTarget]: Detected deployment target or None if unclear

        Raises:
            FileNotFoundError: If project_path does not exist
        """
