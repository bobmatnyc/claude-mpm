from pathlib import Path

"""
Branch Strategy Manager - Branch strategy implementations for Version Control Agent.

This module provides comprehensive branch strategy management including:
1. Issue-driven development workflow
2. GitFlow implementation
3. GitHub Flow implementation
4. Custom branch strategies
5. Branch lifecycle management
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.unified_paths import get_path_manager


class BranchStrategyType(Enum):
    """Types of branch strategies."""

    ISSUE_DRIVEN = "issue_driven"
    GITFLOW = "gitflow"
    GITHUB_FLOW = "github_flow"
    CUSTOM = "custom"


class BranchType(Enum):
    """Types of branches in different strategies."""

    MAIN = "main"
    DEVELOP = "develop"
    FEATURE = "feature"
    ISSUE = "issue"
    ENHANCEMENT = "enhancement"
    HOTFIX = "hotfix"
    RELEASE = "release"
    EPIC = "epic"


@dataclass
class BranchNamingRule:
    """Rules for branch naming."""

    branch_type: BranchType
    prefix: str
    pattern: str
    required_fields: List[str] = field(default_factory=list)
    max_length: Optional[int] = None
    description: str = ""


@dataclass
class BranchLifecycleRule:
    """Rules for branch lifecycle management."""

    branch_type: BranchType
    auto_create: bool = False
    auto_merge_target: Optional[str] = None
    auto_merge_strategy: str = "merge"
    auto_delete_after_merge: bool = False
    requires_qa_approval: bool = False
    requires_review: bool = False
    merge_message_template: Optional[str] = None


@dataclass
class BranchWorkflow:
    """Workflow definition for a branch strategy."""

    strategy_type: BranchStrategyType
    main_branch: str
    development_branch: Optional[str] = None
    naming_rules: List[BranchNamingRule] = field(default_factory=list)
    lifecycle_rules: List[BranchLifecycleRule] = field(default_factory=list)
    merge_targets: Dict[str, str] = field(default_factory=dict)
    quality_gates: List[str] = field(default_factory=list)


class BranchStrategyManager:
    """
    Manages branch strategies for the Version Control Agent.

    Provides implementation of different branching strategies including
    issue-driven development, GitFlow, and GitHub Flow.
    """

    def __init__(self, project_root: str, logger: logging.Logger):
        """
        Initialize Branch Strategy Manager.

        Args:
            project_root: Root directory of the project
            logger: Logger instance
        """
        self.project_root = Path(project_root)
        self.logger = logger

        # Initialize predefined strategies
        self.strategies = {
            BranchStrategyType.ISSUE_DRIVEN: self._create_issue_driven_strategy(),
            BranchStrategyType.GITFLOW: self._create_gitflow_strategy(),
            BranchStrategyType.GITHUB_FLOW: self._create_github_flow_strategy(),
        }

        # Current strategy
        self.current_strategy: Optional[BranchWorkflow] = None

        # Load strategy from configuration
        self._load_strategy_configuration()

    def _create_issue_driven_strategy(self) -> BranchWorkflow:
        """Create issue-driven development strategy."""
        naming_rules = [
            BranchNamingRule(
                branch_type=BranchType.ISSUE,
                prefix="issue/",
                pattern=r"^issue/[A-Z]+-\d+(-.*)?$",
                required_fields=["ticket_id"],
                description="Issue branches for bug fixes and standard issues",
            ),
            BranchNamingRule(
                branch_type=BranchType.FEATURE,
                prefix="feature/",
                pattern=r"^feature/[A-Z]+-\d+(-.*)?$",
                required_fields=["ticket_id"],
                description="Feature branches for new functionality",
            ),
            BranchNamingRule(
                branch_type=BranchType.ENHANCEMENT,
                prefix="enhancement/",
                pattern=r"^enhancement/[A-Z]+-\d+(-.*)?$",
                required_fields=["ticket_id"],
                description="Enhancement branches for improvements",
            ),
            BranchNamingRule(
                branch_type=BranchType.HOTFIX,
                prefix="hotfix/",
                pattern=r"^hotfix/[A-Z]+-\d+(-.*)?$",
                required_fields=["ticket_id"],
                description="Hotfix branches for critical fixes",
            ),
            BranchNamingRule(
                branch_type=BranchType.EPIC,
                prefix="epic/",
                pattern=r"^epic/[A-Z]+-\d+(-.*)?$",
                required_fields=["epic_id"],
                description="Epic branches for large features",
            ),
        ]

        lifecycle_rules = [
            BranchLifecycleRule(
                branch_type=BranchType.ISSUE,
                auto_merge_target="main",
                auto_merge_strategy="merge",
                auto_delete_after_merge=True,
                requires_qa_approval=True,
                merge_message_template="Merge {branch_name}: {ticket_title}",
            ),
            BranchLifecycleRule(
                branch_type=BranchType.FEATURE,
                auto_merge_target="main",
                auto_merge_strategy="merge",
                auto_delete_after_merge=True,
                requires_qa_approval=True,
                requires_review=True,
                merge_message_template="Merge {branch_name}: {ticket_title}",
            ),
            BranchLifecycleRule(
                branch_type=BranchType.ENHANCEMENT,
                auto_merge_target="main",
                auto_merge_strategy="merge",
                auto_delete_after_merge=True,
                requires_qa_approval=True,
                merge_message_template="Merge {branch_name}: {ticket_title}",
            ),
            BranchLifecycleRule(
                branch_type=BranchType.HOTFIX,
                auto_merge_target="main",
                auto_merge_strategy="merge",
                auto_delete_after_merge=True,
                requires_qa_approval=False,  # Hotfixes can be fast-tracked
                merge_message_template="Hotfix {branch_name}: {ticket_title}",
            ),
            BranchLifecycleRule(
                branch_type=BranchType.EPIC,
                auto_merge_target="main",
                auto_merge_strategy="squash",
                auto_delete_after_merge=True,
                requires_qa_approval=True,
                requires_review=True,
                merge_message_template="Complete epic {branch_name}: {epic_title}",
            ),
        ]

        return BranchWorkflow(
            strategy_type=BranchStrategyType.ISSUE_DRIVEN,
            main_branch="main",
            naming_rules=naming_rules,
            lifecycle_rules=lifecycle_rules,
            merge_targets={
                "issue/*": "main",
                "feature/*": "main",
                "enhancement/*": "main",
                "hotfix/*": "main",
                "epic/*": "main",
            },
            quality_gates=["documentation_validation", "qa_testing", "code_quality"],
        )

    def _create_gitflow_strategy(self) -> BranchWorkflow:
        """Create GitFlow strategy."""
        naming_rules = [
            BranchNamingRule(
                branch_type=BranchType.FEATURE,
                prefix="feature/",
                pattern=r"^feature/.*$",
                description="Feature branches for new functionality",
            ),
            BranchNamingRule(
                branch_type=BranchType.RELEASE,
                prefix="release/",
                pattern=r"^release/\d+\.\d+(\.\d+)?$",
                required_fields=["version"],
                description="Release branches for version preparation",
            ),
            BranchNamingRule(
                branch_type=BranchType.HOTFIX,
                prefix="hotfix/",
                pattern=r"^hotfix/.*$",
                description="Hotfix branches for critical fixes",
            ),
        ]

        lifecycle_rules = [
            BranchLifecycleRule(
                branch_type=BranchType.FEATURE,
                auto_merge_target="develop",
                auto_merge_strategy="merge",
                auto_delete_after_merge=True,
                requires_review=True,
            ),
            BranchLifecycleRule(
                branch_type=BranchType.RELEASE,
                auto_merge_target="main",
                auto_merge_strategy="merge",
                auto_delete_after_merge=True,
                requires_qa_approval=True,
            ),
            BranchLifecycleRule(
                branch_type=BranchType.HOTFIX,
                auto_merge_target="main",
                auto_merge_strategy="merge",
                auto_delete_after_merge=True,
            ),
        ]

        return BranchWorkflow(
            strategy_type=BranchStrategyType.GITFLOW,
            main_branch="main",
            development_branch="develop",
            naming_rules=naming_rules,
            lifecycle_rules=lifecycle_rules,
            merge_targets={
                "feature/*": "develop",
                "release/*": "main",
                "hotfix/*": "main",
            },
            quality_gates=["testing", "code_review"],
        )

    def _create_github_flow_strategy(self) -> BranchWorkflow:
        """Create GitHub Flow strategy."""
        naming_rules = [
            BranchNamingRule(
                branch_type=BranchType.FEATURE,
                prefix="",
                pattern=r"^[a-z0-9\-/]+$",
                description="Feature branches with descriptive names",
            )
        ]

        lifecycle_rules = [
            BranchLifecycleRule(
                branch_type=BranchType.FEATURE,
                auto_merge_target="main",
                auto_merge_strategy="squash",
                auto_delete_after_merge=True,
                requires_review=True,
                requires_qa_approval=True,
            )
        ]

        return BranchWorkflow(
            strategy_type=BranchStrategyType.GITHUB_FLOW,
            main_branch="main",
            naming_rules=naming_rules,
            lifecycle_rules=lifecycle_rules,
            merge_targets={"*": "main"},
            quality_gates=["ci_tests", "code_review", "deployment_test"],
        )

    def _load_strategy_configuration(self) -> None:
        """Load strategy configuration from project files."""
        # Try to load from configuration files
        config_files = [
            f"{get_path_manager().CONFIG_DIR}/config.json",
            "workflow.md",
            ".github/workflows/branch-strategy.yml",
            "branch-strategy.json",
        ]

        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                try:
                    strategy = self._parse_strategy_config(config_path)
                    if strategy:
                        self.current_strategy = strategy
                        self.logger.info(f"Loaded branch strategy from {config_file}")
                        return
                except Exception as e:
                    self.logger.error(f"Error loading strategy from {config_file}: {e}")

        # Default to issue-driven strategy
        self.current_strategy = self.strategies[BranchStrategyType.ISSUE_DRIVEN]
        self.logger.info("Using default issue-driven branch strategy")

    def _parse_strategy_config(self, config_path: Path) -> Optional[BranchWorkflow]:
        """Parse strategy configuration from file."""
        # This would implement parsing logic for different config file formats
        # For now, return None to use defaults
        return None

    def get_current_strategy(self) -> BranchWorkflow:
        """Get the current branch strategy."""
        if not self.current_strategy:
            self.current_strategy = self.strategies[BranchStrategyType.ISSUE_DRIVEN]
        return self.current_strategy

    def set_strategy(self, strategy_type: BranchStrategyType) -> bool:
        """
        Set the current branch strategy.

        Args:
            strategy_type: Type of strategy to use

        Returns:
            True if strategy was set successfully
        """
        if strategy_type in self.strategies:
            self.current_strategy = self.strategies[strategy_type]
            self.logger.info(f"Set branch strategy to {strategy_type.value}")
            return True
        self.logger.error(f"Unknown strategy type: {strategy_type}")
        return False

    def generate_branch_name(
        self,
        branch_type: BranchType,
        ticket_id: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        Generate a branch name following the current strategy.

        Args:
            branch_type: Type of branch to create
            ticket_id: Ticket/issue ID
            description: Optional description
            **kwargs: Additional parameters

        Returns:
            Generated branch name
        """
        strategy = self.get_current_strategy()

        # Find naming rule for this branch type
        naming_rule = None
        for rule in strategy.naming_rules:
            if rule.branch_type == branch_type:
                naming_rule = rule
                break

        if not naming_rule:
            # Fallback to simple naming
            prefix = branch_type.value + "/"
            if ticket_id:
                return f"{prefix}{ticket_id}"
            if description:
                return f"{prefix}{self._sanitize_branch_name(description)}"
            return f"{prefix}{datetime.now(timezone.utc).strftime('%Y%m%d')}"

        # Generate name based on rule
        if strategy.strategy_type == BranchStrategyType.ISSUE_DRIVEN:
            if ticket_id:
                branch_name = f"{naming_rule.prefix}{ticket_id}"
                if description:
                    sanitized_desc = self._sanitize_branch_name(description)
                    branch_name += f"-{sanitized_desc}"
                return branch_name

        # Default generation
        return f"{naming_rule.prefix}{ticket_id or 'branch'}"

    def _sanitize_branch_name(self, name: str) -> str:
        """Sanitize a string for use in branch names."""
        # Convert to lowercase and replace spaces/special chars with hyphens
        sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "-", name.lower())
        # Remove multiple consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip("-")
        # Limit length
        return sanitized[:50]

    def validate_branch_name(self, branch_name: str) -> Tuple[bool, str]:
        """
        Validate a branch name against current strategy rules.

        Args:
            branch_name: Branch name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        strategy = self.get_current_strategy()

        # Check against naming rules
        for rule in strategy.naming_rules:
            if branch_name.startswith(rule.prefix):
                # Check pattern
                if not re.match(rule.pattern, branch_name):
                    return False, f"Branch name doesn't match pattern: {rule.pattern}"

                # Check length
                if rule.max_length and len(branch_name) > rule.max_length:
                    return (
                        False,
                        f"Branch name exceeds maximum length: {rule.max_length}",
                    )

                return True, "Valid branch name"

        # Check if it's a protected branch
        protected_branches = [strategy.main_branch]
        if strategy.development_branch:
            protected_branches.append(strategy.development_branch)

        if branch_name in protected_branches:
            return False, f"Cannot use protected branch name: {branch_name}"

        return True, "Valid branch name"

    def get_merge_target(self, branch_name: str) -> Optional[str]:
        """
        Get the merge target for a branch based on current strategy.

        Args:
            branch_name: Source branch name

        Returns:
            Target branch name or None
        """
        strategy = self.get_current_strategy()

        # Check specific merge targets
        for pattern, target in strategy.merge_targets.items():
            if pattern == "*" or branch_name.startswith(pattern.rstrip("*")):
                return target

        # Default to main branch
        return strategy.main_branch

    def get_lifecycle_rule(self, branch_name: str) -> Optional[BranchLifecycleRule]:
        """
        Get the lifecycle rule for a branch.

        Args:
            branch_name: Branch name

        Returns:
            BranchLifecycleRule or None
        """
        strategy = self.get_current_strategy()

        # Determine branch type from name
        branch_type = self._get_branch_type(branch_name)

        # Find matching lifecycle rule
        for rule in strategy.lifecycle_rules:
            if rule.branch_type == branch_type:
                return rule

        return None

    def _get_branch_type(self, branch_name: str) -> BranchType:
        """Determine branch type from branch name."""
        strategy = self.get_current_strategy()

        # Check against naming rules
        for rule in strategy.naming_rules:
            if branch_name.startswith(rule.prefix):
                return rule.branch_type

        # Default to feature
        return BranchType.FEATURE

    def should_auto_merge(self, branch_name: str) -> bool:
        """
        Check if a branch should be automatically merged.

        Args:
            branch_name: Branch name

        Returns:
            True if branch should be auto-merged
        """
        rule = self.get_lifecycle_rule(branch_name)
        return rule and rule.auto_merge_target is not None

    def should_delete_after_merge(self, branch_name: str) -> bool:
        """
        Check if a branch should be deleted after merge.

        Args:
            branch_name: Branch name

        Returns:
            True if branch should be deleted after merge
        """
        rule = self.get_lifecycle_rule(branch_name)
        return rule and rule.auto_delete_after_merge

    def requires_qa_approval(self, branch_name: str) -> bool:
        """
        Check if a branch requires QA approval before merge.

        Args:
            branch_name: Branch name

        Returns:
            True if QA approval is required
        """
        rule = self.get_lifecycle_rule(branch_name)
        return rule and rule.requires_qa_approval

    def requires_code_review(self, branch_name: str) -> bool:
        """
        Check if a branch requires code review before merge.

        Args:
            branch_name: Branch name

        Returns:
            True if code review is required
        """
        rule = self.get_lifecycle_rule(branch_name)
        return rule and rule.requires_review

    def get_merge_strategy(self, branch_name: str) -> str:
        """
        Get the merge strategy for a branch.

        Args:
            branch_name: Branch name

        Returns:
            Merge strategy (merge, squash, rebase)
        """
        rule = self.get_lifecycle_rule(branch_name)
        return rule.auto_merge_strategy if rule else "merge"

    def generate_merge_message(
        self, branch_name: str, ticket_title: Optional[str] = None, **kwargs
    ) -> str:
        """
        Generate merge commit message based on strategy.

        Args:
            branch_name: Source branch name
            ticket_title: Optional ticket title
            **kwargs: Additional template variables

        Returns:
            Generated merge message
        """
        rule = self.get_lifecycle_rule(branch_name)

        if rule and rule.merge_message_template:
            template = rule.merge_message_template

            # Replace template variables
            variables = {
                "branch_name": branch_name,
                "ticket_title": ticket_title or "Updates",
                **kwargs,
            }

            for key, value in variables.items():
                template = template.replace(f"{{{key}}}", str(value))

            return template

        # Default merge message
        if ticket_title:
            return f"Merge {branch_name}: {ticket_title}"
        return f"Merge {branch_name}"

    def get_quality_gates(self) -> List[str]:
        """Get quality gates for the current strategy."""
        strategy = self.get_current_strategy()
        return strategy.quality_gates

    def create_custom_strategy(
        self, name: str, config: Dict[str, Any]
    ) -> BranchWorkflow:
        """
        Create a custom branch strategy.

        Args:
            name: Strategy name
            config: Strategy configuration

        Returns:
            Custom BranchWorkflow
        """
        # This would implement custom strategy creation
        # For now, return a basic custom strategy
        return BranchWorkflow(
            strategy_type=BranchStrategyType.CUSTOM,
            main_branch=config.get("main_branch", "main"),
            naming_rules=[],
            lifecycle_rules=[],
            merge_targets={},
            quality_gates=[],
        )

    def export_strategy_config(self) -> Dict[str, Any]:
        """Export current strategy as configuration."""
        strategy = self.get_current_strategy()

        return {
            "strategy_type": strategy.strategy_type.value,
            "main_branch": strategy.main_branch,
            "development_branch": strategy.development_branch,
            "naming_rules": [
                {
                    "branch_type": rule.branch_type.value,
                    "prefix": rule.prefix,
                    "pattern": rule.pattern,
                    "required_fields": rule.required_fields,
                    "max_length": rule.max_length,
                    "description": rule.description,
                }
                for rule in strategy.naming_rules
            ],
            "lifecycle_rules": [
                {
                    "branch_type": rule.branch_type.value,
                    "auto_merge_target": rule.auto_merge_target,
                    "auto_merge_strategy": rule.auto_merge_strategy,
                    "auto_delete_after_merge": rule.auto_delete_after_merge,
                    "requires_qa_approval": rule.requires_qa_approval,
                    "requires_review": rule.requires_review,
                    "merge_message_template": rule.merge_message_template,
                }
                for rule in strategy.lifecycle_rules
            ],
            "merge_targets": strategy.merge_targets,
            "quality_gates": strategy.quality_gates,
        }
