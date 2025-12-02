"""
Toolchain Analyzer Service for Claude MPM Framework
===================================================

WHY: This service orchestrates multiple detection strategies to analyze
project toolchains. It provides comprehensive analysis of languages,
frameworks, and deployment targets for auto-configuration.

DESIGN DECISION: Uses Strategy pattern for pluggable detection strategies,
enabling easy addition of new language detectors. Implements dependency
injection for integration with existing ProjectAnalyzer.

Part of TSK-0054: Auto-Configuration Feature - Phase 2
"""

import time
from pathlib import Path
from typing import Dict, List, Optional

from ...core.base_service import BaseService
from ..core.interfaces.project import IToolchainAnalyzer
from ..core.models.toolchain import (
    ConfidenceLevel,
    DeploymentTarget,
    Framework,
    LanguageDetection,
    ToolchainAnalysis,
    ToolchainComponent,
)
from .detection_strategies import (
    GoDetectionStrategy,
    IToolchainDetectionStrategy,
    NodeJSDetectionStrategy,
    PythonDetectionStrategy,
    RustDetectionStrategy,
)


class ToolchainAnalyzerService(BaseService, IToolchainAnalyzer):
    """Service for analyzing project toolchains using pluggable strategies.

    WHY: Understanding project toolchain is essential for intelligent agent
    recommendations. This service provides comprehensive analysis with
    confidence scoring and evidence tracking.

    DESIGN DECISION: Separates detection logic into pluggable strategies,
    making it easy to add new language support. Uses dependency injection
    to integrate with existing ProjectAnalyzer for enhanced detection.
    """

    def __init__(
        self,
        project_analyzer: Optional[any] = None,
        dependency_analyzer: Optional[any] = None,
        config: Optional[Dict] = None,
    ):
        """Initialize the toolchain analyzer.

        Args:
            project_analyzer: Optional ProjectAnalyzer for enhanced detection
            dependency_analyzer: Optional DependencyAnalyzer for dependency parsing
            config: Optional configuration dictionary
        """
        super().__init__(
            name="ToolchainAnalyzer",
            config=config,
            enable_enhanced_features=False,
        )

        # Store dependencies
        self.project_analyzer = project_analyzer
        self.dependency_analyzer = dependency_analyzer

        # Initialize detection strategies
        self._strategies: Dict[str, IToolchainDetectionStrategy] = {}
        self._register_default_strategies()

        # Analysis cache
        self._cache: Dict[str, ToolchainAnalysis] = {}
        self._cache_ttl = 300  # 5 minutes

    def _register_default_strategies(self) -> None:
        """Register default detection strategies."""
        self.register_strategy("nodejs", NodeJSDetectionStrategy())
        self.register_strategy("python", PythonDetectionStrategy())
        self.register_strategy("rust", RustDetectionStrategy())
        self.register_strategy("go", GoDetectionStrategy())

    def register_strategy(
        self, name: str, strategy: IToolchainDetectionStrategy
    ) -> None:
        """Register a new detection strategy.

        WHY: Allows runtime registration of new detection strategies,
        enabling extensibility without modifying core code.

        Args:
            name: Unique name for the strategy
            strategy: Detection strategy instance
        """
        self._strategies[name] = strategy
        self.logger.debug(f"Registered detection strategy: {name}")

    async def _initialize(self) -> None:
        """Initialize the service."""
        self.logger.info("ToolchainAnalyzerService initialized")

    async def _cleanup(self) -> None:
        """Cleanup service resources."""
        self._cache.clear()
        self.logger.info("ToolchainAnalyzerService cleaned up")

    def analyze_toolchain(self, project_path: Path) -> ToolchainAnalysis:
        """Analyze project toolchain and dependencies.

        WHY: Provides complete toolchain analysis including languages,
        frameworks, build tools, and deployment targets in a single call.

        Args:
            project_path: Path to the project root directory

        Returns:
            ToolchainAnalysis: Complete analysis result with confidence scores

        Raises:
            FileNotFoundError: If project_path does not exist
            PermissionError: If project_path is not readable
        """
        # Validate project path
        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")
        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")

        # Check cache
        cache_key = str(project_path.absolute())
        cached = self._get_from_cache(cache_key)
        if cached:
            self.logger.debug(f"Using cached analysis for {project_path}")
            return cached

        self.logger.info(f"Analyzing toolchain for project: {project_path}")
        start_time = time.time()

        # Detect language
        language_detection = self.detect_language(project_path)

        # Detect frameworks
        frameworks = self.detect_frameworks(project_path)

        # Detect build tools and package managers
        build_tools = self._detect_build_tools(project_path)
        package_managers = self._detect_package_managers(project_path)

        # Detect development tools
        dev_tools = self._detect_development_tools(project_path)

        # Detect deployment target
        deployment_target = self.detect_deployment_target(project_path)

        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(
            language_detection, frameworks, deployment_target
        )

        # Create analysis result
        analysis = ToolchainAnalysis(
            project_path=project_path,
            language_detection=language_detection,
            frameworks=frameworks,
            deployment_target=deployment_target,
            build_tools=build_tools,
            package_managers=package_managers,
            development_tools=dev_tools,
            overall_confidence=overall_confidence,
            analysis_timestamp=time.time(),
            metadata={
                "analysis_duration_ms": (time.time() - start_time) * 1000,
                "strategies_used": list(self._strategies.keys()),
            },
        )

        # Cache the result
        self._add_to_cache(cache_key, analysis)

        duration_ms = (time.time() - start_time) * 1000
        self.logger.info(
            f"Toolchain analysis complete in {duration_ms:.2f}ms: "
            f"{language_detection.primary_language} with {len(frameworks)} frameworks"
        )

        return analysis

    def detect_language(self, project_path: Path) -> LanguageDetection:
        """Detect primary and secondary languages used in the project.

        WHY: Language detection is foundational for all other analysis.
        Multiple strategies are tried to ensure accurate detection.

        Args:
            project_path: Path to the project root directory

        Returns:
            LanguageDetection: Detected languages with confidence scores

        Raises:
            FileNotFoundError: If project_path does not exist
        """
        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        detections: List[LanguageDetection] = []

        # Run all strategies that can detect
        for strategy_name, strategy in self._strategies.items():
            try:
                if strategy.can_detect(project_path):
                    detection = strategy.detect_language(project_path)
                    if detection:
                        detections.append(detection)
                        self.logger.debug(
                            f"Strategy '{strategy_name}' detected: "
                            f"{detection.primary_language} "
                            f"(confidence: {detection.primary_confidence.value})"
                        )
            except Exception as e:
                self.logger.warning(
                    f"Strategy '{strategy_name}' failed: {e}", exc_info=True
                )

        # If no detections, return unknown
        if not detections:
            self.logger.warning(f"No language detected for {project_path}")
            return LanguageDetection(
                primary_language="Unknown",
                primary_confidence=ConfidenceLevel.VERY_LOW,
                secondary_languages=[],
                language_percentages={"Unknown": 100.0},
            )

        # If multiple detections, choose highest confidence
        if len(detections) > 1:
            # Sort by confidence level
            confidence_order = {
                ConfidenceLevel.HIGH: 4,
                ConfidenceLevel.MEDIUM: 3,
                ConfidenceLevel.LOW: 2,
                ConfidenceLevel.VERY_LOW: 1,
            }
            detections.sort(
                key=lambda d: confidence_order.get(d.primary_confidence, 0),
                reverse=True,
            )

            # Merge secondary languages from other detections
            primary = detections[0]
            for other in detections[1:]:
                # Add other primary languages as secondary
                if other.primary_language != primary.primary_language:
                    primary.secondary_languages.append(
                        ToolchainComponent(
                            name=other.primary_language,
                            version=other.primary_version,
                            confidence=other.primary_confidence,
                        )
                    )

        return detections[0]

    def detect_frameworks(self, project_path: Path) -> List[Framework]:
        """Detect frameworks and their versions.

        WHY: Framework detection enables targeted agent recommendations
        and provides context for development assistance.

        Args:
            project_path: Path to the project root directory

        Returns:
            List[Framework]: List of detected frameworks with versions and types

        Raises:
            FileNotFoundError: If project_path does not exist
        """
        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        all_frameworks: List[Framework] = []
        seen_frameworks: set = set()

        # Run all strategies that can detect
        for strategy_name, strategy in self._strategies.items():
            try:
                if strategy.can_detect(project_path):
                    frameworks = strategy.detect_frameworks(project_path)
                    for fw in frameworks:
                        # Deduplicate by name (case-insensitive)
                        fw_key = fw.name.lower()
                        if fw_key not in seen_frameworks:
                            all_frameworks.append(fw)
                            seen_frameworks.add(fw_key)
                            self.logger.debug(
                                f"Detected framework: {fw.name} "
                                f"(type: {fw.framework_type}, version: {fw.version})"
                            )
            except Exception as e:
                self.logger.warning(
                    f"Framework detection failed for '{strategy_name}': {e}",
                    exc_info=True,
                )

        # Sort by confidence and popularity
        all_frameworks.sort(
            key=lambda f: (
                (
                    4
                    if f.confidence == ConfidenceLevel.HIGH
                    else (
                        3
                        if f.confidence == ConfidenceLevel.MEDIUM
                        else 2
                        if f.confidence == ConfidenceLevel.LOW
                        else 1
                    )
                ),
                f.popularity_score,
            ),
            reverse=True,
        )

        return all_frameworks

    def detect_deployment_target(
        self, project_path: Path
    ) -> Optional[DeploymentTarget]:
        """Detect intended deployment environment.

        WHY: Deployment target affects agent recommendations (e.g., DevOps
        agents for Kubernetes, serverless agents for Lambda).

        Args:
            project_path: Path to the project root directory

        Returns:
            Optional[DeploymentTarget]: Detected deployment target or None if unclear

        Raises:
            FileNotFoundError: If project_path does not exist
        """
        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {project_path}")

        # Check for Docker
        if (project_path / "Dockerfile").exists() or (
            project_path / "docker-compose.yml"
        ).exists():
            return DeploymentTarget(
                target_type="container",
                platform="docker",
                confidence=ConfidenceLevel.HIGH,
                requires_ops_agent=True,
                metadata={
                    "docker_compose": (project_path / "docker-compose.yml").exists()
                },
            )

        # Check for Kubernetes
        if (project_path / "k8s").exists() or (project_path / "kubernetes").exists():
            return DeploymentTarget(
                target_type="container",
                platform="kubernetes",
                confidence=ConfidenceLevel.HIGH,
                requires_ops_agent=True,
            )

        # Check for Vercel
        if (project_path / "vercel.json").exists():
            return DeploymentTarget(
                target_type="serverless",
                platform="vercel",
                confidence=ConfidenceLevel.HIGH,
                requires_ops_agent=False,
            )

        # Check for AWS
        if (project_path / "serverless.yml").exists():
            return DeploymentTarget(
                target_type="serverless",
                platform="aws",
                confidence=ConfidenceLevel.MEDIUM,
                requires_ops_agent=True,
            )

        # Check for Terraform
        if list(project_path.glob("*.tf")):
            return DeploymentTarget(
                target_type="cloud",
                platform="terraform",
                confidence=ConfidenceLevel.MEDIUM,
                requires_ops_agent=True,
            )

        # Check for GCP
        if (project_path / "app.yaml").exists():
            return DeploymentTarget(
                target_type="cloud",
                platform="gcp",
                confidence=ConfidenceLevel.MEDIUM,
                requires_ops_agent=False,
            )

        # No clear deployment target
        self.logger.debug(f"No deployment target detected for {project_path}")
        return None

    def _detect_build_tools(self, project_path: Path) -> List[ToolchainComponent]:
        """Detect build tools used in the project."""
        build_tools = []

        # Check for common build tools
        build_indicators = {
            "webpack": ["webpack.config.js", "webpack.config.ts"],
            "vite": ["vite.config.js", "vite.config.ts"],
            "rollup": ["rollup.config.js"],
            "parcel": [".parcelrc"],
            "make": ["Makefile"],
            "cmake": ["CMakeLists.txt"],
            "gradle": ["build.gradle", "build.gradle.kts"],
            "maven": ["pom.xml"],
        }

        for tool_name, indicators in build_indicators.items():
            for indicator in indicators:
                if (project_path / indicator).exists():
                    build_tools.append(
                        ToolchainComponent(
                            name=tool_name,
                            confidence=ConfidenceLevel.HIGH,
                        )
                    )
                    break

        return build_tools

    def _detect_package_managers(self, project_path: Path) -> List[ToolchainComponent]:
        """Detect package managers used in the project."""
        package_managers = []

        # Check for package manager indicators
        pm_indicators = {
            "npm": ["package-lock.json"],
            "yarn": ["yarn.lock"],
            "pnpm": ["pnpm-lock.yaml"],
            "pip": ["requirements.txt"],
            "poetry": ["poetry.lock"],
            "pipenv": ["Pipfile.lock"],
            "cargo": ["Cargo.lock"],
            "go modules": ["go.sum"],
        }

        for pm_name, indicators in pm_indicators.items():
            for indicator in indicators:
                if (project_path / indicator).exists():
                    package_managers.append(
                        ToolchainComponent(
                            name=pm_name,
                            confidence=ConfidenceLevel.HIGH,
                        )
                    )
                    break

        return package_managers

    def _detect_development_tools(self, project_path: Path) -> List[ToolchainComponent]:
        """Detect development tools and utilities."""
        dev_tools = []

        # Check for common dev tools
        tool_indicators = {
            "docker": ["Dockerfile", "docker-compose.yml"],
            "kubernetes": ["k8s", "kubernetes"],
            "terraform": ["*.tf"],
            "git": [".git"],
            "pre-commit": [".pre-commit-config.yaml"],
            "eslint": [".eslintrc.js", ".eslintrc.json"],
            "prettier": [".prettierrc", ".prettierrc.json"],
            "black": ["pyproject.toml"],  # Could check for [tool.black]
        }

        for tool_name, indicators in tool_indicators.items():
            for indicator in indicators:
                if "*" in indicator:
                    # Glob pattern
                    if list(project_path.glob(indicator)):
                        dev_tools.append(
                            ToolchainComponent(
                                name=tool_name,
                                confidence=ConfidenceLevel.HIGH,
                            )
                        )
                        break
                # Direct path
                elif (project_path / indicator).exists():
                    dev_tools.append(
                        ToolchainComponent(
                            name=tool_name,
                            confidence=ConfidenceLevel.HIGH,
                        )
                    )
                    break

        return dev_tools

    def _calculate_overall_confidence(
        self,
        language_detection: LanguageDetection,
        frameworks: List[Framework],
        deployment_target: Optional[DeploymentTarget],
    ) -> ConfidenceLevel:
        """Calculate overall confidence for the analysis.

        WHY: Overall confidence helps users understand reliability of
        the complete analysis, not just individual components.
        """
        # Start with language detection confidence
        confidence_scores = {
            ConfidenceLevel.HIGH: 4,
            ConfidenceLevel.MEDIUM: 3,
            ConfidenceLevel.LOW: 2,
            ConfidenceLevel.VERY_LOW: 1,
        }

        scores = [confidence_scores.get(language_detection.primary_confidence, 1)]

        # Add framework confidence scores
        if frameworks:
            framework_avg = sum(
                confidence_scores.get(fw.confidence, 1) for fw in frameworks
            ) / len(frameworks)
            scores.append(framework_avg)

        # Add deployment target confidence if available
        if deployment_target:
            scores.append(confidence_scores.get(deployment_target.confidence, 1))

        # Calculate average
        avg_score = sum(scores) / len(scores)

        # Convert back to confidence level
        if avg_score >= 3.5:
            return ConfidenceLevel.HIGH
        if avg_score >= 2.5:
            return ConfidenceLevel.MEDIUM
        if avg_score >= 1.5:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.VERY_LOW

    def _get_from_cache(self, cache_key: str) -> Optional[ToolchainAnalysis]:
        """Get analysis from cache if valid."""
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            # Check if cache is still valid
            if cached.analysis_timestamp:
                age = time.time() - cached.analysis_timestamp
                if age < self._cache_ttl:
                    return cached
                # Remove stale cache
                del self._cache[cache_key]
        return None

    def _add_to_cache(self, cache_key: str, analysis: ToolchainAnalysis) -> None:
        """Add analysis to cache."""
        self._cache[cache_key] = analysis

        # Limit cache size
        if len(self._cache) > 100:
            # Remove oldest entries
            sorted_items = sorted(
                self._cache.items(),
                key=lambda x: x[1].analysis_timestamp or 0,
            )
            for key, _ in sorted_items[:-50]:  # Keep only 50 most recent
                del self._cache[key]
