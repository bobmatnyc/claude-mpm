# Ticket CLI Known Issues and Limitations

> **⚠️ OUTDATED DOCUMENT WARNING** 
> 
> This document references the old `claude-mpm tickets` command system which has been replaced with direct `aitrackdown` usage. The issues described below may no longer be relevant.
>
> **For current ticket management:** Use `aitrackdown` commands directly as documented in [Ticket CLI Reference](ticket-cli-reference.md).
>
> This document is kept for historical reference and will be updated in a future release.

---

This document outlines known issues, limitations, and workarounds for the **legacy** claude-mpm ticket CLI system based on QA testing and user feedback.

## Status Alignment Issues

### Issue: Status Filtering Inconsistency

**Problem:**
Status values are inconsistent between the TicketManager interface and aitrackdown CLI, causing filtering and display issues.

**Symptoms:**
- `claude-mpm tickets list --status done` may not show all completed tickets
- Some tickets show `completed` status while others show `done`
- Status filtering may miss tickets due to terminology mismatch

**Affected Commands:**
- `list --status` filter
- `search --status` filter  
- `workflow` state transitions

**Current Workaround:**
```bash
# Use both status values when searching
claude-mpm tickets search "your-query" --status done
claude-mpm tickets search "your-query" --status completed

# Or use aitrackdown directly for comprehensive results
aitrackdown task list --status done,completed
```

**Resolution Timeline:** Planned for v3.8.0 - standardize status terminology across all interfaces

### Issue: Workflow State Mapping Confusion

**Problem:**
The workflow command uses different state names than standard status values, causing user confusion.

**Current Mapping:**
- `todo` → `open` status
- `in_progress` → `in_progress` status
- `ready` → `ready` status  
- `tested` → `tested` status
- `done` → `done` status
- `blocked` → `blocked` status

**Confusion Points:**
- Users expect `todo` status but see `open` in list commands
- `ready` and `tested` statuses not widely supported in list filtering
- Workflow states don't align with aitrackdown native states

**Workaround:**
```bash
# Use standard status values for consistency
claude-mpm tickets update TSK-0123 --status in_progress
# Instead of: claude-mpm tickets workflow TSK-0123 in_progress
```

## Update Command Limitations

### Issue: Complex Updates Require aitrackdown Fallback

**Problem:**
The TicketManager interface doesn't support all update operations, causing inconsistent user experience when updates fall back to aitrackdown CLI.

**Limited Operations:**
- Bulk updates across multiple tickets
- Advanced assignment management (multiple assignees)
- Custom field updates
- Relationship modifications (parent changes)
- Tag removal (can only replace, not remove specific tags)

**Fallback Behavior:**
Some update operations automatically fall back to `aitrackdown` commands, which may:
- Have different output formats
- Require additional authentication
- Use different parameter formats
- Not support all CLI options

**Workaround:**
```bash
# For complex updates, use aitrackdown directly
aitrackdown task update TSK-0123 \
  --assignee "user1@company.com,user2@company.com" \
  --custom-field priority=critical \
  --add-tags "urgent,customer-facing" \
  --remove-tags "low-priority"
```

### Issue: Parent Relationship Updates Not Supported

**Problem:**
Cannot change parent relationships after ticket creation through the CLI.

**Symptoms:**
- `--parent-issue` and `--parent-epic` only work during creation
- `update` command doesn't accept parent modification options
- Orphaned tickets cannot be re-linked to parents

**Workaround:**
```bash
# Use aitrackdown for relationship changes
aitrackdown task update TSK-0123 --parent ISS-0067
aitrackdown issue link ISS-0067 --epic EP-0012
```

## Type Filtering Behavior

### Issue: Type Filter Case Sensitivity

**Problem:**
Type filtering is case-sensitive and doesn't handle common variations.

**Symptoms:**
- `--type Bug` doesn't match tickets created with `--type bug`
- Mixed case types from different sources cause filtering issues
- Type validation during creation doesn't normalize case

**Affected Commands:**
- `list --type`
- `search --type`

**Workaround:**
```bash
# Always use lowercase type names
claude-mpm tickets list --type bug  # not --type Bug or --type BUG
```

### Issue: Limited Type Options

**Problem:**
The CLI type options don't cover all aitrackdown ticket types.

**Supported Types:**
- `task`, `bug`, `feature`, `issue`, `epic`

**Missing Types:**
- `enhancement`, `story`, `spike`, `chore`
- Custom types defined in aitrackdown configuration
- Legacy type names from imported tickets

**Workaround:**
```bash
# Create with supported type, then update via aitrackdown
claude-mpm tickets create "title" --type feature
aitrackdown issue update ISS-0123 --type enhancement
```

## Comment Functionality Status

### Issue: Limited Comment Features

**Problem:**
The comment command is a thin wrapper around aitrackdown and lacks CLI-specific features.

**Limitations:**
- Cannot edit or delete comments through CLI
- No support for comment threading or replies
- Cannot attach files or images
- No markdown preview or formatting validation
- Cannot list comments for a ticket

**Missing Features:**
```bash
# These operations are not supported:
claude-mpm tickets comment TSK-0123 --edit  # Not implemented
claude-mpm tickets comment TSK-0123 --list  # Not implemented
claude-mpm tickets comment TSK-0123 --delete # Not implemented
```

**Workaround:**
```bash
# Use aitrackdown for advanced comment operations
aitrackdown comment list TSK-0123
aitrackdown comment edit TSK-0123 --comment-id 5
aitrackdown comment delete TSK-0123 --comment-id 5
```

### Issue: Comment Content Limitations

**Problem:**
Command-line comment input has practical limitations for complex content.

**Limitations:**
- Difficult to enter multi-line comments
- No markdown preview before submission
- Limited formatting options
- Cannot include code blocks or tables easily

**Workaround:**
```bash
# Use temporary files for complex comments
echo "
## Progress Update

**Completed:**
- Feature implementation
- Unit tests

**Next Steps:**
- Integration testing
- Documentation update
" > comment.txt

aitrackdown comment add TSK-0123 --from-file comment.txt
```

## Performance Issues

### Issue: Slow Search Performance

**Problem:**
Search operations can be slow with large ticket databases due to full-text scanning.

**Symptoms:**
- Search timeouts with large result sets
- Slow response times for complex queries
- Memory usage spikes during search operations

**Affected Operations:**
- `search` command with broad queries
- `list` with large limits (>100)
- Filtering operations on large datasets

**Mitigation:**
```bash
# Use specific queries and smaller limits
claude-mpm tickets search "specific-term" --limit 20
claude-mpm tickets list --type bug --status open --limit 10

# For extensive searches, use aitrackdown with pagination
aitrackdown search "query" --page-size 25 --page 1
```

### Issue: Memory Usage with Large Hierarchies

**Problem:**
Loading large epic hierarchies can consume significant memory and cause performance issues.

**Symptoms:**
- Slow `view` command for large epics
- CLI hanging when displaying complex hierarchies
- Out of memory errors in extreme cases

**Workaround:**
```bash
# View specific levels instead of full hierarchy
claude-mpm tickets view EP-0012  # Shows epic details only
aitrackdown epic show EP-0012 --shallow  # Limits depth
```

## Integration Issues

### Issue: ai-trackdown-pytools Dependency

**Problem:**
The CLI requires ai-trackdown-pytools but installation and version compatibility can cause issues.

**Common Problems:**
- Package not installed or wrong version
- Virtual environment issues
- Conflicting dependencies
- PATH issues with aitrackdown command

**Diagnostic Commands:**
```bash
# Check installation
python -c "import aitrackdown; print(aitrackdown.__version__)"

# Verify CLI availability  
which aitrackdown

# Test basic functionality
aitrackdown --version
```

**Resolution:**
```bash
# Reinstall with correct version
pip uninstall ai-trackdown-pytools
pip install ai-trackdown-pytools>=0.9.0

# Ensure PATH is correct
echo $PATH | grep -o '[^:]*bin[^:]*'
```

### Issue: Configuration Synchronization

**Problem:**
CLI and aitrackdown may use different configuration sources, causing inconsistent behavior.

**Symptoms:**
- Tickets created in wrong directories
- ID format mismatches
- Different default priorities or statuses

**Resolution:**
```bash
# Verify configuration alignment
claude-mpm config view
aitrackdown config show

# Use same configuration directory
export AITRACKDOWN_CONFIG_DIR=.ai-trackdown
```

## Error Handling Issues

### Issue: Inconsistent Error Messages

**Problem:**
Error messages vary in format and helpfulness depending on whether operations use TicketManager or aitrackdown fallback.

**Examples:**
```bash
# TicketManager error (concise)
❌ Ticket TSK-9999 not found

# aitrackdown fallback error (verbose)
Error: Command failed with exit code 1
stderr: aitrackdown: error: ticket 'TSK-9999' not found in database
```

**Impact:**
- Users can't predict error message format
- Some errors lack actionable guidance
- Debugging information varies by operation

### Issue: Limited Error Recovery

**Problem:**
When operations fail, there's limited guidance on alternative approaches or recovery steps.

**Missing Recovery Options:**
- No retry mechanisms for transient failures
- No suggestions for alternative commands
- Limited context about what caused failures

**Workaround:**
```bash
# Manual retry with verbose output
claude-mpm tickets create "title" --verbose
# If that fails, try aitrackdown directly:
aitrackdown task create "title" --debug
```

## Documentation Gaps

### Issue: Incomplete Parameter Documentation

**Problem:**
Some command parameters lack complete documentation or examples.

**Under-documented Areas:**
- Tag formatting and conventions
- Parent relationship syntax
- Priority level impact on workflow
- Status transition rules and validation

### Issue: Integration Examples Missing

**Problem:**
Limited examples for integration with common development workflows.

**Missing Integration Guides:**
- Git hook integration patterns
- CI/CD pipeline integration
- IDE plugin compatibility
- Slack/Teams notification setup

## Planned Improvements

### Short Term (v3.8.0)
- [ ] Standardize status terminology across all interfaces
- [ ] Improve error message consistency and helpfulness
- [ ] Add comprehensive parameter validation
- [ ] Enhance search performance with indexing

### Medium Term (v3.9.0)
- [ ] Support for all aitrackdown ticket types
- [ ] Advanced comment management features
- [ ] Bulk operation support in CLI
- [ ] Parent relationship modification support

### Long Term (v4.0.0)
- [ ] Native ticket storage (reduce aitrackdown dependency)
- [ ] Real-time collaboration features
- [ ] Advanced reporting and analytics
- [ ] Plugin architecture for custom integrations

## Reporting New Issues

If you encounter issues not listed here, please report them with:

1. **Full command and output:**
   ```bash
   claude-mpm tickets create "test" --debug 2>&1 | tee error.log
   ```

2. **Environment information:**
   ```bash
   claude-mpm info
   pip list | grep -E "(claude-mpm|ai-trackdown)"
   ```

3. **Configuration details:**
   ```bash
   claude-mpm config view --sanitized
   ```

Submit reports to the [claude-mpm issues tracker](https://github.com/claude-mpm/claude-mpm/issues) with the `ticket-cli` label.

## See Also

- [Ticket CLI Reference](ticket-cli-reference.md) - Complete command documentation
- [Ticket Workflow Best Practices](ticket-workflow-best-practices.md) - Effective usage patterns
- [Troubleshooting Guide](../troubleshooting.md) - General troubleshooting procedures