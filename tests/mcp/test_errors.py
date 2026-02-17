"""Tests for MCP session error classes.

Tests SessionError hierarchy and parse_error() routing logic.
"""

import pytest

from claude_mpm.mcp.errors import (
    APIError,
    ContextWindowError,
    RateLimitError,
    SessionError,
    parse_error,
)


class TestSessionError:
    """Tests for base SessionError class."""

    def test_basic_instantiation(self):
        """SessionError should be created with message only."""
        error = SessionError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.session_id is None
        assert error.retry_after is None

    def test_with_session_id(self):
        """SessionError should accept session_id."""
        error = SessionError("Error occurred", session_id="sess-123")

        assert str(error) == "Error occurred"
        assert error.session_id == "sess-123"
        assert error.retry_after is None

    def test_with_retry_after(self):
        """SessionError should accept retry_after."""
        error = SessionError("Rate limited", retry_after=60)

        assert str(error) == "Rate limited"
        assert error.retry_after == 60

    def test_with_all_parameters(self):
        """SessionError should accept all parameters."""
        error = SessionError("Full error", session_id="sess-456", retry_after=120)

        assert str(error) == "Full error"
        assert error.session_id == "sess-456"
        assert error.retry_after == 120

    def test_is_exception(self):
        """SessionError should be an Exception."""
        error = SessionError("Test")
        assert isinstance(error, Exception)

    def test_can_be_raised(self):
        """SessionError should be raiseable."""
        with pytest.raises(SessionError) as exc_info:
            raise SessionError("Raised error", session_id="test-id")

        assert str(exc_info.value) == "Raised error"
        assert exc_info.value.session_id == "test-id"


class TestRateLimitError:
    """Tests for RateLimitError class."""

    def test_basic_instantiation(self):
        """RateLimitError should be created with message."""
        error = RateLimitError("Rate limit exceeded")

        assert str(error) == "Rate limit exceeded"
        assert isinstance(error, SessionError)

    def test_with_retry_after(self):
        """RateLimitError should accept retry_after."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)

        assert error.retry_after == 60

    def test_with_session_id(self):
        """RateLimitError should accept session_id."""
        error = RateLimitError(
            "Rate limit exceeded", session_id="sess-123", retry_after=30
        )

        assert error.session_id == "sess-123"
        assert error.retry_after == 30

    def test_inheritance(self):
        """RateLimitError should inherit from SessionError."""
        error = RateLimitError("Test")
        assert isinstance(error, SessionError)
        assert isinstance(error, Exception)


class TestContextWindowError:
    """Tests for ContextWindowError class."""

    def test_basic_instantiation(self):
        """ContextWindowError should be created with message."""
        error = ContextWindowError("Context window exceeded")

        assert str(error) == "Context window exceeded"
        assert isinstance(error, SessionError)

    def test_with_session_id(self):
        """ContextWindowError should accept session_id."""
        error = ContextWindowError("Context too large", session_id="sess-456")

        assert error.session_id == "sess-456"

    def test_inheritance(self):
        """ContextWindowError should inherit from SessionError."""
        error = ContextWindowError("Test")
        assert isinstance(error, SessionError)
        assert isinstance(error, Exception)


class TestAPIError:
    """Tests for APIError class."""

    def test_basic_instantiation(self):
        """APIError should be created with message."""
        error = APIError("API request failed")

        assert str(error) == "API request failed"
        assert isinstance(error, SessionError)

    def test_with_session_id(self):
        """APIError should accept session_id."""
        error = APIError("API error", session_id="sess-789")

        assert error.session_id == "sess-789"

    def test_inheritance(self):
        """APIError should inherit from SessionError."""
        error = APIError("Test")
        assert isinstance(error, SessionError)
        assert isinstance(error, Exception)


class TestParseError:
    """Tests for parse_error() function routing logic."""

    def test_rate_limit_error_lowercase(self):
        """parse_error should detect rate limit in lowercase."""
        result = {"error": "rate limit exceeded, please retry later"}

        error = parse_error(result)

        assert isinstance(error, RateLimitError)
        assert "rate limit" in str(error).lower()

    def test_rate_limit_error_mixed_case(self):
        """parse_error should detect Rate Limit in mixed case."""
        result = {"error": "Rate Limit error occurred"}

        error = parse_error(result)

        assert isinstance(error, RateLimitError)

    def test_rate_limit_with_retry_after(self):
        """parse_error should use retry_after from result if provided."""
        result = {
            "error": "rate limit exceeded",
            "retry_after": 30,
        }

        error = parse_error(result)

        assert isinstance(error, RateLimitError)
        assert error.retry_after == 30

    def test_rate_limit_default_retry_after(self):
        """parse_error should default retry_after to 60 for rate limits."""
        result = {"error": "rate limit exceeded"}

        error = parse_error(result)

        assert isinstance(error, RateLimitError)
        assert error.retry_after == 60

    def test_context_window_error(self):
        """parse_error should detect context window error."""
        result = {"error": "Context window size exceeded"}

        error = parse_error(result)

        assert isinstance(error, ContextWindowError)

    def test_context_window_error_lowercase(self):
        """parse_error should detect context window in lowercase."""
        result = {"error": "the context window has been exceeded"}

        error = parse_error(result)

        assert isinstance(error, ContextWindowError)

    def test_context_window_partial_match(self):
        """parse_error should require both 'context' and 'window'."""
        # Only 'context' - should not match
        result1 = {"error": "invalid context provided"}
        error1 = parse_error(result1)
        assert not isinstance(error1, ContextWindowError)
        assert isinstance(error1, SessionError)

        # Only 'window' - should not match
        result2 = {"error": "window closed unexpectedly"}
        error2 = parse_error(result2)
        assert not isinstance(error2, ContextWindowError)
        assert isinstance(error2, SessionError)

    def test_api_error(self):
        """parse_error should detect API error."""
        result = {"error": "API request failed with status 500"}

        error = parse_error(result)

        assert isinstance(error, APIError)

    def test_api_error_lowercase(self):
        """parse_error should detect api in lowercase."""
        result = {"error": "api connection timeout"}

        error = parse_error(result)

        assert isinstance(error, APIError)

    def test_generic_session_error(self):
        """parse_error should return SessionError for unrecognized errors."""
        result = {"error": "Unknown error occurred"}

        error = parse_error(result)

        assert type(error) is SessionError
        assert not isinstance(error, RateLimitError)
        assert not isinstance(error, ContextWindowError)
        assert not isinstance(error, APIError)

    def test_session_id_passed_through(self):
        """parse_error should pass session_id to error."""
        result = {
            "error": "Something failed",
            "session_id": "sess-test-123",
        }

        error = parse_error(result)

        assert error.session_id == "sess-test-123"

    def test_session_id_with_specific_error_types(self):
        """parse_error should pass session_id for all error types."""
        # Rate limit
        result1 = {"error": "rate limit", "session_id": "sess-1"}
        assert parse_error(result1).session_id == "sess-1"

        # Context window
        result2 = {"error": "context window", "session_id": "sess-2"}
        assert parse_error(result2).session_id == "sess-2"

        # API error
        result3 = {"error": "api error", "session_id": "sess-3"}
        assert parse_error(result3).session_id == "sess-3"

    def test_missing_error_key(self):
        """parse_error should handle missing error key."""
        result = {"session_id": "test"}

        error = parse_error(result)

        assert str(error) == "Unknown error"

    def test_empty_result(self):
        """parse_error should handle empty result dict."""
        result = {}

        error = parse_error(result)

        assert str(error) == "Unknown error"
        assert error.session_id is None

    def test_retry_after_only_for_rate_limit(self):
        """parse_error should only use retry_after for rate limit errors."""
        # API error with retry_after - should be ignored
        result = {
            "error": "api error occurred",
            "retry_after": 30,
        }

        error = parse_error(result)

        assert isinstance(error, APIError)
        # APIError doesn't use retry_after from result
        assert error.retry_after is None
