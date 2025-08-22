# Implied PM Detection Feature

## Overview

The Implied PM Detection feature automatically identifies and visualizes "orphan" subagents - agents that were spawned without an explicit PM Task delegation. This helps users understand the complete agent hierarchy even when some agents are invoked directly or through system hooks without PM involvement.

## Problem Statement

In the Claude MPM system, subagents are typically spawned through PM Task delegations, creating a clear parent-child hierarchy. However, agents can also be spawned:

1. **Directly by users** - Tools that trigger subagents without PM involvement
2. **By system hooks** - Internal system processes that spawn agents
3. **Legacy events** - Historical data before PM tracking was implemented
4. **Error conditions** - Agents spawned when PM tracking fails

Without proper detection, these "orphan" agents appear disconnected in the hierarchy, making it difficult to understand the complete execution flow.

## Solution

### Detection Logic

The system identifies orphan subagents by:

1. **Tracking SubagentStart events** - Records all agent initialization events
2. **Checking for PM Task delegations** - Looks for corresponding Task tool calls within a time window
3. **Marking orphans** - Agents without Task delegations are marked as orphans
4. **Smart grouping** - Groups orphans by:
   - Time proximity (within 5 seconds)
   - Session correlation
   - Conversation context

### Visual Distinction

Implied PMs and their orphan agents are visually distinguished:

- **Icon**: 🔍 (magnifying glass) instead of 👔 (suit) for regular PMs
- **Border**: Dashed border style instead of solid
- **Background**: Subtle purple gradient (rgba(107, 70, 193, 0.08))
- **Text**: Italic font style for names
- **Status**: "inferred" status badge in purple
- **Tooltips**: Explanatory tooltips on hover

### Implementation Components

#### 1. Agent Inference Module (`agent-inference.js`)

Enhanced with orphan detection:

```javascript
// State tracking for orphans
state: {
    orphanSubagents: new Map(),      // Orphan events
    subagentStartEvents: new Map()   // All SubagentStart events
}

// Detection methods
identifyOrphanSubagents(events)      // Find orphans
groupOrphanSubagents(timeWindow)     // Group by proximity
isOrphanSubagent(eventIndex)         // Check if orphan
getOrphanGroups()                     // Get grouped orphans
```

#### 2. Agent Hierarchy Module (`agent-hierarchy.js`)

Creates implied PM nodes:

```javascript
// Multiple implied PM groups instead of single node
const impliedPMGroups = new Map();

// Create implied PM for each orphan group
for (const [groupingKey, orphans] of orphanGroups) {
    const impliedPM = {
        type: 'pm',
        name: `PM (Implied #${counter})`,
        isImplied: true,
        status: 'inferred',
        tooltip: 'Inferred PM - Subagents started without explicit PM delegation'
    };
    // Add orphan agents as children
}
```

#### 3. CSS Styling (`dashboard.css`)

Visual differentiation:

```css
/* Implied PM styling */
.agent-node-implied .agent-node-header {
    border-left-style: dashed !important;
    opacity: 0.9;
    background: linear-gradient(135deg, rgba(107, 70, 193, 0.05) 0%, rgba(107, 70, 193, 0.1) 100%);
}

.agent-status-inferred .agent-status {
    background: #f0e5ff;
    color: #6b46c1;
    font-style: italic;
}
```

## Usage Examples

### Scenario 1: Direct Tool Invocation

When a user directly calls a tool that spawns a subagent:

```javascript
// User calls tool directly (no PM involved)
WebSearch({ query: "latest AI news" })
// This triggers a Research Agent internally

// Detection: SubagentStart without preceding Task
// Result: Creates "PM (Implied #1)" → "Research Agent"
```

### Scenario 2: System Hook Spawning

When system hooks automatically spawn agents:

```javascript
// System detects security issue and spawns agent
systemHook.onSecurityAlert(() => {
    spawnAgent("security", { check: "vulnerability scan" })
})

// Detection: SubagentStart without Task delegation
// Result: Creates "PM (Implied #2)" → "Security Agent"
```

### Scenario 3: Grouped Orphans

Multiple orphans spawned close together:

```javascript
// Multiple agents spawned within 5 seconds
spawnAgent("qa", { test: "unit tests" })      // t=0
spawnAgent("documentation", { update: true })  // t=3s

// Detection: Both orphans within time window
// Result: Single "PM (Implied #3)" with both agents as children
```

## Testing

### Test Data Generation

Run the test script to generate sample events:

```bash
python scripts/test_implied_pm_detection.py
```

This creates `test_implied_pm_events.json` with various scenarios.

### Unit Tests

Run unit tests for the detection logic:

```bash
pytest tests/test_implied_pm_detection.py -v
```

### Manual Testing

1. Start the dashboard: `claude-mpm dashboard`
2. Load test data: Click "Load File" → select `test_implied_pm_events.json`
3. Navigate to "Agents" tab
4. Verify implied PM nodes appear with:
   - Dashed borders
   - 🔍 icon
   - "inferred" status
   - Proper grouping

## Benefits

1. **Complete Visibility** - All agents are shown, even without PM delegation
2. **Clear Distinction** - Visual cues identify inferred vs explicit hierarchy
3. **Smart Grouping** - Related orphans are grouped intelligently
4. **Better Debugging** - Easier to identify agent spawning patterns
5. **Historical Support** - Works with legacy event formats

## Future Enhancements

Potential improvements:

1. **Confidence Scoring** - Show confidence level for inferred relationships
2. **Pattern Learning** - Learn common orphan patterns over time
3. **Custom Grouping Rules** - User-configurable grouping parameters
4. **Export Support** - Include implied PMs in hierarchy exports
5. **Filtering Options** - Show/hide implied PMs toggle

## Configuration

Currently, the feature uses these defaults:

- **Time Window**: 5 seconds for grouping orphans
- **Look-back Range**: 20 events for Task delegation search
- **Auto-expand**: Implied PM nodes expanded by default

These could be made configurable in future versions.