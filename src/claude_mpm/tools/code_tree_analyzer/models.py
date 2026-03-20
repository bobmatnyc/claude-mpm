#!/usr/bin/env python3
"""
Code Tree Models
================

Data structures for representing code nodes in the analysis tree.

WHY: Centralizes data models for clean separation between data and logic.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CodeNode:
    """Represents a node in the code tree."""

    file_path: str
    node_type: str
    name: str
    line_start: int
    line_end: int
    complexity: int = 0
    has_docstring: bool = False
    decorators: list[str] = None
    parent: str | None = None
    children: list["CodeNode"] = None
    language: str = "python"
    signature: str = ""
    metrics: dict[str, Any] = None

    def __post_init__(self):
        if self.decorators is None:
            self.decorators = []
        if self.children is None:
            self.children = []
        if self.metrics is None:
            self.metrics = {}
