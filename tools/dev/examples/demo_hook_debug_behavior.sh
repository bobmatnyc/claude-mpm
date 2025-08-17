#!/bin/bash
# Demo script showing hook handler debug mode behavior

echo "🔍 Hook Handler Debug Mode Demo"
echo "==============================="
echo

echo "1️⃣ DEFAULT BEHAVIOR (no environment variable) - Debug ON:"
echo "Command: echo '{...}' | python hook_handler.py"
echo "Output:"
echo '{"hook_event_name": "UserPromptSubmit", "session_id": "demo1", "prompt": "Default test"}' | python src/claude_mpm/hooks/claude_hooks/hook_handler.py 2>&1 | head -2
echo

echo "2️⃣ DISABLE DEBUG with CLAUDE_MPM_HOOK_DEBUG=false - Debug OFF:"
echo "Command: CLAUDE_MPM_HOOK_DEBUG=false echo '{...}' | python hook_handler.py"
echo "Output (should be minimal):"
CLAUDE_MPM_HOOK_DEBUG=false echo '{"hook_event_name": "UserPromptSubmit", "session_id": "demo2", "prompt": "False test"}' | python src/claude_mpm/hooks/claude_hooks/hook_handler.py 2>&1 | wc -l | xargs -I {} echo "Only {} lines of stderr output"
echo

echo "3️⃣ DISABLE DEBUG with CLAUDE_MPM_HOOK_DEBUG=FALSE - Debug OFF:"
echo "Command: CLAUDE_MPM_HOOK_DEBUG=FALSE echo '{...}' | python hook_handler.py"
echo "Output (should be minimal):"
CLAUDE_MPM_HOOK_DEBUG=FALSE echo '{"hook_event_name": "UserPromptSubmit", "session_id": "demo3", "prompt": "FALSE test"}' | python src/claude_mpm/hooks/claude_hooks/hook_handler.py 2>&1 | wc -l | xargs -I {} echo "Only {} lines of stderr output"
echo

echo "4️⃣ BACKWARD COMPATIBILITY with CLAUDE_MPM_HOOK_DEBUG=true - Debug ON:"
echo "Command: CLAUDE_MPM_HOOK_DEBUG=true echo '{...}' | python hook_handler.py"
echo "Output:"
CLAUDE_MPM_HOOK_DEBUG=true echo '{"hook_event_name": "UserPromptSubmit", "session_id": "demo4", "prompt": "True test"}' | python src/claude_mpm/hooks/claude_hooks/hook_handler.py 2>&1 | head -2
echo

echo "5️⃣ EDGE CASE with CLAUDE_MPM_HOOK_DEBUG=no - Debug ON (only 'false' disables):"
echo "Command: CLAUDE_MPM_HOOK_DEBUG=no echo '{...}' | python hook_handler.py"
echo "Output:"
CLAUDE_MPM_HOOK_DEBUG=no echo '{"hook_event_name": "UserPromptSubmit", "session_id": "demo5", "prompt": "No test"}' | python src/claude_mpm/hooks/claude_hooks/hook_handler.py 2>&1 | head -1
echo

echo "✅ SUMMARY:"
echo "• Debug is ON by default (no environment variable needed)"
echo "• Set CLAUDE_MPM_HOOK_DEBUG=false to disable (case-insensitive)"
echo "• All other values (including 'true', 'no', '0', etc.) enable debug"
echo "• Only the string 'false' (case-insensitive) disables debug mode"
