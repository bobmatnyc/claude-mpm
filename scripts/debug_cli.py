#!/usr/bin/env python3
"""
Debug script to test CLI search functionality.
"""

import sys
import os
from pathlib import Path

# Add the mcp-vector-search source to Python path
MCP_VECTOR_SEARCH_ROOT = "/Users/masa/Projects/managed/mcp-vector-search"
sys.path.insert(0, os.path.join(MCP_VECTOR_SEARCH_ROOT, "src"))

# Set up environment
os.environ["VIRTUAL_ENV"] = os.path.join(MCP_VECTOR_SEARCH_ROOT, ".venv")
os.environ["PATH"] = f"{os.path.join(MCP_VECTOR_SEARCH_ROOT, '.venv', 'bin')}:{os.environ.get('PATH', '')}"

async def debug_cli_search():
    """Debug the CLI search functionality."""
    try:
        from mcp_vector_search.cli.commands.search import run_search
        
        print("🔍 Starting CLI search debug...")
        
        # Test the exact same function the CLI uses
        project_root = Path("/Users/masa/Projects/claude-mpm")
        
        print("🔧 Testing run_search function...")
        await run_search(
            project_root=project_root,
            query="function",
            limit=3,
            similarity_threshold=0.0,
            show_content=True,
            json_output=False,
        )
        
        print("✅ CLI search debug completed!")
        
    except Exception as e:
        print(f"❌ CLI search debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_cli_search())
