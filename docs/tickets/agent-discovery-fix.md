# Fix Agent Discovery: Sync All Agents from Git Source

## Problem
Currently, only 10 agents are synced from the git repository even though 48 agents are available. The `_get_agent_list()` method in `git_source_sync_service.py` has a hardcoded list.

## Current Behavior
- Hardcoded list of 10 agents (lines 626-637 in git_source_sync_service.py)
- Ignores 38 other agents in the repository
- No user control over which agents to install

## Expected Behavior
- **Sync ALL agents** from git source (auto-discovery)
- **User manifest** determines which agents to deploy
- Progress bar shows actual count of all available agents

## Technical Details

### Current Implementation (Wrong)
```python
def _get_agent_list(self) -> List[str]:
    # Hardcoded list - only 10 agents
    return [
        "research.md",
        "engineer.md",
        # ... only 10 total
    ]
```

### Proposed Solution
1. **Auto-discovery**: Use GitHub API to list all .md files in agents/ directory
2. **Sync all agents**: Download all discovered agent files to cache
3. **User manifest**: Add agent_manifest.yaml to control which agents to deploy
4. **Filter on deploy**: Only deploy agents enabled in manifest

### Architecture

```
Git Source (48 agents)
    ↓ (sync ALL)
Local Cache (~/.claude-mpm/cache/remote-agents/)
    ↓ (filter by manifest)
Deployed Agents (~/.claude/agents/)
```

### Implementation Steps

1. **Replace hardcoded list with GitHub API call**
   - File: `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
   - Method: `_get_agent_list()`
   - Use: `GET /repos/{owner}/{repo}/contents/{path}`

2. **Create agent manifest schema**
   - File: `~/.claude-mpm/config/agent_manifest.yaml`
   - Format:
     ```yaml
     agents:
       - name: research
         enabled: true
       - name: engineer
         enabled: true
       - name: python_engineer
         enabled: false  # User choice
     ```

3. **Update deployment to filter by manifest**
   - File: `src/claude_mpm/services/agents/deployment/`
   - Only deploy agents with `enabled: true`

4. **Update progress bar to show all agents**
   - Current: "10/10 (100%)"
   - New: "48/48 (100%)" during sync
   - Deployment: "12/48 (25%)" if only 12 enabled

### Files to Modify

- `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
  - `_get_agent_list()` method
- `src/claude_mpm/config/agent_sources.py`
  - Add manifest support
- `src/claude_mpm/services/agents/deployment/`
  - Add manifest filtering

### Testing

- Verify all 48 agents sync from bobmatnyc/claude-mpm-agents
- Test manifest enable/disable functionality
- Verify progress bar shows correct counts
- Test with custom git sources

## Acceptance Criteria

- [ ] Sync discovers all agents automatically (no hardcoded list)
- [ ] Progress bar shows actual count (48/48 for default repo)
- [ ] User manifest controls which agents deploy
- [ ] `claude-mpm agents list` shows all available vs deployed
- [ ] Documentation updated for manifest configuration

## Priority
Medium - Affects discoverability and user control of agents

## Labels
enhancement, agent-management, git-sources
