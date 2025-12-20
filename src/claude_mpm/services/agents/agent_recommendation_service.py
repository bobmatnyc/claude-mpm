"""Agent Recommendation Service

WHY: Provides intelligent agent recommendations based on toolchain detection
and always-recommended core agents. Helps users discover and install the
most relevant agents for their project without manual selection.

DESIGN DECISION: Uses toolchain analysis to map detected languages/frameworks
to specific engineer agents, plus always includes core agents.

Architecture:
- Toolchain-based recommendations: Python → python-engineer, etc.
- Core agents (always recommended): engineer, qa-agent, memory-manager-agent, local-ops-agent,
  research-agent, documentation-agent, security-agent
- Confidence-based filtering: Only recommend high-confidence detections
"""

from pathlib import Path
from typing import Dict, List, Optional, Set

from ...services.project.toolchain_analyzer import ToolchainAnalyzerService


class AgentRecommendationService:
    """Service for recommending agents based on project toolchain.

    WHY: Users shouldn't have to manually figure out which agents to install.
    This service provides intelligent recommendations based on detected stack.

    DESIGN DECISION: Separated from configure.py for reusability and testability.
    Can be used by CLI, API, or future auto-configuration features.
    """

    # Core agents always included - matches ToolchainDetector.CORE_AGENTS
    # Uses exact agent IDs from repository for consistency
    CORE_AGENTS = {
        "engineer",
        "qa-agent",
        "memory-manager-agent",
        "local-ops-agent",
        "research-agent",
        "documentation-agent",
        "security-agent",
    }

    # Map detected languages to recommended engineer agents
    LANGUAGE_TO_AGENTS: Dict[str, List[str]] = {
        "python": [
            "engineer/backend/python-engineer",
            "qa/api-qa",
        ],
        "javascript": [
            "engineer/backend/javascript-engineer",
            "engineer/data/typescript-engineer",
        ],
        "typescript": [
            "engineer/data/typescript-engineer",
            "engineer/backend/javascript-engineer",
        ],
        "rust": [
            "engineer/backend/rust-engineer",
        ],
        "go": [
            "engineer/backend/golang-engineer",
        ],
        "java": [
            "engineer/backend/java-engineer",
        ],
        "dart": [
            "engineer/mobile/dart-engineer",
        ],
        "php": [
            "engineer/backend/php-engineer",
        ],
        "ruby": [
            "engineer/backend/ruby-engineer",
        ],
        "swift": [
            "engineer/mobile/swift-engineer",
        ],
        "kotlin": [
            "engineer/mobile/kotlin-engineer",
        ],
    }

    # Map detected frameworks to recommended agents
    FRAMEWORK_TO_AGENTS: Dict[str, List[str]] = {
        # Frontend frameworks
        "react": [
            "engineer/frontend/react-engineer",
            "qa/web-qa",
        ],
        "nextjs": [
            "engineer/frontend/nextjs-engineer",
            "engineer/frontend/react-engineer",
            "ops/platform/vercel-ops",
        ],
        "vue": [
            "engineer/frontend/vue-engineer",
        ],
        "angular": [
            "engineer/frontend/angular-engineer",
        ],
        # Backend frameworks
        "fastapi": [
            "engineer/backend/python-engineer",
            "qa/api-qa",
        ],
        "django": [
            "engineer/backend/python-engineer",
            "qa/api-qa",
        ],
        "flask": [
            "engineer/backend/python-engineer",
            "qa/api-qa",
        ],
        "express": [
            "engineer/backend/javascript-engineer",
            "qa/api-qa",
        ],
        "nest": [
            "engineer/backend/javascript-engineer",
            "qa/api-qa",
        ],
        # Mobile frameworks
        "flutter": [
            "engineer/mobile/dart-engineer",
        ],
        "react-native": [
            "engineer/frontend/react-engineer",
            "engineer/mobile/react-native-engineer",
        ],
        # Desktop frameworks
        "tauri": [
            "engineer/mobile/tauri-engineer",
            "engineer/backend/rust-engineer",
        ],
        "electron": [
            "engineer/backend/javascript-engineer",
        ],
    }

    def __init__(self, toolchain_analyzer: Optional[ToolchainAnalyzerService] = None):
        """Initialize agent recommendation service.

        Args:
            toolchain_analyzer: Optional pre-initialized toolchain analyzer.
                               If None, creates a new instance.
        """
        self.toolchain_analyzer = toolchain_analyzer or ToolchainAnalyzerService()

    def get_recommended_agents(
        self,
        project_path: Optional[str] = None,
        confidence_threshold: float = 0.5,
    ) -> Set[str]:
        """Get recommended agents for a project.

        Args:
            project_path: Path to project directory. Defaults to cwd.
            confidence_threshold: Minimum confidence for recommendations (0.0-1.0).
                                 Only include detected components above this threshold.

        Returns:
            Set of recommended agent IDs (e.g., {"qa-agent", "research-agent", ...})

        Example:
            >>> service = AgentRecommendationService()
            >>> recommended = service.get_recommended_agents()
            >>> "qa-agent" in recommended
            True
            >>> # For Python project:
            >>> "engineer/backend/python-engineer" in recommended
            True
        """
        # Start with core agents (always recommended)
        recommended = self.CORE_AGENTS.copy()

        # Analyze project toolchain
        if project_path is None:
            project_path = str(Path.cwd())

        try:
            # ToolchainAnalyzerService.analyze_toolchain takes Path, not str
            analysis = self.toolchain_analyzer.analyze_toolchain(Path(project_path))
        except Exception as e:
            # If analysis fails, just return core agents
            print(f"Warning: Toolchain analysis failed: {e}")
            return recommended

        # Add language-specific agents
        # ToolchainAnalysis has a single LanguageDetection object, not a list
        if analysis.language_detection:
            # Check primary language
            primary_lang = analysis.language_detection.primary_language.lower()
            if primary_lang in self.LANGUAGE_TO_AGENTS:
                recommended.update(self.LANGUAGE_TO_AGENTS[primary_lang])

            # Check secondary languages
            for lang_component in analysis.language_detection.secondary_languages:
                lang = lang_component.name.lower()
                if lang in self.LANGUAGE_TO_AGENTS:
                    recommended.update(self.LANGUAGE_TO_AGENTS[lang])

        # Add framework-specific agents
        for framework in analysis.frameworks:
            fw_name = framework.name.lower()
            if fw_name in self.FRAMEWORK_TO_AGENTS:
                recommended.update(self.FRAMEWORK_TO_AGENTS[fw_name])

        return recommended

    def get_detection_summary(self, project_path: Optional[str] = None) -> Dict:
        """Get human-readable summary of detected toolchain.

        Args:
            project_path: Path to project directory. Defaults to cwd.

        Returns:
            Dict with keys:
            - detected_languages: List of detected language names
            - detected_frameworks: List of detected framework names
            - recommended_count: Number of recommended agents
            - detection_quality: "high", "medium", "low", or "none"

        Example:
            >>> summary = service.get_detection_summary()
            >>> summary['detected_languages']
            ['Python', 'JavaScript']
            >>> summary['recommended_count']
            15
        """
        if project_path is None:
            project_path = str(Path.cwd())

        try:
            analysis = self.toolchain_analyzer.analyze_toolchain(Path(project_path))

            # Extract languages from LanguageDetection object
            languages = []
            if analysis.language_detection:
                languages.append(analysis.language_detection.primary_language)
                languages.extend(
                    comp.name
                    for comp in analysis.language_detection.secondary_languages
                )

            # Extract frameworks
            frameworks = [fw.name for fw in analysis.frameworks]

            # Get recommended agents
            recommended = self.get_recommended_agents(project_path)

            # Determine detection quality from overall_confidence
            confidence_map = {
                "high": "high",
                "medium": "medium",
                "low": "low",
                "very_low": "low",
            }
            quality = confidence_map.get(
                str(analysis.overall_confidence).lower(), "unknown"
            )

            return {
                "detected_languages": languages,
                "detected_frameworks": frameworks,
                "recommended_count": len(recommended),
                "detection_quality": quality,
            }
        except Exception as e:
            # Log the error for debugging
            print(f"Warning: Toolchain analysis failed: {e}")
            return {
                "detected_languages": [],
                "detected_frameworks": [],
                "recommended_count": len(self.CORE_AGENTS),
                "detection_quality": "none",
            }
