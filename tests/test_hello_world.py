#!/usr/bin/env python3
"""
Simple Hello World test demonstrating claude-mpm is operational.
This script shows basic usage of the SimpleClaudeRunner.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.claude_runner import SimpleClaudeRunner, create_simple_context


def hello_world_demo():
    """Demonstrate basic claude-mpm functionality with Hello World."""
    print("=" * 60)
    print("Claude MPM - Hello World Demo")
    print("=" * 60)
    
    try:
        # Create a simple runner without tickets or logging
        print("\n1. Creating SimpleClaudeRunner...")
        runner = SimpleClaudeRunner(enable_tickets=False, log_level="OFF")
        print("   ✅ Runner created successfully")
        
        # Create a simple context
        print("\n2. Creating execution context...")
        context = create_simple_context()
        print("   ✅ Context created")
        print(f"   - Context length: {len(context)} characters")
        print(f"   - Context preview: {context[:100]}...")
        
        # Demonstrate what would happen with a prompt
        print("\n3. Example usage (dry run - no actual Claude call):")
        print("   - In interactive mode: runner.run_interactive(context)")
        print("   - In non-interactive mode: runner.run_oneshot('Hello, World!', context)")
        
        print("\n4. System capabilities:")
        
        # Show available agents
        from claude_mpm.agents import list_available_agents
        agents = list_available_agents()
        print(f"   - Available agents: {len(agents)}")
        if agents:
            print("     Agents:", ", ".join(list(agents.keys())[:5]), "...")
        
        # Show hook system status
        from claude_mpm.services.json_rpc_hook_manager import JSONRPCHookManager
        hook_manager = JSONRPCHookManager()
        if hook_manager.start_service():
            print("   - Hook system: ✅ Operational")
            hook_manager.stop_service()
        else:
            print("   - Hook system: ⚠️  Not available (may be disabled)")
        
        print("\n✅ Hello World demo completed successfully!")
        print("\nThe claude-mpm system is operational and ready to use.")
        print("\nTo run claude-mpm:")
        print("  Interactive mode:     ./claude-mpm")
        print("  Non-interactive:      ./claude-mpm run -i 'Your prompt here' --non-interactive")
        print("  With specific agent:  ./claude-mpm run --agent engineer -i 'Your prompt'")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = hello_world_demo()
    sys.exit(0 if success else 1)