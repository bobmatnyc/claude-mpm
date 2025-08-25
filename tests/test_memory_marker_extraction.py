"""Test the new explicit marker-based memory extraction.

WHY: We need to verify that the new memory extraction system correctly
identifies and extracts learnings using the # Add To Memory: format.

DESIGN DECISION: Test both positive cases (valid formats) and edge cases
(invalid formats, malformed blocks, etc.) to ensure robustness.
"""

import pytest

from claude_mpm.hooks.memory_integration_hook import MemoryPostDelegationHook


def test_single_memory_extraction():
    """Test extracting a single memory entry."""
    hook = MemoryPostDelegationHook()

    text = """
    I've analyzed the codebase and found an important pattern.

    # Add To Memory:
    Type: pattern
    Content: All services use dependency injection for flexibility
    #

    This pattern ensures loose coupling.
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["pattern"]) == 1
    assert (
        learnings["pattern"][0]
        == "All services use dependency injection for flexibility"
    )


def test_multiple_memory_extraction():
    """Test extracting multiple memory entries."""
    hook = MemoryPostDelegationHook()

    text = """
    After reviewing the code, I've learned several things:

    # Add To Memory:
    Type: pattern
    Content: All services use dependency injection for flexibility
    #

    Also, I noticed a common mistake:

    # Add To Memory:
    Type: mistake
    Content: Never hardcode paths, always use get_path_manager()
    #

    And an architectural insight:

    # Add To Memory:
    Type: architecture
    Content: The system uses a layered architecture with clear boundaries
    #
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["pattern"]) == 1
    assert len(learnings["mistake"]) == 1
    assert len(learnings["architecture"]) == 1
    assert (
        learnings["pattern"][0]
        == "All services use dependency injection for flexibility"
    )
    assert (
        learnings["mistake"][0] == "Never hardcode paths, always use get_path_manager()"
    )
    assert (
        learnings["architecture"][0]
        == "The system uses a layered architecture with clear boundaries"
    )


def test_multiline_content_extraction():
    """Test that multiline content takes only the first line."""
    hook = MemoryPostDelegationHook()

    text = """
    # Add To Memory:
    Type: guideline
    Content: Always validate input parameters
    This is especially important for user-facing APIs
    to prevent security vulnerabilities
    #
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["guideline"]) == 1
    assert learnings["guideline"][0] == "Always validate input parameters"


def test_invalid_type_rejection():
    """Test that invalid types are rejected."""
    hook = MemoryPostDelegationHook()

    text = """
    # Add To Memory:
    Type: random_type
    Content: This should not be extracted
    #
    """

    learnings = hook._extract_learnings(text)

    # Should not extract anything for invalid type
    assert all(len(items) == 0 for items in learnings.values())


def test_length_validation():
    """Test that content length is validated."""
    hook = MemoryPostDelegationHook()

    text = """
    # Add To Memory:
    Type: pattern
    Content: Short
    #

    # Add To Memory:
    Type: pattern
    Content: This is a very long content that exceeds the 100 character limit and should not be extracted because it's too verbose
    #

    # Add To Memory:
    Type: pattern
    Content: This content is just right - not too short and not too long
    #
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["pattern"]) == 1
    assert (
        learnings["pattern"][0]
        == "This content is just right - not too short and not too long"
    )


def test_duplicate_detection():
    """Test that duplicates are not added."""
    hook = MemoryPostDelegationHook()

    text = """
    # Add To Memory:
    Type: pattern
    Content: Use dependency injection
    #

    # Add To Memory:
    Type: pattern
    Content: Use dependency injection
    #

    # Add To Memory:
    Type: pattern
    Content: USE DEPENDENCY INJECTION
    #
    """

    learnings = hook._extract_learnings(text)

    # Should only have one entry (case-insensitive duplicate detection)
    assert len(learnings["pattern"]) == 1


def test_all_supported_types():
    """Test that all supported types work correctly."""
    hook = MemoryPostDelegationHook()

    text = """
    # Add To Memory:
    Type: pattern
    Content: Pattern example content
    #

    # Add To Memory:
    Type: architecture
    Content: Architecture example content
    #

    # Add To Memory:
    Type: guideline
    Content: Guideline example content
    #

    # Add To Memory:
    Type: mistake
    Content: Mistake example content
    #

    # Add To Memory:
    Type: strategy
    Content: Strategy example content
    #

    # Add To Memory:
    Type: integration
    Content: Integration example content
    #

    # Add To Memory:
    Type: performance
    Content: Performance example content
    #

    # Add To Memory:
    Type: context
    Content: Context example content
    #
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["pattern"]) == 1
    assert len(learnings["architecture"]) == 1
    assert len(learnings["guideline"]) == 1
    assert len(learnings["mistake"]) == 1
    assert len(learnings["strategy"]) == 1
    assert len(learnings["integration"]) == 1
    assert len(learnings["performance"]) == 1
    assert len(learnings["context"]) == 1


def test_case_insensitive_markers():
    """Test that markers are case-insensitive."""
    hook = MemoryPostDelegationHook()

    text = """
    # add to memory:
    type: PATTERN
    content: Case insensitive test
    #

    # ADD TO MEMORY:
    Type: Pattern
    Content: Another case test
    #
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["pattern"]) == 2


def test_memorize_trigger():
    """Test that 'Memorize' trigger phrase works."""
    hook = MemoryPostDelegationHook()

    text = """
    I've learned something important about the architecture.

    # Memorize:
    Type: architecture
    Content: Services communicate through message queues for reliability
    #

    This pattern ensures loose coupling between services.
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["architecture"]) == 1
    assert (
        learnings["architecture"][0]
        == "Services communicate through message queues for reliability"
    )


def test_remember_trigger():
    """Test that 'Remember' trigger phrase works."""
    hook = MemoryPostDelegationHook()

    text = """
    I discovered a common mistake that should be avoided.

    # Remember:
    Type: mistake
    Content: Never expose internal IDs in public APIs
    #

    This prevents security vulnerabilities.
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["mistake"]) == 1
    assert learnings["mistake"][0] == "Never expose internal IDs in public APIs"


def test_all_trigger_phrases():
    """Test that all trigger phrases work together."""
    hook = MemoryPostDelegationHook()

    text = """
    # Add To Memory:
    Type: pattern
    Content: Use dependency injection for testability
    #

    # Memorize:
    Type: guideline
    Content: Always validate user input at API boundaries
    #

    # Remember:
    Type: mistake
    Content: Don't forget to handle edge cases in validation
    #
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["pattern"]) == 1
    assert len(learnings["guideline"]) == 1
    assert len(learnings["mistake"]) == 1
    assert learnings["pattern"][0] == "Use dependency injection for testability"
    assert learnings["guideline"][0] == "Always validate user input at API boundaries"
    assert learnings["mistake"][0] == "Don't forget to handle edge cases in validation"


def test_trigger_phrases_case_insensitive():
    """Test that all trigger phrases are case-insensitive."""
    hook = MemoryPostDelegationHook()

    text = """
    # memorize:
    Type: strategy
    Content: Use caching for frequently accessed data
    #

    # REMEMBER:
    Type: performance
    Content: Database queries should use indexes
    #

    # Remember:
    Type: integration
    Content: Always handle timeout scenarios gracefully
    #
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["strategy"]) == 1
    assert len(learnings["performance"]) == 1
    assert len(learnings["integration"]) == 1
    assert learnings["strategy"][0] == "Use caching for frequently accessed data"
    assert learnings["performance"][0] == "Database queries should use indexes"
    assert learnings["integration"][0] == "Always handle timeout scenarios gracefully"


def test_whitespace_handling():
    """Test that extra whitespace is handled correctly."""
    hook = MemoryPostDelegationHook()

    text = """
    #  Add To Memory:
    Type:  pattern
    Content:   Whitespace should be trimmed
    #
    """

    learnings = hook._extract_learnings(text)

    assert len(learnings["pattern"]) == 1
    assert learnings["pattern"][0] == "Whitespace should be trimmed"


def test_malformed_blocks():
    """Test that malformed blocks are ignored."""
    hook = MemoryPostDelegationHook()

    text = """
    # Add To Memory:
    Missing type and content
    #

    # Add To Memory:
    Type: pattern
    # Missing content

    # Add To Memory:
    Content: Missing type
    #

    Add To Memory:
    Type: pattern
    Content: Missing opening marker
    #

    # Add To Memory:
    Type: pattern
    Content: Missing closing marker

    # Add To Memory:
    Type: pattern
    Content: Valid entry for comparison
    #
    """

    learnings = hook._extract_learnings(text)

    # Should only extract the valid entry
    assert len(learnings["pattern"]) == 1
    assert learnings["pattern"][0] == "Valid entry for comparison"


def test_integration_all_trigger_phrases():
    """Integration test that all trigger phrases work in a realistic scenario."""
    hook = MemoryPostDelegationHook()

    # Simulate a realistic agent response with multiple learnings using different triggers
    agent_response = """
    I've completed the authentication system implementation. Here's what I learned:

    First, about the pattern we should follow:
    # Add To Memory:
    Type: pattern
    Content: Always use JWT with refresh tokens for web applications
    #

    Something important to memorize for future reference:
    # Memorize:
    Type: architecture
    Content: Authentication service should be stateless and horizontally scalable
    #

    And let me remember this mistake I made initially:
    # Remember:
    Type: mistake
    Content: Don't store sensitive data in JWT payload
    #

    Also, a guideline for the team:
    # memorize:
    Type: guideline
    Content: Use rate limiting on all authentication endpoints
    #

    Performance consideration to remember:
    # REMEMBER:
    Type: performance
    Content: Cache user permissions to reduce database queries
    #

    The implementation is complete and follows our security standards.
    """

    learnings = hook._extract_learnings(agent_response)

    # Verify all learnings were extracted correctly
    assert len(learnings["pattern"]) == 1
    assert len(learnings["architecture"]) == 1
    assert len(learnings["mistake"]) == 1
    assert len(learnings["guideline"]) == 1
    assert len(learnings["performance"]) == 1

    # Verify content is correct
    assert (
        learnings["pattern"][0]
        == "Always use JWT with refresh tokens for web applications"
    )
    assert (
        learnings["architecture"][0]
        == "Authentication service should be stateless and horizontally scalable"
    )
    assert learnings["mistake"][0] == "Don't store sensitive data in JWT payload"
    assert (
        learnings["guideline"][0] == "Use rate limiting on all authentication endpoints"
    )
    assert (
        learnings["performance"][0]
        == "Cache user permissions to reduce database queries"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
