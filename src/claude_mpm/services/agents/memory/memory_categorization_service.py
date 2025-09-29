#!/usr/bin/env python3
"""Memory Categorization Service - Categorizes learnings into appropriate sections."""

from typing import List

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class MemoryCategorizationService:
    """Service for categorizing memory learnings."""

    # Category keywords for automatic categorization
    CATEGORY_KEYWORDS = {
        "Project Architecture": [
            "architecture",
            "structure",
            "design",
            "pattern",
            "framework",
            "component",
            "module",
            "service",
            "interface",
            "api",
            "endpoint",
            "schema",
            "model",
            "database",
            "microservice",
        ],
        "Implementation Guidelines": [
            "implement",
            "code",
            "function",
            "method",
            "class",
            "algorithm",
            "logic",
            "process",
            "workflow",
            "feature",
            "requirement",
            "specification",
            "standard",
            "convention",
            "practice",
        ],
        "Common Mistakes to Avoid": [
            "mistake",
            "error",
            "bug",
            "issue",
            "problem",
            "avoid",
            "don't",
            "never",
            "warning",
            "caution",
            "gotcha",
            "pitfall",
            "trap",
            "wrong",
            "incorrect",
        ],
        "Current Technical Context": [
            "current",
            "status",
            "context",
            "environment",
            "configuration",
            "setup",
            "version",
            "dependency",
            "tool",
            "library",
            "package",
            "integration",
            "deployment",
            "infrastructure",
            "state",
        ],
    }

    def __init__(self):
        """Initialize the categorization service."""

    def categorize_learning(self, learning: str) -> str:
        """Categorize a learning item based on its content.

        WHY: Learnings are automatically organized into categories to make them
        easier to find and review. This uses keyword matching to determine the
        most appropriate category.

        Args:
            learning: The learning content to categorize

        Returns:
            Category name (defaults to "Current Technical Context")
        """
        if not learning:
            return "Current Technical Context"

        learning_lower = learning.lower()
        category_scores = {}

        # Score each category based on keyword matches
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in learning_lower)
            if score > 0:
                category_scores[category] = score

        # Return category with highest score, or default
        if category_scores:
            return max(category_scores, key=category_scores.get)

        return "Current Technical Context"

    def categorize_learnings_batch(self, learnings: List[str]) -> dict:
        """Categorize multiple learnings at once.

        Args:
            learnings: List of learning items to categorize

        Returns:
            Dictionary mapping categories to lists of learnings
        """
        categorized = {}

        for learning in learnings:
            category = self.categorize_learning(learning)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(learning)

        return categorized

    def merge_categorized_learnings(
        self, existing: dict, new: dict, max_per_category: int = 15
    ) -> dict:
        """Merge new categorized learnings with existing ones.

        Args:
            existing: Existing categorized learnings
            new: New categorized learnings to add
            max_per_category: Maximum items per category

        Returns:
            Merged categorized learnings with limits applied
        """
        merged = existing.copy()

        for category, items in new.items():
            if category not in merged:
                merged[category] = []

            # Add new items, avoiding duplicates
            for item in items:
                if item not in merged[category]:
                    merged[category].append(item)

            # Apply limit (keep most recent)
            if len(merged[category]) > max_per_category:
                merged[category] = merged[category][-max_per_category:]

        return merged
