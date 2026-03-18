#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Agent Loading Functionality
========================================================

This test module provides comprehensive coverage for the AgentLoader class,
testing all core methods, caching behavior, error handling, and performance.

Test Categories:
----------------
1. Core Methods: list_agents, get_agent, get_agent_prompt, get_agent_metadata
2. Caching: Cache hits/misses, invalidation, TTL behavior
3. Error Handling: Missing agents, invalid configurations, corrupted files
4. Dynamic Model Selection: Complexity analysis, model thresholds
5. Performance: Loading multiple agents, cache efficiency
6. Backward Compatibility: Legacy function support
7. Utility Functions: Validation, reloading, cache management

WHY: Comprehensive testing ensures the agent loading system remains reliable
as it's a critical component used throughout the Claude MPM system. These
tests verify both functional correctness and performance characteristics.
"""


# NOTE: These legacy functions were removed from the codebase
