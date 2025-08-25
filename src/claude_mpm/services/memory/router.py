#!/usr/bin/env python3
"""
Memory Router Service
====================

Routes memory commands to appropriate agents based on content analysis.

This service provides:
- Content analysis to determine target agent
- Support for "remember", "memorize", "add to memory" commands
- Routing decision with reasoning
- Context-aware agent selection

WHY: When users say "remember this for next time", the system needs to determine
which agent should store the information. This service analyzes content to make
intelligent routing decisions for PM delegation.

DESIGN DECISION: Uses keyword matching and context analysis rather than ML models
for simplicity and transparency. Routing decisions include reasoning to help
users understand why content was assigned to specific agents.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.config import Config
from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.core.mixins import LoggerMixin


class MemoryRouter(LoggerMixin):
    """Routes memory commands to appropriate agents based on content analysis.

    WHY: Different types of learnings belong to different agents. Engineering
    insights should go to the engineer agent, while research findings should
    go to the research agent. This service provides intelligent routing.

    DESIGN DECISION: Uses explicit keyword patterns and rules rather than ML
    to ensure predictable, transparent routing decisions that users can understand.
    """

    # Agent routing patterns - keywords that indicate agent specialization
    AGENT_PATTERNS = {
        "engineer": {
            "keywords": [
                "implementation",
                "code",
                "coding",
                "programming",
                "function",
                "method",
                "class",
                "module",
                "import",
                "dependency",
                "build",
                "compile",
                "deploy",
                "refactor",
                "optimize",
                "performance",
                "algorithm",
                "data structure",
                "design pattern",
                "architecture",
                "api",
                "interface",
                "library",
                "framework",
                "testing",
                "unit test",
                "integration test",
                "debug",
                "error handling",
                "exception",
            ],
            "sections": [
                "Coding Patterns Learned",
                "Implementation Guidelines",
                "Performance Considerations",
                "Integration Points",
            ],
        },
        "research": {
            "keywords": [
                "research",
                "analysis",
                "investigate",
                "explore",
                "study",
                "examine",
                "findings",
                "discovery",
                "insights",
                "documentation",
                "specification",
                "requirements",
                "use case",
                "user story",
                "business logic",
                "domain knowledge",
                "best practices",
                "standards",
                "compliance",
                "security",
                "vulnerability",
                "threat",
                "risk",
            ],
            "sections": [
                "Domain-Specific Knowledge",
                "Research Findings",
                "Security Considerations",
                "Compliance Requirements",
            ],
        },
        "qa": {
            "keywords": [
                "test",
                "testing",
                "quality",
                "bug",
                "defect",
                "issue",
                "validation",
                "verification",
                "quality assurance",
                "test case",
                "test plan",
                "coverage",
                "automation",
                "regression",
                "smoke test",
                "acceptance",
                "criteria",
                "checklist",
                "review",
                "audit",
                "compliance",
                "standards",
                "metrics",
                "measurement",
            ],
            "sections": [
                "Quality Standards",
                "Testing Strategies",
                "Common Issues Found",
                "Verification Patterns",
            ],
        },
        "documentation": {
            "keywords": [
                "document",
                "documentation",
                "readme",
                "guide",
                "manual",
                "help",
                "instructions",
                "tutorial",
                "explanation",
                "description",
                "overview",
                "summary",
                "specification",
                "reference",
                "glossary",
                "faq",
                "examples",
                "usage",
                "howto",
                "walkthrough",
            ],
            "sections": [
                "Documentation Patterns",
                "User Guide Standards",
                "Content Organization",
                "Writing Guidelines",
            ],
        },
        "security": {
            "keywords": [
                "security",
                "authentication",
                "authorization",
                "encryption",
                "decrypt",
                "password",
                "token",
                "certificate",
                "ssl",
                "tls",
                "vulnerability",
                "exploit",
                "attack",
                "malware",
                "virus",
                "firewall",
                "access control",
                "permissions",
                "privilege",
                "audit",
                "compliance",
                "privacy",
                "data protection",
                "gdpr",
                "sensitive data",
            ],
            "sections": [
                "Security Patterns",
                "Threat Analysis",
                "Compliance Requirements",
                "Access Control Patterns",
            ],
        },
        "pm": {
            "keywords": [
                "project",
                "management",
                "coordination",
                "planning",
                "schedule",
                "timeline",
                "milestone",
                "deliverable",
                "stakeholder",
                "requirement",
                "priority",
                "resource",
                "allocation",
                "budget",
                "scope",
                "risk",
                "communication",
                "meeting",
                "status",
                "progress",
                "workflow",
                "process",
                "methodology",
                "agile",
                "scrum",
                "kanban",
            ],
            "sections": [
                "Project Coordination",
                "Team Communication",
                "Process Improvements",
                "Risk Management",
            ],
        },
        "data_engineer": {
            "keywords": [
                "data",
                "database",
                "sql",
                "pipeline",
                "etl",
                "elt",
                "extract",
                "transform",
                "load",
                "analytics",
                "warehouse",
                "lake",
                "schema",
                "migration",
                "replication",
                "streaming",
                "batch",
                "kafka",
                "spark",
                "hadoop",
                "mongodb",
                "postgres",
                "mysql",
                "redis",
                "elasticsearch",
                "index",
                "query",
                "optimization",
                "performance",
                "partitioning",
                "sharding",
                "normalization",
                "denormalization",
                "aggregation",
                "cleansing",
                "validation",
                "quality",
                "lineage",
                "governance",
                "backup",
                "restore",
                "ai api",
                "openai",
                "claude",
                "llm",
                "embedding",
                "vector database",
            ],
            "sections": [
                "Database Architecture Patterns",
                "Pipeline Design Strategies",
                "Data Quality Standards",
                "Performance Optimization Techniques",
            ],
        },
        "test_integration": {
            "keywords": [
                "integration",
                "e2e",
                "end-to-end",
                "system test",
                "workflow test",
                "cross-system",
                "api test",
                "contract test",
                "service test",
                "boundary test",
                "interface test",
                "component test",
                "smoke test",
                "acceptance test",
                "scenario test",
                "user journey",
                "flow test",
                "regression",
                "compatibility",
                "interoperability",
                "validation",
                "verification",
                "mock",
                "stub",
                "test data",
                "test environment",
                "test setup",
                "teardown",
                "isolation",
                "coordination",
                "synchronization",
                "selenium",
                "cypress",
                "playwright",
                "postman",
                "newman",
            ],
            "sections": [
                "Integration Test Patterns",
                "Cross-System Validation",
                "Test Environment Management",
                "End-to-End Workflow Testing",
            ],
        },
        "ops": {
            "keywords": [
                "deployment",
                "infrastructure",
                "devops",
                "cicd",
                "ci/cd",
                "docker",
                "container",
                "kubernetes",
                "helm",
                "terraform",
                "ansible",
                "jenkins",
                "pipeline",
                "build",
                "release",
                "staging",
                "production",
                "environment",
                "monitoring",
                "logging",
                "metrics",
                "alerts",
                "observability",
                "scaling",
                "load balancer",
                "proxy",
                "nginx",
                "apache",
                "server",
                "network",
                "firewall",
                "vpc",
                "aws",
                "azure",
                "gcp",
                "cloud",
                "backup",
                "disaster recovery",
                "failover",
                "redundancy",
                "uptime",
                "prometheus",
                "grafana",
                "splunk",
                "datadog",
                "newrelic",
            ],
            "sections": [
                "Deployment Strategies",
                "Infrastructure Patterns",
                "Monitoring and Observability",
                "Scaling and Performance",
            ],
        },
        "version_control": {
            "keywords": [
                "git",
                "github",
                "gitlab",
                "bitbucket",
                "branch",
                "merge",
                "commit",
                "pull request",
                "merge request",
                "tag",
                "release",
                "version",
                "changelog",
                "semantic versioning",
                "semver",
                "workflow",
                "gitflow",
                "conflict",
                "resolution",
                "rebase",
                "cherry-pick",
                "stash",
                "bisect",
                "blame",
                "diff",
                "patch",
                "submodule",
                "hook",
                "pre-commit",
                "post-commit",
                "repository",
                "remote",
                "origin",
                "upstream",
                "fork",
                "clone",
            ],
            "sections": [
                "Branching Strategies",
                "Release Management",
                "Version Control Workflows",
                "Collaboration Patterns",
            ],
        },
    }

    # Default agent for unmatched content
    DEFAULT_AGENT = "pm"

    def __init__(self, config: Optional[Config] = None):
        """Initialize the memory router.

        Args:
            config: Optional Config object
        """
        super().__init__()
        self.config = config or Config()
        self._dynamic_patterns_loaded = False
        self._dynamic_patterns = {}

    def _load_dynamic_patterns(self) -> None:
        """Load memory routing patterns dynamically from agent templates.

        WHY: Allows agents to define their own memory routing patterns
        in their template files, making the system more flexible and
        maintainable.
        """
        if self._dynamic_patterns_loaded:
            return

        try:
            # Initialize framework loader to access agent templates
            framework_loader = FrameworkLoader()

            # Try to load patterns from deployed agents
            from pathlib import Path

            # Check both project and user agent directories
            agent_dirs = [
                Path(".claude/agents"),  # Project agents
                Path.home() / ".claude-mpm/agents",  # User agents
            ]

            for agent_dir in agent_dirs:
                if not agent_dir.exists():
                    continue

                # Look for deployed agent files
                for agent_file in agent_dir.glob("*.md"):
                    agent_name = agent_file.stem

                    # Try to load memory routing from template
                    memory_routing = (
                        framework_loader._load_memory_routing_from_template(agent_name)
                    )

                    if memory_routing:
                        # Convert agent name to pattern key format
                        # e.g., "research-agent" -> "research"
                        pattern_key = (
                            agent_name.replace("-agent", "")
                            .replace("_agent", "")
                            .replace("-", "_")
                        )

                        # Build pattern structure from memory routing
                        pattern_data = {
                            "keywords": memory_routing.get("keywords", []),
                            "sections": memory_routing.get("categories", []),
                        }

                        # Merge with existing patterns or add new
                        if pattern_key in self.AGENT_PATTERNS:
                            # Merge keywords, keeping unique values
                            existing_keywords = set(
                                self.AGENT_PATTERNS[pattern_key]["keywords"]
                            )
                            new_keywords = set(memory_routing.get("keywords", []))
                            pattern_data["keywords"] = list(
                                existing_keywords | new_keywords
                            )

                        self._dynamic_patterns[pattern_key] = pattern_data
                        self.logger.debug(
                            f"Loaded dynamic memory routing for {pattern_key}"
                        )

            self._dynamic_patterns_loaded = True
            self.logger.info(
                f"Loaded memory routing patterns for {len(self._dynamic_patterns)} agents"
            )

        except Exception as e:
            self.logger.warning(f"Could not load dynamic memory routing patterns: {e}")
            self._dynamic_patterns_loaded = True  # Don't retry

    def get_supported_agents(self) -> List[str]:
        """Get list of supported agent types.

        WHY: Other components need to know which agent types are supported
        for validation and UI display purposes.

        Returns:
            List of supported agent type names
        """
        self._load_dynamic_patterns()

        # Combine static and dynamic patterns
        all_agents = set(self.AGENT_PATTERNS.keys())
        all_agents.update(self._dynamic_patterns.keys())
        return list(all_agents)

    def is_agent_supported(self, agent_type: str) -> bool:
        """Check if an agent type is supported by the memory router.

        WHY: Provides validation for agent types before attempting routing.
        This prevents errors and provides clear feedback about unsupported types.

        Args:
            agent_type: Agent type to check

        Returns:
            True if agent type is supported, False otherwise
        """
        self._load_dynamic_patterns()
        return agent_type in self.AGENT_PATTERNS or agent_type in self._dynamic_patterns

    def analyze_and_route(
        self, content: str, context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Analyze content and determine target agent for memory storage.

        WHY: Different types of information belong to different agents. This method
        analyzes content using keyword patterns and context to make intelligent
        routing decisions.

        Args:
            content: The content to be remembered
            context: Optional context for routing decisions

        Returns:
            Dict containing routing decision and reasoning
        """
        try:
            # Clean and normalize content for analysis
            normalized_content = self._normalize_content(content)

            # Analyze content for agent patterns
            agent_scores = self._calculate_agent_scores(normalized_content)

            # Apply context-based adjustments
            if context:
                agent_scores = self._apply_context_adjustments(agent_scores, context)

            # Select target agent
            target_agent, confidence = self._select_target_agent(agent_scores)

            # Determine appropriate section
            section = self._determine_section(target_agent, normalized_content)

            # Build reasoning
            reasoning = self._build_reasoning(
                target_agent, agent_scores, section, context
            )

            result = {
                "target_agent": target_agent,
                "section": section,
                "confidence": confidence,
                "reasoning": reasoning,
                "agent_scores": agent_scores,
                "timestamp": datetime.now().isoformat(),
                "content_length": len(content),
            }

            self.logger.debug(
                f"Routed content to {target_agent} with confidence {confidence}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Error analyzing content for routing: {e}")
            return {
                "target_agent": self.DEFAULT_AGENT,
                "section": "Recent Learnings",
                "confidence": 0.1,
                "reasoning": f"Error during analysis, defaulting to {self.DEFAULT_AGENT}",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "content_length": len(content) if content else 0,
            }

    def test_routing_patterns(
        self, test_cases: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Test routing logic with provided test cases.

        WHY: Routing patterns need validation to ensure they work correctly.
        This method allows testing of routing logic with known inputs.

        Args:
            test_cases: List of test cases with 'content' and optional 'expected_agent'

        Returns:
            List of routing results for each test case
        """
        results = []

        for i, test_case in enumerate(test_cases):
            content = test_case.get("content", "")
            expected = test_case.get("expected_agent")

            routing_result = self.analyze_and_route(content)

            test_result = {
                "test_case": i + 1,
                "content": content[:100] + "..." if len(content) > 100 else content,
                "expected_agent": expected,
                "actual_agent": routing_result["target_agent"],
                "confidence": routing_result["confidence"],
                "correct": (
                    expected == routing_result["target_agent"] if expected else None
                ),
                "reasoning": routing_result["reasoning"],
            }

            results.append(test_result)

        return results

    def get_routing_patterns(self) -> Dict[str, Any]:
        """Get current routing patterns and statistics.

        WHY: Users and developers need to understand how routing works and
        potentially customize patterns for their specific use cases.

        Returns:
            Dict containing routing patterns and statistics
        """
        self._load_dynamic_patterns()

        # Combine static and dynamic patterns
        all_patterns = dict(self.AGENT_PATTERNS)
        all_patterns.update(self._dynamic_patterns)

        return {
            "agents": list(all_patterns.keys()),
            "default_agent": self.DEFAULT_AGENT,
            "static_agents": list(self.AGENT_PATTERNS.keys()),
            "dynamic_agents": list(self._dynamic_patterns.keys()),
            "patterns": {
                agent: {
                    "keyword_count": len(patterns["keywords"]),
                    "section_count": len(patterns["sections"]),
                    "keywords": patterns["keywords"][:10],  # Show first 10
                    "sections": patterns["sections"],
                    "source": (
                        "dynamic" if agent in self._dynamic_patterns else "static"
                    ),
                }
                for agent, patterns in all_patterns.items()
            },
            "total_keywords": sum(len(p["keywords"]) for p in all_patterns.values()),
        }

    def _normalize_content(self, content: str) -> str:
        """Normalize content for analysis.

        Args:
            content: Raw content

        Returns:
            Normalized content string
        """
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r"\s+", " ", content.lower().strip())

        # Remove common noise words that don't help with routing
        noise_words = [
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        ]
        words = normalized.split()
        filtered_words = [w for w in words if w not in noise_words and len(w) > 2]

        return " ".join(filtered_words)

    def _calculate_agent_scores(self, content: str) -> Dict[str, float]:
        """Calculate relevance scores for each agent.

        Args:
            content: Normalized content

        Returns:
            Dict mapping agent names to relevance scores
        """
        self._load_dynamic_patterns()
        scores = {}

        # Combine static and dynamic patterns
        all_patterns = dict(self.AGENT_PATTERNS)
        all_patterns.update(self._dynamic_patterns)

        for agent, patterns in all_patterns.items():
            score = 0.0
            matched_keywords = []

            for keyword in patterns["keywords"]:
                # Exact keyword match gets higher score
                if keyword in content:
                    # Multi-word keywords get bonus score
                    bonus = 1.5 if " " in keyword else 1.0
                    score += bonus
                    matched_keywords.append(keyword)
                # Partial match (word contains keyword)
                elif any(keyword in word for word in content.split()):
                    score += 0.5

            # Normalize score by square root to avoid penalizing agents with many keywords
            if patterns["keywords"]:
                import math

                score = score / math.sqrt(len(patterns["keywords"]))

            scores[agent] = {
                "score": score,
                "matched_keywords": matched_keywords[:5],  # Limit for readability
                "match_count": len(matched_keywords),
            }

        return scores

    def _apply_context_adjustments(
        self, agent_scores: Dict[str, Any], context: Dict
    ) -> Dict[str, Any]:
        """Apply context-based adjustments to agent scores.

        Args:
            agent_scores: Current agent scores
            context: Context information

        Returns:
            Adjusted agent scores
        """
        # Context hints for routing
        if "agent_hint" in context:
            hint = context["agent_hint"].lower()
            if hint in agent_scores:
                agent_scores[hint]["score"] += 0.3
                agent_scores[hint]["context_boost"] = True

        # Task type hints
        if "task_type" in context:
            task_type = context["task_type"].lower()
            task_mappings = {
                "implementation": "engineer",
                "coding": "engineer",
                "analysis": "research",
                "testing": "qa",
                "documentation": "documentation",
                "security": "security",
                "planning": "pm",
            }

            if task_type in task_mappings:
                target_agent = task_mappings[task_type]
                if target_agent in agent_scores:
                    agent_scores[target_agent]["score"] += 0.2
                    agent_scores[target_agent]["task_type_boost"] = True

        return agent_scores

    def _select_target_agent(self, agent_scores: Dict[str, Any]) -> Tuple[str, float]:
        """Select target agent based on scores.

        Args:
            agent_scores: Agent relevance scores

        Returns:
            Tuple of (target_agent, confidence)
        """
        # Find agent with highest score
        best_agent = self.DEFAULT_AGENT
        best_score = 0.0

        for agent, score_data in agent_scores.items():
            score = score_data["score"]
            if score > best_score:
                best_score = score
                best_agent = agent

        # If no clear winner, use default
        # Lowered threshold to handle diverse agent patterns better
        if best_score < 0.05:
            return self.DEFAULT_AGENT, 0.1

        # Convert score to confidence (0.0 to 1.0)
        confidence = min(1.0, best_score * 2)  # Scale up for better confidence values

        return best_agent, confidence

    def _determine_section(self, agent: str, content: str) -> str:
        """Determine appropriate section for the content.

        Args:
            agent: Target agent
            content: Normalized content

        Returns:
            Section name for memory storage
        """
        self._load_dynamic_patterns()

        # Check both static and dynamic patterns
        if agent in self.AGENT_PATTERNS:
            sections = self.AGENT_PATTERNS[agent]["sections"]
        elif agent in self._dynamic_patterns:
            sections = self._dynamic_patterns[agent]["sections"]
        else:
            return "Recent Learnings"

        sections = sections if sections else []

        # Simple heuristics for section selection
        if "mistake" in content or "error" in content or "avoid" in content:
            return "Common Mistakes to Avoid"
        if "pattern" in content or "architecture" in content:
            return (
                sections[0] if sections else "Recent Learnings"
            )  # First section is usually patterns
        if "guideline" in content or "standard" in content:
            return "Implementation Guidelines"
        if "context" in content or "current" in content:
            return "Current Technical Context"
        # Default to first available section or Recent Learnings
        return sections[0] if sections else "Recent Learnings"

    def _build_reasoning(
        self,
        target_agent: str,
        agent_scores: Dict[str, Any],
        section: str,
        context: Optional[Dict],
    ) -> str:
        """Build human-readable reasoning for routing decision.

        Args:
            target_agent: Selected target agent
            agent_scores: All agent scores
            section: Selected section
            context: Optional context

        Returns:
            Human-readable reasoning string
        """
        if target_agent not in agent_scores:
            return f"Defaulted to {target_agent} agent due to analysis error"

        score_data = agent_scores[target_agent]
        score = score_data["score"]
        matched_keywords = score_data.get("matched_keywords", [])

        reasoning_parts = []

        # Primary reasoning
        if score > 0.3:
            reasoning_parts.append(f"Strong match for {target_agent} agent")
        elif score > 0.1:
            reasoning_parts.append(f"Moderate match for {target_agent} agent")
        else:
            reasoning_parts.append(f"Weak match, defaulting to {target_agent} agent")

        # Keyword evidence
        if matched_keywords:
            keyword_str = ", ".join(matched_keywords)
            reasoning_parts.append(f"matched keywords: {keyword_str}")

        # Context boosts
        if score_data.get("context_boost"):
            reasoning_parts.append("boosted by context hint")
        if score_data.get("task_type_boost"):
            reasoning_parts.append("boosted by task type")

        # Section selection
        if section != "Recent Learnings":
            reasoning_parts.append(f"assigned to '{section}' section")

        return "; ".join(reasoning_parts).capitalize()
