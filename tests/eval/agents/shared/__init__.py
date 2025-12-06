"""
Shared utilities for agent evaluation testing.

This module provides common infrastructure for testing BASE_AGENT
and specialized agents (Research, Engineer, QA, Ops, Documentation, Prompt Engineer).

Exports:
    - AgentResponseParser: Generic agent response parser
    - AgentTestBase: Base test class for agent testing
    - Common fixtures for agent testing
    - Shared metric utilities
"""

from .agent_response_parser import (
    AgentResponseAnalysis,
    AgentResponseParser,
    AgentType,
    MemoryCapture,
    ToolUsage,
    VerificationEvent,
    parse_agent_response,
)

__all__ = [
    "AgentResponseParser",
    "AgentResponseAnalysis",
    "AgentType",
    "ToolUsage",
    "VerificationEvent",
    "MemoryCapture",
    "parse_agent_response",
]
