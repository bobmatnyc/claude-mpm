# Agent Deployment Error Display Implementation

## Summary

Enhanced error reporting in startup.py to display agent deployment errors to users, not just in logs.

## Problem Statement

When agent deployment failed during startup, errors were logged but never shown to the user. The progress bar would show "Complete: 0 agents ready (all up-to-date)" even when all agents failed to deploy, giving users no indication that something went wrong.

## Solution

Modified `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/startup.py` to check for deployment errors and display them to users with clear, actionable formatting.

## Changes Made

### 1. Enhanced Error Display in startup.py (Lines 357-384)

Added error checking after agent deployment completes:

```python
# Display deployment errors to user (not just logs)
deploy_errors = deployment_result.get("errors", [])
if deploy_errors:
    # Log for debugging
    logger.warning(
        f"Agent deployment completed with {len(deploy_errors)} errors: {deploy_errors}"
    )

    # Display errors to user with clear formatting
    print("\n⚠️  Agent Deployment Errors:")

    # Show first 10 errors to avoid overwhelming output
    max_errors_to_show = 10
    errors_to_display = deploy_errors[:max_errors_to_show]

    for error in errors_to_display:
        # Format error message for readability
        print(f"   - {error}")

    # If more errors exist, show count
    if len(deploy_errors) > max_errors_to_show:
        remaining = len(deploy_errors) - max_errors_to_show
        print(f"   ... and {remaining} more error(s)")

    # Show summary message
    print(f"\n❌ Failed to deploy {len(deploy_errors)} agent(s). Please check the error messages above.")
    print("   Run with --verbose for detailed error information.\n")
```

### 2. Added Comprehensive Tests

Added three new tests to `/Users/masa/Projects/claude-mpm/tests/cli/test_agent_startup_deployment.py`:

1. **test_sync_remote_agents_displays_deployment_errors_to_user**
   - Verifies errors are displayed when deployment fails
   - Checks for error header, specific error messages, and summary
   - Ensures users see actionable error information

2. **test_sync_remote_agents_no_error_display_when_successful**
   - Verifies no error messages shown when deployment succeeds
   - Prevents false alarms in successful deployments

3. **Fixed Existing Tests**
   - Changed `.json` files to `.md` files in test fixtures
   - Aligns with actual code behavior (counts .md files, not .json)

## Features

### User-Friendly Error Messages

- **Clear Header**: "⚠️  Agent Deployment Errors:"
- **Specific Errors**: Lists each failed agent with error reason
- **Error Limit**: Shows first 10 errors, counts remaining
- **Summary**: Clear count of failed deployments
- **Actionable Guidance**: Suggests running with --verbose

### Example Output

```
Deploying agents [████████████████████] 100% (39/39) Complete: 0 agents ready

⚠️  Agent Deployment Errors:
   - engineer.md: Failed to parse template: JSONDecodeError
   - qa.md: Failed to parse template: JSONDecodeError
   - research.md: Failed to parse template: Invalid frontmatter
   ... and 36 more error(s)

❌ Failed to deploy 39 agent(s). Please check the error messages above.
   Run with --verbose for detailed error information.
```

## Testing

All tests pass:
```bash
python -m pytest tests/cli/test_agent_startup_deployment.py -xvs
# 6 passed in 0.33s
```

## Benefits

1. **Immediate Visibility**: Users see errors right away, not buried in logs
2. **Clear Distinction**: Easy to tell successful from failed deployments
3. **Actionable Messages**: Users know what went wrong and what to do
4. **Non-Breaking**: Doesn't affect functionality when no errors occur
5. **Professional UX**: Clean formatting with emojis for visual distinction

## Backward Compatibility

- ✅ Existing functionality unchanged when no errors
- ✅ Progress bar still shows completion status
- ✅ Logging still happens for debugging
- ✅ Non-blocking - startup continues even with errors

## Success Criteria

- [x] Users see deployment errors immediately
- [x] Clear distinction between successful and failed deployments
- [x] Actionable error messages (tell user what went wrong)
- [x] Doesn't break existing functionality when no errors occur
- [x] Tests verify error display behavior
- [x] Tests verify no false alarms on success

## Related Issues

This fix is part of the v5.0 agent deployment issue resolution. The Markdown parser has been implemented, and this enhancement ensures any future deployment errors are visible to users.
