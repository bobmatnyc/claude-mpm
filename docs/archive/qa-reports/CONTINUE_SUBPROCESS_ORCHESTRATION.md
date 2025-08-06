# CONTINUATION TICKET: Subprocess Orchestration Investigation

**Created**: 2025-01-23
**Priority**: High
**Tags**: subprocess-orchestration, claude-cli, print-mode
**Type**: TODO

## Context
We discovered that Claude's --print mode has fundamental limitations:
- Works for simple queries (2+2) in ~4 seconds
- Times out for any code generation or complex tasks
- Debug shows Claude is working but tool usage adds overhead
- Requires --dangerously-skip-permissions flag

## Completed Work
1. ✅ Implemented complete SubprocessOrchestrator class
2. ✅ Added delegation detection for multiple formats
3. ✅ Created parallel subprocess execution framework
4. ✅ Fixed missing permissions flag
5. ✅ Integrated with CLI via --subprocess flag
6. ✅ Documented findings in tests/reports/subprocess_orchestration_findings.md

## Next Steps
1. Monitor Claude CLI updates for print mode improvements
2. Consider alternative approaches (conversation API, expect/pexpect)
3. Keep subprocess implementation ready for future use
4. Use interactive mode with built-in Task tool for now

## Key Files
- `src/orchestration/subprocess_orchestrator.py` (complete implementation)
- `src/orchestration/SUBPROCESS_DESIGN.md` (design doc with findings)
- `tests/reports/subprocess_orchestration_findings.md` (detailed analysis)
- `tests/reports/test_claude_subprocess.py` (test scripts)

## Session Summary
Previous work included:
- Fixed agent discovery by updating framework_loader.py to check templates directory
- Reduced framework size from 100KB to 1.2KB with minimal_framework_loader.py
- Discovered Claude's built-in Task tool in interactive mode creates real subprocesses perfectly
- Investigated and documented print mode limitations

## To Resume Work
1. Open this ticket in `/Users/masa/Projects/claude-mpm`
2. Review the subprocess orchestration implementation
3. Consider implementing mock subprocess mode for testing
4. Monitor Claude CLI updates for print mode improvements