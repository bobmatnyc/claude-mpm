# Pending Tasks

## 1. Test Tavily Agent
- Agent created at: `.claude/agents/tavily-agent.md`
- API Key configured: `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`
- TODO: Run sample web scraping task to verify functionality

## 2. Token Tracking Investigation
- **Issue**: Dashboard shows zeros for all token metrics
- **Root Cause**: Claude Code stop hooks don't include `usage` field
- **Status**: Research completed, verification script created
- **Script**: `verify_assistant_response_usage.py`
- **Report**: `docs/research/token-usage-source-investigation-2026-02-07.md`
- **TODO**: Run verification script to test alternative hook types (AssistantResponse)

## 3. Dashboard Token Tracking Timeline
- Fixed event categorization (session_event)
- Fixed dashboard listeners (socket.svelte.ts)
- Rebuilt and reinstalled multiple times
- Server confirmed broadcasting events correctly
- **Blocker**: Events not emitted because stop hooks lack usage field
- **Next**: Verify if other hook types provide usage data

---
*Saved: 2026-02-08 02:00 EST*
