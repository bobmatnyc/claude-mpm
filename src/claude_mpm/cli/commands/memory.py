"""
Memory command implementation for claude-mpm.

WHY: This module provides CLI commands for managing agent memory files,
allowing users to view, add, and manage persistent learnings across sessions.

DESIGN DECISION: We follow the existing CLI pattern using a main function
that dispatches to specific subcommand handlers. This maintains consistency
with other command modules like agents.py.
"""

import json
from datetime import datetime
from pathlib import Path

import click

from ...core.logger import get_logger
from ...core.config import Config
from ...services.agent_memory_manager import AgentMemoryManager


def manage_memory(args):
    """
    Manage agent memory files.
    
    WHY: Agents need persistent memory to maintain learnings across sessions.
    This command provides a unified interface for memory-related operations.
    
    DESIGN DECISION: When no subcommand is provided, we show memory status
    as the default action, giving users a quick overview of the memory system.
    
    Args:
        args: Parsed command line arguments with memory_command attribute
    """
    logger = get_logger("cli")
    
    try:
        # Load configuration for memory manager
        config = Config()
        memory_manager = AgentMemoryManager(config)
        
        if not args.memory_command:
            # No subcommand - show status
            _show_status(memory_manager)
            return
        
        if args.memory_command == "status":
            _show_status(memory_manager)
        
        elif args.memory_command == "view":
            _view_memory(args, memory_manager)
        
        elif args.memory_command == "add":
            _add_learning(args, memory_manager)
        
        elif args.memory_command == "clean":
            _clean_memory(args, memory_manager)
        
    except Exception as e:
        logger.error(f"Error managing memory: {e}")
        print(f"❌ Error: {e}")
        return 1
    
    return 0


def _show_status(memory_manager):
    """
    Show memory file status.
    
    WHY: Users need to see what memory files exist, their sizes, and
    when they were last updated to understand the memory system state.
    
    Args:
        memory_manager: AgentMemoryManager instance
    """
    print("Agent Memory Status")
    print("-" * 80)
    
    memory_dir = memory_manager.memories_dir
    if not memory_dir.exists():
        print("📁 Memory directory not found - no agent memories stored yet")
        print(f"   Expected location: {memory_dir}")
        return
    
    memory_files = list(memory_dir.glob("*_agent.md"))
    
    if not memory_files:
        print("📭 No memory files found")
        print(f"   Memory directory: {memory_dir}")
        return
    
    print(f"📁 Memory directory: {memory_dir}")
    print(f"📊 Total memory files: {len(memory_files)}")
    print()
    
    total_size = 0
    for file_path in sorted(memory_files):
        stat = file_path.stat()
        size_kb = stat.st_size / 1024
        total_size += stat.st_size
        
        # Extract agent ID from filename (remove '_agent' suffix)
        agent_id = file_path.stem.replace('_agent', '')
        
        # Try to count sections in markdown file
        try:
            content = file_path.read_text()
            # Count level 2 headers (sections)
            section_count = len([line for line in content.splitlines() if line.startswith('## ')])
            # Count bullet points (learnings)
            learning_count = len([line for line in content.splitlines() if line.strip().startswith('- ')])
        except:
            section_count = "?"
            learning_count = "?"
        
        print(f"🧠 {agent_id}")
        print(f"   Size: {size_kb:.1f} KB")
        print(f"   Sections: {section_count}")
        print(f"   Items: {learning_count}")
        print(f"   Last modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    print(f"💾 Total size: {total_size / 1024:.1f} KB")


def _view_memory(args, memory_manager):
    """
    View agent memory file contents.
    
    WHY: Users need to inspect what learnings an agent has accumulated
    to understand its behavior and debug issues.
    
    Args:
        args: Command arguments with agent_id
        memory_manager: AgentMemoryManager instance
    """
    agent_id = args.agent_id
    
    try:
        memory_content = memory_manager.load_agent_memory(agent_id)
        
        if not memory_content:
            print(f"📭 No memory found for agent: {agent_id}")
            return
        
        print(f"🧠 Memory for agent: {agent_id}")
        print("-" * 80)
        print(memory_content)
                
    except FileNotFoundError:
        print(f"📭 No memory file found for agent: {agent_id}")
    except Exception as e:
        print(f"❌ Error viewing memory: {e}")


def _add_learning(args, memory_manager):
    """
    Manually add learning to agent memory.
    
    WHY: Allows manual injection of learnings for testing or correction
    purposes, useful for debugging and development.
    
    Args:
        args: Command arguments with agent_id, learning_type, and content
        memory_manager: AgentMemoryManager instance
    """
    agent_id = args.agent_id
    section = args.learning_type  # Map learning_type to section name
    content = args.content
    
    # Map learning types to appropriate sections
    section_map = {
        "pattern": "Project Architecture",
        "error": "Common Mistakes to Avoid",
        "optimization": "Implementation Guidelines",
        "preference": "Implementation Guidelines",
        "context": "Current Technical Context"
    }
    
    section_name = section_map.get(section, "Current Technical Context")
    
    try:
        success = memory_manager.update_agent_memory(agent_id, section_name, content)
        
        if success:
            print(f"✅ Added {section} to {agent_id} memory in section: {section_name}")
            print(f"   Content: {content[:100]}{'...' if len(content) > 100 else ''}")
        else:
            print(f"❌ Failed to add learning to {agent_id} memory")
            print("   Memory file may be at size limit or section may be full")
            
    except Exception as e:
        print(f"❌ Error adding learning: {e}")


def _clean_memory(args, memory_manager):
    """
    Clean up old/unused memory files.
    
    WHY: Memory files can accumulate over time. This provides a way to
    clean up old or unused files to save disk space.
    
    DESIGN DECISION: For Phase 1, this is a stub implementation.
    Full cleanup logic will be implemented based on usage patterns.
    
    Args:
        args: Command arguments
        memory_manager: AgentMemoryManager instance
    """
    print("🧹 Memory cleanup")
    print("-" * 80)
    
    # For Phase 1, just show what would be cleaned
    memory_dir = memory_manager.memories_dir
    if not memory_dir.exists():
        print("📁 No memory directory found - nothing to clean")
        return
    
    memory_files = list(memory_dir.glob("*_agent.md"))
    if not memory_files:
        print("📭 No memory files found - nothing to clean")
        return
    
    print(f"📊 Found {len(memory_files)} memory files")
    print()
    print("⚠️  Cleanup not yet implemented in Phase 1")
    print("   Future cleanup will remove:")
    print("   - Memory files older than 30 days with no recent access")
    print("   - Corrupted memory files")
    print("   - Memory files for non-existent agents")