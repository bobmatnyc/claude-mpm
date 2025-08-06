# Dashboard Enhancements Guide

## Overview

Claude MPM's dashboard has been significantly enhanced to provide better insights into your multi-agent workflows. This guide covers the key features introduced in version 3.4.0: agent consolidation, enhanced prompt analysis, and integrated git diff viewing.

## Agent Consolidation

### What It Is

The agent consolidation feature groups all activities from the same type of agent into unified entries, giving you a cleaner view of your agent usage patterns.

### Benefits

- **Cleaner Interface**: Instead of seeing 10 separate entries for "DocumentationAgent", you see one consolidated entry
- **Better Analytics**: Quickly see which agents you use most frequently
- **Aggregated Metrics**: Total delegation counts, combined event counts, and time ranges at a glance
- **Detailed History**: Still access individual delegation details when needed

### How to Use

1. **Navigate to the Agents Tab**: Click the "Agents" tab in the dashboard
2. **View Consolidated Entries**: Each unique agent type appears as a single row showing:
   - Agent name (e.g., "DocumentationAgent", "CodeReviewAgent")
   - Number of times delegated
   - Total events generated
   - Time range from first to last use

3. **Access Details**: Click any consolidated agent to see:
   - Individual delegation sessions
   - Specific prompts used
   - Event timelines
   - Performance metrics

### Example

Instead of seeing:
```
DocumentationAgent (Session 1) - 15 events
DocumentationAgent (Session 2) - 8 events  
DocumentationAgent (Session 3) - 22 events
```

You now see:
```
📄 DocumentationAgent
   └── 3 delegations, 45 total events
   └── Used from 09:15 AM to 02:30 PM
```

## Enhanced Prompt Viewer

### What It Is

The enhanced prompt viewer provides intelligent analysis of your prompts and agent instructions, including token counting, text metrics, and improved formatting.

### Key Features

#### Token Counting
- **Automatic Estimation**: Get approximate token counts for all prompts
- **Context Planning**: Understand how much of your LLM context window is being used
- **Cost Estimation**: Better predict API costs based on token usage

#### Text Metrics
- **Character Count**: Total characters including spaces
- **Word Count**: Number of words for readability analysis
- **Line Count**: Number of lines for formatting reference

#### Smart Formatting
- **Whitespace Cleanup**: Removes excessive spaces and normalizes formatting
- **HTML Safety**: Automatically escapes potentially dangerous content
- **Truncation**: Long prompts are smartly truncated with expansion options

### How to Use

1. **Select Any Event**: Click on any event in the Events tab
2. **View Enhanced Prompts**: In the detail panel, look for prompt sections that now show:
   ```
   📝 User Prompt (estimated 45 tokens, 180 chars, 32 words)
   ┌─────────────────────────────────────┐
   │ Please create comprehensive docs... │
   │ [Click to expand full prompt]       │
   └─────────────────────────────────────┘
   ```
3. **Analyze Metrics**: Use the metrics to:
   - Plan context usage across multiple agent calls
   - Optimize prompt length for efficiency
   - Track prompt complexity over time

### Practical Applications

#### Context Window Management
```
Total Context: 4,096 tokens
Current prompt: 350 tokens
Agent response: ~800 tokens  
Memory context: 200 tokens
Remaining: ~2,746 tokens ✅
```

#### Prompt Optimization
- **Too Long**: Prompts over 500 tokens may need simplification
- **Just Right**: 100-300 tokens often work well for most tasks
- **Too Short**: Very brief prompts may lack necessary context

## Git Diff Viewer

### What It Is

An integrated git diff viewer that shows file changes directly in the dashboard without switching to external tools.

### Benefits

- **Workflow Integration**: See changes in context of your file operations
- **Visual Clarity**: Syntax-highlighted diffs with color coding
- **No Tool Switching**: Everything in one interface
- **Copy Functionality**: Easy copying of diff content

### How to Use

#### Accessing Diffs

1. **Go to Files Tab**: Navigate to the Files tab in the dashboard
2. **Look for Diff Icons**: Files with git changes show a 📋 icon
3. **Click to View**: Click the diff icon to open the diff viewer

#### Understanding the Display

The diff viewer shows:

- **File Header**: File path and timestamp
- **Diff Metadata**: Commit hash and diff method used
- **Color-Coded Changes**:
  - 🟢 **Green lines**: Additions (lines starting with +)
  - 🔴 **Red lines**: Deletions (lines starting with -)
  - 🔵 **Blue headers**: Context information (@@...@@)
  - ⚪ **White lines**: Unchanged context

#### Example Diff

```diff
📋 Git Diff: src/example.js

commit: abc1234
method: git diff HEAD~1

@@ -10,7 +10,8 @@ function processData(input) {
     return null;
   }
 
-  const result = input.map(item => item.value);
+  const result = input.map(item => item.value || 0);
+  console.log('Processing:', result.length, 'items');
   
   return result.filter(value => value > 0);
 }
```

### File Status Indicators

- **📋 Tracked & Modified**: File is in git and has changes
- **📝 Untracked**: File exists but isn't in git yet
- **❌ No Changes**: File is tracked but unchanged
- **⚠️ Error**: Can't access git information

### Advanced Features

#### Keyboard Navigation
- **Escape**: Close diff viewer
- **Ctrl+C**: Copy diff content (when focused)

#### Error Handling
The system gracefully handles:
- Files not in git repositories
- Network connectivity issues
- Permission problems
- Large diff files

## Practical Workflows

### Agent Performance Analysis

1. **Check Agent Usage**: Use the Agents tab to see which agents you use most
2. **Analyze Patterns**: Look for agents with high delegation counts
3. **Optimize Workflows**: Consider consolidating similar agent roles

### Prompt Engineering

1. **Monitor Token Usage**: Track prompt lengths across different tasks
2. **Test Variations**: Compare token counts for different prompt styles
3. **Context Planning**: Ensure total context fits within model limits

### Code Review Integration

1. **Make Changes**: Edit files through claude-mpm agents
2. **Review Diffs**: Use the integrated diff viewer to see changes
3. **Iterate**: Make adjustments based on diff analysis
4. **Commit**: Standard git workflow after review

### Development Workflow Example

```
1. Agent creates documentation
   └── View in Files tab
   └── Click diff icon to see changes
   └── Review additions/modifications
   
2. Agent refactors code  
   └── Check prompt token count
   └── Analyze agent consolidation stats
   └── Review file diffs
   
3. Final review
   └── Export consolidated agent report
   └── Verify all changes via diffs
   └── Commit to version control
```

## Tips and Best Practices

### Agent Consolidation

- **Review Regularly**: Check agent usage patterns weekly
- **Optimize Delegation**: Reduce redundant agent calls
- **Track Performance**: Monitor event counts for efficiency

### Prompt Analysis

- **Target Token Range**: Aim for 100-300 tokens for most prompts
- **Monitor Complexity**: Track word-to-token ratios
- **Context Budget**: Reserve 20-30% context for agent responses

### Git Integration

- **Small Commits**: Review changes frequently with diff viewer
- **Clear History**: Use diffs to ensure clean commit messages
- **Collaboration**: Share diff links with team members

## Troubleshooting

### Agent Consolidation Issues

**Problem**: Agents not consolidating properly
- **Check**: Ensure agents have consistent names
- **Verify**: Socket.IO connection is active
- **Solution**: Refresh dashboard or restart monitoring

**Problem**: Missing agent statistics
- **Check**: Events contain agent metadata
- **Verify**: Agent inference is working (check console)
- **Solution**: Update claude-mpm to latest version

### Prompt Viewer Issues

**Problem**: Token counts seem wrong
- **Note**: Counts are estimates, not exact
- **Check**: Very short or very long prompts may be less accurate
- **Solution**: Use for relative comparison, not absolute values

**Problem**: Text not displaying properly
- **Check**: Browser console for JavaScript errors
- **Verify**: Content contains valid text
- **Solution**: Refresh page or clear browser cache

### Diff Viewer Issues

**Problem**: Diff not loading
- **Check**: File is in a git repository
- **Verify**: Monitoring server is running (port 8765)
- **Solution**: Ensure file has been committed at least once

**Problem**: No diff icon appearing
- **Check**: File has actual changes
- **Verify**: Git repository is properly initialized
- **Solution**: Make changes to file and refresh dashboard

### General Issues

**Problem**: Features not working
1. **Refresh Dashboard**: Try reloading the page
2. **Check Connection**: Verify socket connection status
3. **Update Version**: Ensure you're running claude-mpm 3.4.0+
4. **Check Console**: Look for JavaScript errors in browser console

## Getting Help

If you encounter issues with the dashboard enhancements:

1. **Check Documentation**: Refer to the technical documentation in `docs/developer/dashboard/`
2. **Enable Debug Mode**: Set `localStorage.setItem('dashboard-debug', 'true')` in browser console
3. **Check Server Logs**: Review claude-mpm monitoring server logs
4. **Report Issues**: Create an issue with specific error details and reproduction steps

## What's Next

The dashboard enhancements provide a solid foundation for monitoring and optimizing your multi-agent workflows. Future releases will include:

- Advanced agent performance metrics
- Enhanced diff visualization
- Export capabilities for reports
- Integration with external tools

These features help you work more efficiently with claude-mpm's multi-agent system while maintaining visibility into all operations.