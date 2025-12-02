"""Agent configuration provider for deployment service.

This module provides agent-specific configurations and tools for different agent types.
Extracted from AgentDeploymentService to reduce complexity and improve maintainability.
"""

from typing import Any, Dict, List

from claude_mpm.core.constants import ResourceLimits, SystemLimits, TimeoutConfig


class AgentConfigProvider:
    """Provides agent-specific configurations and tools."""

    @staticmethod
    def get_agent_tools(agent_name: str, metadata: Dict[str, Any]) -> List[str]:
        """
        Get appropriate tools for an agent based on its type.

        Args:
            agent_name: Name of the agent
            metadata: Agent metadata

        Returns:
            List of tool names
        """
        # Base tools all agents should have
        base_tools = [
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Grep",
            "Glob",
            "LS",
            "TodoWrite",
        ]

        # Agent-specific tools
        agent_tools = {
            "engineer": [*base_tools, "Bash", "WebSearch", "WebFetch"],
            "qa": [*base_tools, "Bash", "WebSearch"],
            "documentation": [*base_tools, "WebSearch", "WebFetch"],
            "research": [*base_tools, "WebSearch", "WebFetch", "Bash"],
            "security": [*base_tools, "Bash", "WebSearch", "Grep"],
            "ops": [*base_tools, "Bash", "WebSearch"],
            "data_engineer": [*base_tools, "Bash", "WebSearch"],
            "version_control": [*base_tools, "Bash"],
        }

        # Return specific tools or default set
        return agent_tools.get(agent_name, [*base_tools, "Bash", "WebSearch"])

    @staticmethod
    def get_agent_specific_config(agent_name: str) -> Dict[str, Any]:
        """
        Get agent-specific configuration based on agent type.

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary of agent-specific configuration
        """
        # Base configuration all agents share
        base_config = {
            "timeout": TimeoutConfig.DEFAULT_TIMEOUT,
            "max_tokens": SystemLimits.MAX_TOKEN_LIMIT,
            "memory_limit": ResourceLimits.STANDARD_MEMORY_RANGE[
                0
            ],  # Use lower bound of standard memory
            "cpu_limit": ResourceLimits.STANDARD_CPU_RANGE[
                1
            ],  # Use upper bound of standard CPU
            "network_access": True,
        }

        # Agent-specific configurations
        configs = AgentConfigProvider._get_agent_configs(base_config)

        # Return the specific config or a default
        return configs.get(
            agent_name, AgentConfigProvider._get_default_config(agent_name, base_config)
        )

    @staticmethod
    def _get_agent_configs(base_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Get all agent-specific configurations."""
        return {
            "engineer": {
                **base_config,
                "description": "Code implementation, development, and inline documentation",
                "tags": ["engineer", "development", "coding", "implementation"],
                "tools": [
                    "Read",
                    "Write",
                    "Edit",
                    "MultiEdit",
                    "Bash",
                    "Grep",
                    "Glob",
                    "LS",
                    "WebSearch",
                    "TodoWrite",
                ],
                "temperature": 0.2,
                "when_to_use": [
                    "Code implementation needed",
                    "Bug fixes required",
                    "Refactoring tasks",
                ],
                "specialized_knowledge": [
                    "Programming best practices",
                    "Design patterns",
                    "Code optimization",
                ],
                "unique_capabilities": [
                    "Write production code",
                    "Debug complex issues",
                    "Refactor codebases",
                ],
                "primary_role": "Code implementation and development",
                "specializations": [
                    "coding",
                    "debugging",
                    "refactoring",
                    "optimization",
                ],
                "authority": "ALL code implementation decisions",
            },
            "qa": {
                **base_config,
                "description": "Quality assurance, testing, and validation",
                "tags": ["qa", "testing", "quality", "validation"],
                "tools": [
                    "Read",
                    "Write",
                    "Edit",
                    "Bash",
                    "Grep",
                    "Glob",
                    "LS",
                    "TodoWrite",
                ],
                "temperature": 0.1,
                "when_to_use": [
                    "Testing needed",
                    "Quality validation",
                    "Test coverage analysis",
                ],
                "specialized_knowledge": [
                    "Testing methodologies",
                    "Quality metrics",
                    "Test automation",
                ],
                "unique_capabilities": [
                    "Execute test suites",
                    "Identify edge cases",
                    "Validate quality",
                ],
                "primary_role": "Testing and quality assurance",
                "specializations": [
                    "testing",
                    "validation",
                    "quality-assurance",
                    "coverage",
                ],
                "authority": "ALL testing and quality decisions",
            },
            "documentation": {
                **base_config,
                "description": "Documentation creation, maintenance, and changelog generation",
                "tags": ["documentation", "writing", "changelog", "docs"],
                "tools": [
                    "Read",
                    "Write",
                    "Edit",
                    "MultiEdit",
                    "Grep",
                    "Glob",
                    "LS",
                    "WebSearch",
                    "TodoWrite",
                ],
                "temperature": 0.3,
                "when_to_use": [
                    "Documentation updates needed",
                    "Changelog generation",
                    "README updates",
                ],
                "specialized_knowledge": [
                    "Technical writing",
                    "Documentation standards",
                    "Semantic versioning",
                ],
                "unique_capabilities": [
                    "Create clear documentation",
                    "Generate changelogs",
                    "Maintain docs",
                ],
                "primary_role": "Documentation and technical writing",
                "specializations": [
                    "technical-writing",
                    "changelog",
                    "api-docs",
                    "guides",
                ],
                "authority": "ALL documentation decisions",
            },
            "research": {
                **base_config,
                "description": "Technical research, analysis, and investigation",
                "tags": ["research", "analysis", "investigation", "evaluation"],
                "tools": [
                    "Read",
                    "Grep",
                    "Glob",
                    "LS",
                    "WebSearch",
                    "WebFetch",
                    "TodoWrite",
                ],
                "temperature": 0.4,
                "when_to_use": [
                    "Technical research needed",
                    "Solution evaluation",
                    "Best practices investigation",
                ],
                "specialized_knowledge": [
                    "Research methodologies",
                    "Technical analysis",
                    "Evaluation frameworks",
                ],
                "unique_capabilities": [
                    "Deep investigation",
                    "Comparative analysis",
                    "Evidence-based recommendations",
                ],
                "primary_role": "Research and technical analysis",
                "specializations": [
                    "investigation",
                    "analysis",
                    "evaluation",
                    "recommendations",
                ],
                "authority": "ALL research decisions",
            },
            "security": {
                **base_config,
                "description": "Security analysis, vulnerability assessment, and protection",
                "tags": ["security", "vulnerability", "protection", "audit"],
                "tools": [
                    "Read",
                    "Grep",
                    "Glob",
                    "LS",
                    "Bash",
                    "WebSearch",
                    "TodoWrite",
                ],
                "temperature": 0.1,
                "when_to_use": [
                    "Security review needed",
                    "Vulnerability assessment",
                    "Security audit",
                ],
                "specialized_knowledge": [
                    "Security best practices",
                    "OWASP guidelines",
                    "Vulnerability patterns",
                ],
                "unique_capabilities": [
                    "Identify vulnerabilities",
                    "Security auditing",
                    "Threat modeling",
                ],
                "primary_role": "Security analysis and protection",
                "specializations": [
                    "vulnerability-assessment",
                    "security-audit",
                    "threat-modeling",
                    "protection",
                ],
                "authority": "ALL security decisions",
            },
            "ops": {
                **base_config,
                "description": "Deployment, operations, and infrastructure management",
                "tags": ["ops", "deployment", "infrastructure", "devops"],
                "tools": [
                    "Read",
                    "Write",
                    "Edit",
                    "Bash",
                    "Grep",
                    "Glob",
                    "LS",
                    "TodoWrite",
                ],
                "temperature": 0.2,
                "when_to_use": [
                    "Deployment configuration",
                    "Infrastructure setup",
                    "CI/CD pipeline work",
                ],
                "specialized_knowledge": [
                    "Deployment best practices",
                    "Infrastructure as code",
                    "CI/CD",
                ],
                "unique_capabilities": [
                    "Configure deployments",
                    "Manage infrastructure",
                    "Automate operations",
                ],
                "primary_role": "Operations and deployment management",
                "specializations": [
                    "deployment",
                    "infrastructure",
                    "automation",
                    "monitoring",
                ],
                "authority": "ALL operations decisions",
            },
            "data_engineer": {
                **base_config,
                "description": "Data pipeline management and AI API integrations",
                "tags": ["data", "pipeline", "etl", "ai-integration"],
                "tools": [
                    "Read",
                    "Write",
                    "Edit",
                    "Bash",
                    "Grep",
                    "Glob",
                    "LS",
                    "WebSearch",
                    "TodoWrite",
                ],
                "temperature": 0.2,
                "when_to_use": [
                    "Data pipeline setup",
                    "Database design",
                    "AI API integration",
                ],
                "specialized_knowledge": [
                    "Data architectures",
                    "ETL processes",
                    "AI/ML APIs",
                ],
                "unique_capabilities": [
                    "Design data schemas",
                    "Build pipelines",
                    "Integrate AI services",
                ],
                "primary_role": "Data engineering and AI integration",
                "specializations": [
                    "data-pipelines",
                    "etl",
                    "database",
                    "ai-integration",
                ],
                "authority": "ALL data engineering decisions",
            },
            "version_control": {
                **base_config,
                "description": "Git operations, version management, and release coordination",
                "tags": ["git", "version-control", "release", "branching"],
                "tools": ["Read", "Bash", "Grep", "Glob", "LS", "TodoWrite"],
                "temperature": 0.1,
                "network_access": False,  # Git operations are local
                "when_to_use": [
                    "Git operations needed",
                    "Version bumping",
                    "Release management",
                ],
                "specialized_knowledge": [
                    "Git workflows",
                    "Semantic versioning",
                    "Release processes",
                ],
                "unique_capabilities": [
                    "Complex git operations",
                    "Version management",
                    "Release coordination",
                ],
                "primary_role": "Version control and release management",
                "specializations": ["git", "versioning", "branching", "releases"],
                "authority": "ALL version control decisions",
            },
        }

    @staticmethod
    def _get_default_config(
        agent_name: str, base_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get default configuration for unknown agent types."""
        return {
            **base_config,
            "description": f"{agent_name.title()} agent for specialized tasks",
            "tags": [agent_name, "specialized", "mpm"],
            "tools": ["Read", "Write", "Edit", "Grep", "Glob", "LS", "TodoWrite"],
            "temperature": 0.3,
            "when_to_use": [f"When {agent_name} expertise is needed"],
            "specialized_knowledge": [f"{agent_name.title()} domain knowledge"],
            "unique_capabilities": [f"{agent_name.title()} specialized operations"],
            "primary_role": f"{agent_name.title()} operations",
            "specializations": [agent_name],
            "authority": f"ALL {agent_name} decisions",
        }
