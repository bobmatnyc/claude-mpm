# Memory CLI Commands - Test Rewrite Required

**Status**: 🔴 Tests deleted and awaiting rewrite
**Date Deleted**: 2025-10-24
**Reason**: 88% failure rate due to architectural mismatch

## What Was Deleted

**File**: `tests/test_memory_cli_commands.py` (1,487 lines)
- 13 test classes
- 80 test functions
- All broken due to tests expecting different architecture

## Why Deleted

The tests were written for a **functional programming style** that doesn't exist:
- Tests imported standalone functions like `_show_memories()`, `_add_learning()`
- Actual code uses **OOP style** with `MemoryManagementCommand` class
- Architectural mismatch made 70/80 tests fail

**Analysis showed**: Rewriting from scratch (6-8 hours) is faster and better than fixing (7-10 hours).

## What Needs Testing

The Memory CLI commands require comprehensive test coverage:

### Core Commands (Priority 1)
1. **memory status** - Display memory statistics
2. **memory view** - View memory contents
3. **memory add** - Add new memory entries

### Secondary Commands (Priority 2)
4. **memory clean** - Clean up memory files
5. **memory build** - Build memory structures
6. **memory show** - Show specific memory

### Utility Commands (Priority 3)
7. **memory route** - Command routing
8. **Utility functions** - Helper functions

## Implementation Location

The actual code is in:
- **Main class**: `src/claude_mpm/cli/commands/memory.py::MemoryManagementCommand`
- **Architecture**: Object-oriented, class-based commands
- **Pattern**: Command pattern with `run()` method

## Rewrite Strategy

### Phase 1: Smoke Tests (2-3 hours)
Create basic tests for critical commands:
```python
# tests/cli/commands/test_memory_smoke.py
class TestMemoryCommands:
    def test_memory_status_runs(self):
        """Verify memory status command executes without error."""
        cmd = MemoryManagementCommand()
        result = cmd.run(['status'])
        assert result is not None

    def test_memory_view_runs(self):
        """Verify memory view command executes."""
        # Basic smoke test
        pass
```

### Phase 2: Integration Tests (2-3 hours)
Test command integration with fixtures:
```python
@pytest.fixture
def memory_command():
    return MemoryManagementCommand()

@pytest.fixture
def temp_memory_dir(tmp_path):
    memory_dir = tmp_path / ".claude-mpm" / "memories"
    memory_dir.mkdir(parents=True)
    return memory_dir

class TestMemoryIntegration:
    def test_memory_status_with_files(self, memory_command, temp_memory_dir):
        # Test with actual memory files
        pass
```

### Phase 3: Comprehensive Tests (2-3 hours)
Full coverage with edge cases:
- Error handling
- File operations
- CLI argument parsing
- Output formatting

## Estimated Effort

- **Phase 1 (Smoke)**: 2-3 hours
- **Phase 2 (Integration)**: 2-3 hours
- **Phase 3 (Comprehensive)**: 2-3 hours
- **Total**: 6-9 hours

## Success Criteria

✅ All memory CLI commands have test coverage
✅ Tests match actual OOP architecture
✅ 80%+ test coverage for memory commands
✅ All tests pass
✅ Tests use proper fixtures and mocks

## References

- **Analysis**: `/tmp/EXECUTIVE_SUMMARY.md`
- **Failure Examples**: `/tmp/memory_test_failure_examples.md`
- **Decision Summary**: `/tmp/memory_test_decision_summary.md`
