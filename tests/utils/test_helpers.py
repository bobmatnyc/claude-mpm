"""Test Helper Utilities for Claude MPM.

This module provides utility functions to replace anti-patterns in tests,
including sleep() replacement, custom assertions, and common test patterns.

Anti-Pattern Replacements:
- wait_for_condition() replaces time.sleep()
- Event-driven synchronization helpers
- Custom assertions for common patterns

Usage:
    from tests.utils.test_helpers import wait_for_condition

    # Instead of time.sleep(5)
    assert wait_for_condition(
        lambda: service.is_ready(),
        timeout=5,
        message="Service did not become ready"
    )
"""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

# ============================================================================
# SYNCHRONIZATION HELPERS (Replaces sleep())
# ============================================================================


def wait_for_condition(
    predicate: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.1,
    message: str = "Condition not met within timeout",
) -> bool:
    """Wait for a condition to become true with timeout.

    This is the primary replacement for time.sleep() calls in tests.
    Instead of blindly waiting, this actively checks for the condition
    to become true and returns immediately when it does.

    Args:
        predicate: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds (default: 5.0)
        interval: Check interval in seconds (default: 0.1)
        message: Error message if timeout occurs

    Returns:
        True if condition met, False if timeout

    Example:
        # Instead of:
        # time.sleep(5)
        # assert operation_complete()

        # Use:
        assert wait_for_condition(
            lambda: operation_complete(),
            timeout=5,
            message="Operation did not complete"
        )
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if predicate():
            return True
        time.sleep(interval)

    # Condition not met within timeout
    return False


async def wait_for_condition_async(
    predicate: Callable[[], bool],
    timeout: float = 5.0,
    interval: float = 0.1,
    message: str = "Condition not met within timeout",
) -> bool:
    """Async version of wait_for_condition.

    Args:
        predicate: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds (default: 5.0)
        interval: Check interval in seconds (default: 0.1)
        message: Error message if timeout occurs

    Returns:
        True if condition met, False if timeout

    Example:
        assert await wait_for_condition_async(
            lambda: service.is_ready(),
            timeout=5
        )
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if predicate():
            return True
        await asyncio.sleep(interval)

    return False


def wait_for_value(
    getter: Callable[[], Any],
    expected_value: Any,
    timeout: float = 5.0,
    interval: float = 0.1,
) -> bool:
    """Wait for a getter to return expected value.

    Args:
        getter: Function that returns a value to check
        expected_value: Value to wait for
        timeout: Maximum time to wait in seconds
        interval: Check interval in seconds

    Returns:
        True if value matches, False if timeout

    Example:
        # Wait for status to become "ready"
        assert wait_for_value(
            lambda: service.get_status(),
            "ready",
            timeout=3
        )
    """
    return wait_for_condition(
        lambda: getter() == expected_value,
        timeout=timeout,
        interval=interval,
        message=f"Value did not become {expected_value}",
    )


def wait_for_event(
    event_checker: Callable[[], bool], timeout: float = 5.0, event_name: str = "event"
) -> bool:
    """Wait for an event to occur.

    Args:
        event_checker: Function that returns True when event occurred
        timeout: Maximum time to wait in seconds
        event_name: Event description for error messages

    Returns:
        True if event occurred, False if timeout

    Example:
        event_occurred = False

        def on_event():
            nonlocal event_occurred
            event_occurred = True

        event_bus.on("test.event", on_event)
        trigger_event()

        assert wait_for_event(
            lambda: event_occurred,
            timeout=2,
            event_name="test.event"
        )
    """
    return wait_for_condition(
        event_checker, timeout=timeout, message=f"Event '{event_name}' did not occur"
    )


# ============================================================================
# CUSTOM ASSERTIONS
# ============================================================================


def assert_eventually(
    predicate: Callable[[], bool], timeout: float = 5.0, message: Optional[str] = None
) -> None:
    """Assert that condition becomes true eventually.

    Raises AssertionError if condition doesn't become true within timeout.

    Args:
        predicate: Condition to check
        timeout: Maximum wait time
        message: Custom error message

    Raises:
        AssertionError: If condition not met within timeout

    Example:
        assert_eventually(
            lambda: service.is_initialized(),
            timeout=3,
            message="Service failed to initialize"
        )
    """
    result = wait_for_condition(
        predicate, timeout=timeout, message=message or "Condition not met"
    )

    if not result:
        raise AssertionError(message or "Condition not met within timeout")


def assert_dict_contains(
    actual: Dict, expected: Dict, message: Optional[str] = None
) -> None:
    """Assert that actual dict contains all expected key-value pairs.

    Args:
        actual: Dictionary to check
        expected: Expected key-value pairs
        message: Custom error message

    Raises:
        AssertionError: If expected keys/values not in actual

    Example:
        response = {"status": "ok", "code": 200, "data": {...}}
        assert_dict_contains(response, {"status": "ok", "code": 200})
    """
    for key, value in expected.items():
        if key not in actual:
            raise AssertionError(message or f"Key '{key}' not found in actual dict")
        if actual[key] != value:
            raise AssertionError(
                message or f"Key '{key}': expected {value}, got {actual[key]}"
            )


def assert_list_contains_items(
    actual: List, expected_items: List, message: Optional[str] = None
) -> None:
    """Assert that list contains all expected items.

    Args:
        actual: List to check
        expected_items: Items that should be in list
        message: Custom error message

    Raises:
        AssertionError: If any expected item not in list

    Example:
        results = ["apple", "banana", "cherry"]
        assert_list_contains_items(results, ["apple", "banana"])
    """
    for item in expected_items:
        if item not in actual:
            raise AssertionError(message or f"Item '{item}' not found in list")


def assert_called_with_eventually(
    mock_obj, *args, timeout: float = 5.0, **kwargs
) -> None:
    """Assert that mock was called with specific args eventually.

    Args:
        mock_obj: Mock object to check
        *args: Expected positional arguments
        timeout: Maximum wait time
        **kwargs: Expected keyword arguments

    Raises:
        AssertionError: If mock not called with args within timeout

    Example:
        mock_handler = Mock()
        trigger_async_operation()

        assert_called_with_eventually(
            mock_handler,
            "expected_arg",
            timeout=2
        )
    """

    def check_called():
        try:
            mock_obj.assert_called_with(*args, **kwargs)
            return True
        except AssertionError:
            return False

    result = wait_for_condition(
        check_called, timeout=timeout, message="Mock not called with expected args"
    )

    if not result:
        raise AssertionError(
            f"Mock not called with args {args} and kwargs {kwargs} within {timeout}s"
        )


# ============================================================================
# TEST FIXTURES HELPERS
# ============================================================================


def create_mock_with_methods(methods: Dict[str, Any]):
    """Create a mock object with predefined method return values.

    Args:
        methods: Dict mapping method names to return values

    Returns:
        Mock object with configured methods

    Example:
        mock_service = create_mock_with_methods({
            "get_status": "ready",
            "get_count": 42,
            "is_active": True
        })

        assert mock_service.get_status() == "ready"
    """
    from unittest.mock import Mock

    mock = Mock()
    for method_name, return_value in methods.items():
        getattr(mock, method_name).return_value = return_value

    return mock


def create_async_mock_with_methods(methods: Dict[str, Any]):
    """Create an async mock object with predefined method return values.

    Args:
        methods: Dict mapping method names to return values

    Returns:
        AsyncMock object with configured methods

    Example:
        mock_service = create_async_mock_with_methods({
            "fetch_data": {"status": "ok"},
            "process": True
        })

        result = await mock_service.fetch_data()
        assert result == {"status": "ok"}
    """
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    for method_name, return_value in methods.items():
        getattr(mock, method_name).return_value = return_value

    return mock


# ============================================================================
# PERFORMANCE HELPERS
# ============================================================================


class PerformanceAssertion:
    """Context manager for asserting execution time.

    Example:
        with PerformanceAssertion(max_duration=1.0, operation="API call"):
            result = expensive_operation()
    """

    def __init__(
        self,
        max_duration: float,
        operation: str = "operation",
        min_duration: Optional[float] = None,
    ):
        """Initialize performance assertion.

        Args:
            max_duration: Maximum allowed duration in seconds
            operation: Operation description for error messages
            min_duration: Optional minimum duration (for testing delays)
        """
        self.max_duration = max_duration
        self.min_duration = min_duration
        self.operation = operation
        self.start_time = None
        self.duration = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Check duration."""
        self.duration = time.time() - self.start_time

        if self.duration > self.max_duration:
            raise AssertionError(
                f"{self.operation} took {self.duration:.3f}s, "
                f"expected < {self.max_duration}s"
            )

        if self.min_duration and self.duration < self.min_duration:
            raise AssertionError(
                f"{self.operation} took {self.duration:.3f}s, "
                f"expected >= {self.min_duration}s"
            )


def assert_completes_quickly(
    func: Callable, max_duration: float = 1.0, *args, **kwargs
) -> Any:
    """Assert that function completes within time limit.

    Args:
        func: Function to execute
        max_duration: Maximum allowed duration in seconds
        *args: Function positional arguments
        **kwargs: Function keyword arguments

    Returns:
        Function return value

    Raises:
        AssertionError: If function takes longer than max_duration

    Example:
        result = assert_completes_quickly(
            parse_large_file,
            max_duration=2.0,
            filepath="data.json"
        )
    """
    with PerformanceAssertion(max_duration, operation=func.__name__):
        return func(*args, **kwargs)


# ============================================================================
# ASYNC TEST HELPERS
# ============================================================================


def run_async_test(async_func: Callable, *args, **kwargs) -> Any:
    """Run async function in sync test context.

    Args:
        async_func: Async function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result

    Example:
        # In a sync test function
        result = run_async_test(async_fetch_data, url="http://example.com")
    """
    return asyncio.run(async_func(*args, **kwargs))


async def gather_with_timeout(*tasks, timeout: float = 10.0) -> List[Any]:
    """Gather async tasks with timeout.

    Args:
        *tasks: Async tasks to gather
        timeout: Maximum wait time

    Returns:
        List of results

    Raises:
        asyncio.TimeoutError: If tasks don't complete in time

    Example:
        results = await gather_with_timeout(
            fetch_user(1),
            fetch_user(2),
            fetch_user(3),
            timeout=5.0
        )
    """
    return await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)


# ============================================================================
# MOCK VERIFICATION HELPERS
# ============================================================================


def assert_mock_call_order(mock_obj, expected_calls: List[str]) -> None:
    """Assert that mock methods were called in specific order.

    Args:
        mock_obj: Mock object to check
        expected_calls: List of method names in expected order

    Raises:
        AssertionError: If calls don't match expected order

    Example:
        mock_service = Mock()
        mock_service.initialize()
        mock_service.process()
        mock_service.finalize()

        assert_mock_call_order(
            mock_service,
            ["initialize", "process", "finalize"]
        )
    """
    actual_calls = [call[0] for call in mock_obj.method_calls]
    actual_call_names = [call for call in actual_calls if isinstance(call, str)]

    if actual_call_names != expected_calls:
        raise AssertionError(
            f"Expected call order: {expected_calls}, but got: {actual_call_names}"
        )


def reset_all_mocks(*mocks) -> None:
    """Reset multiple mock objects.

    Args:
        *mocks: Mock objects to reset

    Example:
        reset_all_mocks(mock1, mock2, mock3)
    """
    for mock in mocks:
        if hasattr(mock, "reset_mock"):
            mock.reset_mock()


# ============================================================================
# FILE AND PATH HELPERS
# ============================================================================


def create_temp_file(tmp_path, filename: str, content: str = "") -> Any:
    """Create temporary file for testing.

    Args:
        tmp_path: pytest tmp_path fixture
        filename: Name of file to create
        content: File content

    Returns:
        Path object for created file

    Example:
        def test_file_parsing(tmp_path):
            test_file = create_temp_file(
                tmp_path,
                "test.json",
                '{"key": "value"}'
            )
            result = parse_file(test_file)
            assert result["key"] == "value"
    """
    file_path = tmp_path / filename
    file_path.write_text(content)
    return file_path


def create_temp_directory(
    tmp_path, dirname: str, files: Optional[Dict[str, str]] = None
):
    """Create temporary directory with files.

    Args:
        tmp_path: pytest tmp_path fixture
        dirname: Directory name
        files: Optional dict of filename -> content

    Returns:
        Path object for created directory

    Example:
        test_dir = create_temp_directory(
            tmp_path,
            "project",
            {
                "config.json": "{}",
                "data.txt": "test data"
            }
        )
    """
    dir_path = tmp_path / dirname
    dir_path.mkdir(parents=True, exist_ok=True)

    if files:
        for filename, content in files.items():
            (dir_path / filename).write_text(content)

    return dir_path


# ============================================================================
# EXAMPLE USAGE PATTERNS
# ============================================================================


"""
ANTI-PATTERN REPLACEMENT EXAMPLES:

1. Replace sleep() with wait_for_condition():

    ❌ BEFORE:
    def test_async_operation():
        start_operation()
        time.sleep(5)
        assert operation_complete()

    ✅ AFTER:
    def test_async_operation():
        start_operation()
        assert wait_for_condition(
            lambda: operation_complete(),
            timeout=5,
            message="Operation did not complete"
        )

2. Replace print() with proper assertions:

    ❌ BEFORE:
    def test_calculation():
        result = calculate(5, 10)
        print(f"Result: {result}")  # Debugging
        assert result == 15

    ✅ AFTER:
    def test_calculation():
        result = calculate(5, 10)
        assert result == 15  # Failures show result automatically

3. Event-driven synchronization:

    ❌ BEFORE:
    def test_event_handler():
        event_bus.publish("test.event")
        time.sleep(0.5)  # Wait for handler
        assert handler_called

    ✅ AFTER:
    def test_event_handler():
        event_bus.publish("test.event")
        assert wait_for_event(
            lambda: handler_called,
            timeout=1,
            event_name="test.event"
        )

4. Performance assertions:

    ✅ GOOD:
    def test_performance():
        with PerformanceAssertion(max_duration=1.0, operation="search"):
            results = search_large_dataset(query)
        assert len(results) > 0
"""
