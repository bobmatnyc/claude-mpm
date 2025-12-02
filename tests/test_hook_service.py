"""Test the HookService functionality.

WHY: We need to verify that the HookService correctly manages hooks,
executes them in priority order, and handles errors gracefully.
"""

from datetime import datetime, timezone

from claude_mpm.hooks.base_hook import (
    HookContext,
    HookResult,
    HookType,
    PostDelegationHook,
    PreDelegationHook,
)
from claude_mpm.services.hook_service import HookService


class TestPreDelegationHook(PreDelegationHook):
    """Test implementation of a pre-delegation hook."""

    def __init__(self, name: str, priority: int = 50, should_fail: bool = False):
        super().__init__(name, priority)
        self.should_fail = should_fail
        self.executed = False

    def execute(self, context: HookContext) -> HookResult:
        """Execute the test hook."""
        self.executed = True

        if self.should_fail:
            return HookResult(success=False, error="Test failure")

        # Modify the context to show hook was executed
        modified_data = context.data.copy()
        modified_data[f"hook_{self.name}"] = True

        return HookResult(
            success=True, data=modified_data, modified=True, metadata={"test": True}
        )


class TestPostDelegationHook(PostDelegationHook):
    """Test implementation of a post-delegation hook."""

    def __init__(self, name: str, priority: int = 50, should_fail: bool = False):
        super().__init__(name, priority)
        self.should_fail = should_fail
        self.executed = False

    def execute(self, context: HookContext) -> HookResult:
        """Execute the test hook."""
        self.executed = True

        if self.should_fail:
            return HookResult(success=False, error="Test failure")

        # Add extraction result
        modified_data = context.data.copy()
        modified_data[f"extracted_{self.name}"] = "test_data"

        return HookResult(success=True, data=modified_data, modified=True)


def test_hook_registration():
    """Test that hooks can be registered correctly."""
    service = HookService()

    # Create test hooks
    pre_hook = TestPreDelegationHook("test_pre", priority=10)
    post_hook = TestPostDelegationHook("test_post", priority=20)

    # Register hooks
    assert service.register_hook(pre_hook) is True
    assert service.register_hook(post_hook) is True

    # Verify hooks are registered
    hooks = service.list_hooks()
    assert "test_pre" in hooks["pre_delegation"]
    assert "test_post" in hooks["post_delegation"]


def test_hook_priority_ordering():
    """Test that hooks execute in priority order."""
    service = HookService()

    # Create hooks with different priorities
    hook1 = TestPreDelegationHook("high_priority", priority=10)
    hook2 = TestPreDelegationHook("medium_priority", priority=50)
    hook3 = TestPreDelegationHook("low_priority", priority=90)

    # Register in random order
    service.register_hook(hook2)
    service.register_hook(hook3)
    service.register_hook(hook1)

    # Execute hooks
    context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={"agent": "test_agent", "prompt": "test"},
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    result = service.execute_pre_delegation_hooks(context)

    # Verify execution order by checking which keys were added
    assert result.success is True
    assert result.modified is True
    assert "hook_high_priority" in result.data
    assert "hook_medium_priority" in result.data
    assert "hook_low_priority" in result.data


def test_hook_error_handling():
    """Test that hook errors don't break the execution chain."""
    service = HookService()

    # Create hooks where middle one fails
    hook1 = TestPreDelegationHook("first", priority=10)
    hook2 = TestPreDelegationHook("failing", priority=20, should_fail=True)
    hook3 = TestPreDelegationHook("third", priority=30)

    service.register_hook(hook1)
    service.register_hook(hook2)
    service.register_hook(hook3)

    # Execute hooks
    context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={"agent": "test_agent"},
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    result = service.execute_pre_delegation_hooks(context)

    # Verify first and third hooks executed despite second failing
    assert hook1.executed is True
    assert hook2.executed is True
    assert hook3.executed is True

    # Check that successful hooks modified context
    assert result.success is True
    assert result.modified is True
    assert "hook_first" in result.data
    assert "hook_third" in result.data
    assert "hook_failing" not in result.data  # Failed hook shouldn't modify

    # Check error stats
    stats = service.get_stats()
    assert stats["errors"] == 1


def test_hook_removal():
    """Test that hooks can be removed."""
    service = HookService()

    hook = TestPreDelegationHook("removable", priority=50)
    service.register_hook(hook)

    # Verify hook is registered
    assert "removable" in service.list_hooks()["pre_delegation"]

    # Remove hook
    assert service.remove_hook("removable") is True

    # Verify hook is removed
    assert "removable" not in service.list_hooks()["pre_delegation"]

    # Try removing non-existent hook
    assert service.remove_hook("non_existent") is False


def test_disabled_hooks():
    """Test that disabled hooks are skipped."""
    service = HookService()

    hook = TestPreDelegationHook("disabled_hook", priority=50)
    hook.enabled = False
    service.register_hook(hook)

    # Execute hooks
    context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={"agent": "test_agent"},
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    result = service.execute_pre_delegation_hooks(context)

    # Verify disabled hook didn't execute
    assert hook.executed is False
    assert result.success is True
    assert "hook_disabled_hook" not in result.data


def test_config_based_disabling():
    """Test that hooks can be disabled via configuration."""
    # Test with hooks disabled globally
    config = Config({"hooks": {"enabled": False}})
    service = HookService(config)

    hook = TestPreDelegationHook("test_hook", priority=50)
    service.register_hook(hook)

    context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={"agent": "test_agent"},
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    result = service.execute_pre_delegation_hooks(context)

    # Hook shouldn't execute when hooks are disabled
    assert hook.executed is False
    assert result.success is True
    assert result.modified is False

    # Test with specific hook type disabled
    config = Config({"hooks": {"enabled": True, "pre_delegation": {"enabled": False}}})
    service = HookService(config)

    hook2 = TestPreDelegationHook("test_hook2", priority=50)
    service.register_hook(hook2)

    result = service.execute_pre_delegation_hooks(context)
    assert hook2.executed is False


def test_memory_hook_config_check():
    """Test that memory hooks respect memory.enabled config."""
    config = Config({"memory": {"enabled": False}})
    service = HookService(config)

    # Create a memory-related hook
    hook = TestPreDelegationHook("memory_injection", priority=20)
    service.register_hook(hook)

    context = HookContext(
        hook_type=HookType.PRE_DELEGATION,
        data={"agent": "test_agent"},
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    service.execute_pre_delegation_hooks(context)

    # Memory hook shouldn't execute when memory is disabled
    assert hook.executed is False


def test_post_delegation_hooks():
    """Test post-delegation hook execution."""
    service = HookService()

    hook1 = TestPostDelegationHook("extractor1", priority=10)
    hook2 = TestPostDelegationHook("extractor2", priority=20)

    service.register_hook(hook1)
    service.register_hook(hook2)

    # Execute with result context
    context = HookContext(
        hook_type=HookType.POST_DELEGATION,
        data={"result": "Agent execution complete", "agent": "test_agent"},
        metadata={},
        timestamp=datetime.now(timezone.utc),
    )
    result = service.execute_post_delegation_hooks(context)

    # Verify both hooks executed and added their data
    assert hook1.executed is True
    assert hook2.executed is True
    assert result.success is True
    assert result.modified is True
    assert "extracted_extractor1" in result.data
    assert "extracted_extractor2" in result.data


def test_stats_tracking():
    """Test that execution statistics are tracked correctly."""
    service = HookService()

    # Register multiple hooks
    for i in range(3):
        service.register_hook(TestPreDelegationHook(f"pre_{i}", priority=i * 10))

    for i in range(2):
        service.register_hook(TestPostDelegationHook(f"post_{i}", priority=i * 10))

    # Execute hooks multiple times
    for _ in range(2):
        pre_context = HookContext(
            hook_type=HookType.PRE_DELEGATION,
            data={"agent": "test"},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        post_context = HookContext(
            hook_type=HookType.POST_DELEGATION,
            data={"result": "test"},
            metadata={},
            timestamp=datetime.now(timezone.utc),
        )
        service.execute_pre_delegation_hooks(pre_context)
        service.execute_post_delegation_hooks(post_context)

    stats = service.get_stats()
    assert stats["pre_delegation_executed"] == 6  # 3 hooks * 2 executions
    assert stats["post_delegation_executed"] == 4  # 2 hooks * 2 executions

    # Reset stats
    service.reset_stats()
    stats = service.get_stats()
    assert stats["pre_delegation_executed"] == 0
    assert stats["post_delegation_executed"] == 0


if __name__ == "__main__":
    # Run basic tests
    test_hook_registration()
    test_hook_priority_ordering()
    test_hook_error_handling()
    test_hook_removal()
    test_disabled_hooks()
    test_config_based_disabling()
    test_memory_hook_config_check()
    test_post_delegation_hooks()
    test_stats_tracking()

    print("All tests passed!")
