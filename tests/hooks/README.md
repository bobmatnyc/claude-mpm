# Hook System Tests

This directory contains tests for the Claude MPM hook system, with a focus on maintaining the single-path event emission architecture.

## Test Files

### `test_single_path_emission.py`

This file contains two main test classes:

#### `TestSinglePathEmission`
Tests the functional behavior of the connection manager:
- Single emission path success
- HTTP fallback on direct failure
- Event normalization
- No duplicate emissions
- Architecture compliance

#### `TestArchitectureCompliance`
**Critical architecture compliance tests** that prevent regression to duplicate emission patterns:

- **`test_no_eventbus_in_active_hook_files`**: Ensures active hook files contain no EventBus references
- **`test_connection_manager_single_emission_path`**: Verifies single-path pattern implementation
- **`test_required_architecture_files_exist`**: Checks for required documentation files
- **`test_architecture_documentation_references`**: Ensures proper documentation references
- **`test_no_multiple_parallel_emissions`**: Prevents multiple parallel emission paths

## Architecture Compliance

These tests serve as **automated architecture compliance checks** that:

1. **Prevent EventBus regression**: Detect if EventBus references are accidentally re-introduced
2. **Enforce single-path pattern**: Ensure only one primary + one fallback emission path
3. **Validate documentation**: Confirm architecture documentation is maintained
4. **Detect duplicate patterns**: Catch multiple parallel emission implementations

## Running Tests

```bash
# Run all hook tests
cd src && python -m pytest ../tests/hooks/ -v

# Run only architecture compliance tests
cd src && python -m pytest ../tests/hooks/test_single_path_emission.py::TestArchitectureCompliance -v

# Run specific compliance test
cd src && python -m pytest ../tests/hooks/test_single_path_emission.py::TestArchitectureCompliance::test_no_eventbus_in_active_hook_files -v
```

## Test Philosophy

These tests follow the principle that **architecture should be enforced by tests**, not just documentation. By running these tests in CI/CD, we ensure:

- No accidental reintroduction of duplicate emission patterns
- Consistent architecture across development team
- Early detection of architecture violations
- Automated compliance checking

## Maintenance

When modifying the hook system:

1. **Run these tests first** to understand current architecture
2. **Update tests** if architecture changes are intentional
3. **Never disable** architecture compliance tests without team review
4. **Add new tests** for new architecture patterns

## Related Documentation

- [Event Emission Architecture](../../docs/developer/EVENT_EMISSION_ARCHITECTURE.md)
- [Architecture Overview](../../docs/developer/ARCHITECTURE.md)
- [Hook System Documentation](../../src/claude_mpm/hooks/README.md)
