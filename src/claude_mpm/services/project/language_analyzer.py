#!/usr/bin/env python3
"""
Language Analyzer Service
=========================

WHY: Separates language-specific analysis from the main analyzer to follow
single responsibility principle. Handles detection and analysis of programming
languages, frameworks, and language-specific patterns.

DECISION: Extract language detection into a focused service that can be
enhanced independently with better language-specific analysis.
"""

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional


class LanguageAnalyzerService:
    """Analyzes programming languages and frameworks in a project.

    WHY: Language detection and framework identification is a complex task
    that deserves its own focused service. This separation allows for better
    testing and future enhancements like syntax analysis.
    """

    # Language detection by file extension
    FILE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "react",
        ".tsx": "react",
        ".rs": "rust",
        ".java": "java",
        ".go": "go",
        ".php": "php",
        ".rb": "ruby",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".r": "r",
        ".m": "objective-c",
        ".lua": "lua",
        ".pl": "perl",
        ".sh": "bash",
        ".ps1": "powershell",
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        "flask": ["from flask", "Flask(", "app.route"],
        "django": ["from django", "DJANGO_SETTINGS", "django.contrib"],
        "fastapi": ["from fastapi", "FastAPI(", "@app."],
        "express": ["express()", "app.get(", "app.post("],
        "react": ["import React", "from 'react'", 'from "react"', "ReactDOM"],
        "vue": ["Vue.createApp", "new Vue(", "vue-"],
        "angular": ["@Component", "@Injectable", "Angular"],
        "spring": ["@SpringBootApplication", "@RestController", "Spring"],
        "rails": ["Rails.application", "ApplicationController"],
        "nextjs": ["next/router", "next/link", "getServerSideProps"],
        "nuxt": ["nuxt.config", "@nuxt/"],
        "svelte": ["import { writable }", "svelte"],
        "ember": ["ember-cli", "Ember.Application"],
        "backbone": ["Backbone.Model", "Backbone.View"],
        "laravel": ["Illuminate\\", "artisan"],
        "symfony": ["Symfony\\Component", "symfony/"],
        "dotnet": ["using System", "namespace", ".NET"],
    }

    def __init__(self, working_directory: Path):
        """Initialize the language analyzer service.

        Args:
            working_directory: Project root directory
        """
        self.working_directory = working_directory
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def detect_languages(self) -> List[str]:
        """Detect programming languages used in the project.

        WHY: Understanding which languages are used helps determine
        appropriate analysis strategies and tools.

        Returns:
            List of detected language names
        """
        languages = set()

        # Scan for source files
        for ext, lang in self.FILE_EXTENSIONS.items():
            files = list(self.working_directory.rglob(f"*{ext}"))
            # Filter out vendor/node_modules directories
            files = [
                f
                for f in files
                if not any(
                    part in [".git", "node_modules", "vendor", "__pycache__"]
                    for part in f.parts
                )
            ]
            if files:
                languages.add(lang)

        return sorted(languages)

    def detect_primary_language(
        self, file_counts: Optional[Dict[str, int]] = None
    ) -> Optional[str]:
        """Detect the primary programming language.

        WHY: The primary language determines main analysis strategies
        and helps prioritize which patterns to look for.

        Args:
            file_counts: Optional pre-computed file counts by extension

        Returns:
            Primary language name or None
        """
        if file_counts is None:
            file_counts = self._count_files_by_extension()

        if not file_counts:
            return None

        # Weight by file count and typical importance
        language_weights = Counter()

        for ext, count in file_counts.items():
            if ext in self.FILE_EXTENSIONS:
                lang = self.FILE_EXTENSIONS[ext]
                # Give extra weight to certain languages based on project patterns
                weight = count
                if ext in [".py", ".js", ".ts", ".java", ".go", ".rs"]:
                    weight *= 1.5  # Boost common application languages
                language_weights[lang] += weight

        if language_weights:
            return language_weights.most_common(1)[0][0]

        return None

    def detect_frameworks(self, sample_files: Optional[List[Path]] = None) -> List[str]:
        """Detect frameworks used in the project.

        WHY: Framework detection helps understand project architecture
        and development patterns that agents should follow.

        Args:
            sample_files: Optional list of files to analyze

        Returns:
            List of detected framework names
        """
        if sample_files is None:
            sample_files = self._get_sample_source_files()

        framework_mentions = Counter()

        for file_path in sample_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                for framework, patterns in self.FRAMEWORK_PATTERNS.items():
                    if any(pattern in content for pattern in patterns):
                        framework_mentions[framework] += 1

            except Exception as e:
                self.logger.debug(f"Error analyzing {file_path}: {e}")

        # Return frameworks mentioned in multiple files
        return [fw for fw, count in framework_mentions.items() if count >= 2]

    def analyze_code_style(
        self, sample_files: Optional[List[Path]] = None
    ) -> List[str]:
        """Analyze coding style and conventions.

        WHY: Understanding code style helps agents generate code that
        matches the project's existing patterns.

        Args:
            sample_files: Optional list of files to analyze

        Returns:
            List of detected code conventions
        """
        if sample_files is None:
            sample_files = self._get_sample_source_files(limit=10)

        conventions = []
        pattern_counts = Counter()

        for file_path in sample_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Check for common patterns
                if "class " in content and "def __init__" in content:
                    pattern_counts["object_oriented"] += 1
                if "async def" in content or "async function" in content:
                    pattern_counts["async_programming"] += 1
                if "@property" in content or "@decorator" in content:
                    pattern_counts["decorators"] += 1
                if "type:" in content or "->" in content:
                    pattern_counts["type_hints"] += 1
                if re.search(r'""".*?"""', content, re.DOTALL):
                    pattern_counts["docstrings"] += 1

            except Exception as e:
                self.logger.debug(f"Error analyzing {file_path}: {e}")

        # Include patterns found in multiple files
        for pattern, count in pattern_counts.items():
            if count >= 2:
                conventions.append(pattern.replace("_", " ").title())

        return conventions

    def _count_files_by_extension(self) -> Dict[str, int]:
        """Count files by extension in the project."""
        counts = Counter()

        for ext in self.FILE_EXTENSIONS:
            files = list(self.working_directory.rglob(f"*{ext}"))
            # Filter out vendor directories
            files = [
                f
                for f in files
                if not any(
                    part in [".git", "node_modules", "vendor", "__pycache__"]
                    for part in f.parts
                )
            ]
            if files:
                counts[ext] = len(files)

        return dict(counts)

    def _get_sample_source_files(self, limit: int = 20) -> List[Path]:
        """Get a sample of source files for analysis."""
        source_files = []

        for ext in self.FILE_EXTENSIONS:
            files = list(self.working_directory.rglob(f"*{ext}"))
            # Filter out vendor directories
            files = [
                f
                for f in files
                if not any(
                    part in [".git", "node_modules", "vendor", "__pycache__"]
                    for part in f.parts
                )
            ]
            source_files.extend(files[:5])  # Take up to 5 files per extension

        return source_files[:limit]
