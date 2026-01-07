# Comprehensive Tests for Agents Command

## Overview

The comprehensive test suite in `test_agents_comprehensive.py` provides extensive coverage for the agents command module, serving as a safety net during refactoring. This test suite ensures that all functionality is preserved when we refactor the agents command to follow SOLID principles and reduce code duplication.

## Test Coverage

### 1. Listing Operations (`TestListingOperations`)
- **System agents**: Lists available agent templates from the framework
- **Deployed agents**: Lists agents currently deployed in the project
- **By tier**: Groups agents by precedence (project > user > system)
- **Output formats**: Tests JSON, YAML, and text output formats
- **Warnings**: Handles and displays warnings from deployment verification

### 2. Deployment Operations (`TestDeploymentOperations`)
- **Standard deployment**: Deploys both system and project agents
- **Force deployment**: Forces rebuild of all agents even if up-to-date
- **No changes scenario**: Handles case when all agents are already deployed
- **Error handling**: Tests deployment failures and error reporting
- **JSON output**: Structured output for programmatic consumption

### 3. Cleanup Operations (`TestCleanupOperations`)
- **Clean deployed agents**: Removes all deployed agents
- **Clean orphaned agents**: Removes agents without corresponding templates
- **Dry-run mode**: Preview cleanup without making changes
- **Force mode**: Actually performs cleanup operations
- **Error handling**: Tests cleanup failures and partial success

### 4. Viewing Operations (`TestViewingOperations`)
- **View agent details**: Displays full information about a specific agent
- **Missing agent name**: Handles missing required parameters
- **Non-existent agent**: Error handling for invalid agent names
- **JSON format**: Structured output of agent details

### 5. Fix Operations (`TestFixOperations`)
- **Fix deployment issues**: Corrects common deployment problems
- **Fix frontmatter**: Validates and corrects agent metadata
- **No issues scenario**: Handles case when no fixes are needed
- **JSON output**: Reports fixes applied in structured format

### 6. Dependency Operations (`TestDependencyOperations`)
- **Check dependencies**: Identifies missing agent dependencies
- **Install dependencies**: Installs missing Python packages
- **List dependencies**: Shows all agent dependencies
- **Fix dependencies**: Robust installation with retry logic
- **All satisfied**: Handles case when all dependencies are met

### 7. Error Handling (`TestErrorHandling`)
- **Import errors**: Handles missing service dependencies
- **Unknown commands**: Graceful handling of invalid subcommands
- **General exceptions**: Catches and reports unexpected errors
- **Service unavailable**: Handles deployment service failures

### 8. Default Behavior (`TestDefaultBehavior`)
- **Show versions**: Default action displays agent versions
- **No agents deployed**: Helpful message when no agents found
- **JSON format**: Structured output of version information

### 9. Entry Point (`TestManageAgentsFunction`)
- **Success execution**: Tests main entry point function
- **JSON output**: Tests structured output handling
- **Failure handling**: Tests error propagation and exit codes

### 10. Lazy Loading (`TestLazyLoading`)
- **Service initialization**: Tests lazy loading of deployment service
- **Service caching**: Ensures service is only created once

### 11. Output Formats (`TestOutputFormats`)
- **Multiple formats**: Tests JSON, YAML, and text outputs
- **Consistent structure**: Ensures data structure across formats

### 12. Edge Cases (`TestEdgeCases`)
- **Empty lists**: Handles empty agent lists gracefully
- **Missing directories**: Handles non-existent agent directories
- **Special characters**: Tests agent names with special characters
- **Partial failures**: Handles mixed success/failure scenarios

### 13. Backward Compatibility (`TestCompatibility`)
- **Legacy functions**: Tests old function signatures still work
- **Migration path**: Ensures smooth transition to new architecture

### 14. Integration Scenarios (`TestIntegrationScenarios`)
- **Deploy-then-list workflow**: Tests common user workflows
- **Dependency management workflow**: Complete check-install-verify cycle

## Mocking Strategy

The tests use extensive mocking to isolate the agents command from external dependencies:

1. **Deployment Service**: Mocked to avoid file system operations
2. **File System**: Mocked for path existence checks and file operations
3. **External Commands**: Mocked subprocess calls for dependency installation
4. **Network Operations**: Mocked for package index queries
5. **Configuration**: Mocked to provide consistent test environment

## Test Fixtures

### `mock_deployment_service`
Provides a fully mocked deployment service with all required methods and realistic return values.

### `command`
Creates an AgentsCommand instance with the mocked deployment service pre-configured.

### `mock_args`
Creates a mock arguments object with common attributes set to defaults.

## Usage During Refactoring

1. **Run before changes**: Ensure all tests pass before starting refactoring
2. **Run frequently**: Run tests after each significant change
3. **Watch for regressions**: Any failing test indicates broken functionality
4. **Update as needed**: Modify tests to match new architecture while preserving behavior

## Running the Tests

```bash
# Run all comprehensive tests
python -m pytest tests/cli/commands/test_agents_comprehensive.py -v

# Run specific test class
python -m pytest tests/cli/commands/test_agents_comprehensive.py::TestListingOperations -v

# Run with coverage
python -m pytest tests/cli/commands/test_agents_comprehensive.py --cov=claude_mpm.cli.commands.agents

# Run with minimal output
python -m pytest tests/cli/commands/test_agents_comprehensive.py -q
```

## Key Test Patterns

### Mocking Property Access
```python
with patch.object(type(command), 'deployment_service', new_callable=PropertyMock) as mock_prop:
    mock_prop.return_value = mock_service
```

### Testing Multiple Output Formats
```python
@pytest.mark.parametrize("format_type", ["json", "yaml", "text"])
def test_with_formats(self, command, format_type):
    # Test logic for each format
```

### Capturing Print Output
```python
with patch("builtins.print") as mock_print:
    result = command.run(args)
    mock_print.assert_any_call("Expected output")
```

### Testing Lazy Loading
```python
assert command._service is None  # Not loaded yet
service = command.service  # Trigger lazy load
assert command._service is not None  # Now loaded
```

## Success Metrics

- **45+ test methods** covering all command functionality
- **90%+ code coverage** of the agents command module
- **All edge cases** and error conditions tested
- **Multiple output formats** validated
- **Backward compatibility** maintained

These comprehensive tests provide confidence that refactoring can proceed safely without breaking existing functionality.