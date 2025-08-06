"""
Memory command implementation for claude-mpm.

WHY: This module provides CLI commands for managing agent memory files,
allowing users to view, add, and manage persistent learnings across sessions.

DESIGN DECISION: We follow the existing CLI pattern using a main function
that dispatches to specific subcommand handlers. This maintains consistency
with other command modules like agents.py.
"""

import json
import os
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
        # Use CLAUDE_MPM_USER_PWD if available (when called via shell script),
        # otherwise use current working directory
        user_pwd = os.environ.get('CLAUDE_MPM_USER_PWD', os.getcwd())
        current_dir = Path(user_pwd)
        memory_manager = AgentMemoryManager(config, current_dir)
        
        if not args.memory_command:
            # No subcommand - show status
            _show_status(memory_manager)
            return
        
        if args.memory_command == "status":
            _show_status(memory_manager)
        
        elif args.memory_command == "view":
            _show_memories(args, memory_manager)
        
        elif args.memory_command == "add":
            _add_learning(args, memory_manager)
        
        elif args.memory_command == "clean":
            _clean_memory(args, memory_manager)
        
        elif args.memory_command == "optimize":
            _optimize_memory(args, memory_manager)
        
        elif args.memory_command == "build":
            _build_memory(args, memory_manager)
        
        elif args.memory_command == "cross-ref":
            _cross_reference_memory(args, memory_manager)
        
        elif args.memory_command == "route":
            _route_memory_command(args, memory_manager)
        
        elif args.memory_command == "show":
            _show_memories(args, memory_manager)
        
        elif args.memory_command == "init":
            _init_memory(args, memory_manager)
        
        else:
            logger.error(f"Unknown memory command: {args.memory_command}")
            print(f"Unknown memory command: {args.memory_command}")
            print("Available commands: init, status, view, add, clean, optimize, build, cross-ref, route, show")
            return 1
        
    except Exception as e:
        logger.error(f"Error managing memory: {e}")
        print(f"❌ Error: {e}")
        return 1
    
    return 0


def _init_memory(args, memory_manager):
    """
    Initialize project-specific memories via agent delegation.
    
    WHY: When starting with a new project, agents need project-specific knowledge
    beyond what automatic analysis provides. This command triggers an agent task
    to comprehensively scan the project and create custom memories.
    
    Args:
        args: Command line arguments (unused but kept for consistency)
        memory_manager: AgentMemoryManager instance
    """
    logger = get_logger("cli")
    
    print("🚀 Initializing project-specific memories...")
    print("=" * 80)
    print()
    print("This will analyze the project to:")
    print("  1. Scan project structure and documentation")
    print("  2. Analyze source code for patterns and conventions")
    print("  3. Create targeted memories for each agent type")
    print("  4. Add insights using 'claude-mpm memory add' commands")
    print()
    print("The analysis will cover:")
    print("  • Project architecture and design patterns")
    print("  • Coding conventions and standards")
    print("  • Key modules and integration points")
    print("  • Testing patterns and quality standards")
    print("  • Performance considerations")
    print("  • Domain-specific terminology")
    print()
    print("=" * 80)
    print()
    print("[Agent Task: Initialize Project-Specific Memories]")
    print()
    print("Please analyze this project and create custom memories for all agents.")
    print()
    print("Instructions:")
    print("1. Scan the project structure, documentation, and source code")
    print("2. Identify key patterns, conventions, and project-specific knowledge")
    print("3. Create targeted memories for each agent type")
    print("4. Use 'claude-mpm memory add <agent> <type> \"<content>\"' commands")
    print()
    print("Focus areas:")
    print("  • Architectural patterns and design decisions")
    print("  • Coding conventions from actual source code")
    print("  • Key modules, APIs, and integration points")
    print("  • Testing patterns and quality standards")
    print("  • Performance considerations specific to this project")
    print("  • Common pitfalls based on the codebase")
    print("  • Domain-specific terminology and concepts")
    print()
    print("Example commands to use:")
    print('  claude-mpm memory add engineer pattern "Use dependency injection with @inject"')
    print('  claude-mpm memory add qa pattern "Test files follow test_<module>_<feature>.py"')
    print('  claude-mpm memory add research context "Project uses microservices architecture"')
    print()
    print("Begin by examining the project structure and key files.")
    print()
    print("=" * 80)
    print()
    print("📝 Note: Copy the task above to execute the memory initialization process.")
    print("    Use 'claude-mpm memory add' commands to add discovered insights.")
    

def _show_status(memory_manager):
    """
    Show comprehensive memory system status.
    
    WHY: Users need to see memory system health, file sizes, optimization
    opportunities, and agent-specific statistics to understand the system state.
    
    Args:
        memory_manager: AgentMemoryManager instance
    """
    print("Agent Memory System Status")
    print("-" * 80)
    
    try:
        # Get comprehensive status from memory manager
        status = memory_manager.get_memory_status()
        
        if not status.get("success", True):
            print(f"❌ Error getting status: {status.get('error', 'Unknown error')}")
            return
        
        # Show system overview
        system_health = status.get("system_health", "unknown")
        health_emoji = {
            "healthy": "✅",
            "needs_optimization": "⚠️",
            "high_usage": "📊",
            "no_memory_dir": "📁"
        }.get(system_health, "❓")
        
        print(f"🧠 Memory System Health: {health_emoji} {system_health}")
        print(f"📁 Memory Directory: {status.get('memory_directory', 'Unknown')}")
        print(f"🔧 System Enabled: {'Yes' if status.get('system_enabled', True) else 'No'}")
        print(f"📚 Auto Learning: {'Yes' if status.get('auto_learning', True) else 'No'}")
        print(f"📊 Total Agents: {status.get('total_agents', 0)}")
        print(f"💾 Total Size: {status.get('total_size_kb', 0):.1f} KB")
        print()
        
        # Show optimization opportunities
        opportunities = status.get("optimization_opportunities", [])
        if opportunities:
            print(f"⚠️  Optimization Opportunities ({len(opportunities)}):")
            for opportunity in opportunities[:5]:  # Show top 5
                print(f"   • {opportunity}")
            if len(opportunities) > 5:
                print(f"   ... and {len(opportunities) - 5} more")
            print()
        
        # Show per-agent details
        agents = status.get("agents", {})
        if agents:
            print(f"📋 Agent Memory Details:")
            for agent_id, agent_info in sorted(agents.items()):
                if "error" in agent_info:
                    print(f"   ❌ {agent_id}: Error - {agent_info['error']}")
                    continue
                
                size_kb = agent_info.get("size_kb", 0)
                size_limit = agent_info.get("size_limit_kb", 8)
                utilization = agent_info.get("size_utilization", 0)
                sections = agent_info.get("sections", 0)
                items = agent_info.get("items", 0)
                last_modified = agent_info.get("last_modified", "Unknown")
                auto_learning = agent_info.get("auto_learning", True)
                
                # Format last modified time
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                    last_modified_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    last_modified_str = last_modified
                
                # Status indicator based on usage
                if utilization > 90:
                    status_emoji = "🔴"  # High usage
                elif utilization > 70:
                    status_emoji = "🟡"  # Medium usage
                else:
                    status_emoji = "🟢"  # Low usage
                
                print(f"   {status_emoji} {agent_id}")
                print(f"      Size: {size_kb:.1f} KB / {size_limit} KB ({utilization:.1f}%)")
                print(f"      Content: {sections} sections, {items} items")
                print(f"      Auto-learning: {'On' if auto_learning else 'Off'}")
                print(f"      Last modified: {last_modified_str}")
        else:
            print("📭 No agent memories found")
            
    except Exception as e:
        print(f"❌ Error showing status: {e}")
        # Fallback to basic status display
        _show_basic_status(memory_manager)


def _show_basic_status(memory_manager):
    """Fallback basic status display if comprehensive status fails."""
    print("\n--- Basic Status (Fallback) ---")
    
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
    
    total_size = 0
    for file_path in sorted(memory_files):
        stat = file_path.stat()
        size_kb = stat.st_size / 1024
        total_size += stat.st_size
        
        agent_id = file_path.stem.replace('_agent', '')
        print(f"   {agent_id}: {size_kb:.1f} KB")
    
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


def _optimize_memory(args, memory_manager):
    """
    Optimize memory files by removing duplicates and consolidating similar items.
    
    WHY: Memory files can become cluttered over time with duplicate or redundant
    information. This command provides automated cleanup while preserving
    important learnings.
    
    Args:
        args: Command arguments with optional agent_id
        memory_manager: AgentMemoryManager instance
    """
    print("🔧 Memory Optimization")
    print("-" * 80)
    
    agent_id = getattr(args, 'agent_id', None)
    
    try:
        if agent_id:
            print(f"📊 Optimizing memory for agent: {agent_id}")
            result = memory_manager.optimize_memory(agent_id)
        else:
            print("📊 Optimizing all agent memories...")
            result = memory_manager.optimize_memory()
        
        if result.get("success"):
            if agent_id:
                # Single agent results
                _display_single_optimization_result(result)
            else:
                # All agents results
                _display_bulk_optimization_results(result)
        else:
            print(f"❌ Optimization failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error during optimization: {e}")


def _build_memory(args, memory_manager):
    """
    Build agent memories from project documentation.
    
    WHY: Project documentation contains valuable patterns and guidelines that
    agents should be aware of. This command automatically extracts and assigns
    relevant information to appropriate agents.
    
    Args:
        args: Command arguments with optional force_rebuild flag
        memory_manager: AgentMemoryManager instance
    """
    print("📚 Memory Building from Documentation")
    print("-" * 80)
    
    force_rebuild = getattr(args, 'force_rebuild', False)
    
    try:
        print("🔍 Analyzing project documentation...")
        result = memory_manager.build_memories_from_docs(force_rebuild)
        
        if result.get("success"):
            print(f"✅ Successfully processed documentation")
            print(f"   Files processed: {result.get('files_processed', 0)}")
            print(f"   Memories created: {result.get('memories_created', 0)}")
            print(f"   Memories updated: {result.get('memories_updated', 0)}")
            print(f"   Agents affected: {result.get('total_agents_affected', 0)}")
            
            if result.get('agents_affected'):
                print(f"   Affected agents: {', '.join(result['agents_affected'])}")
            
            # Show file-specific results
            files_results = result.get('files', {})
            if files_results:
                print("\n📄 File processing details:")
                for file_path, file_result in files_results.items():
                    if file_result.get('success'):
                        extracted = file_result.get('items_extracted', 0)
                        created = file_result.get('memories_created', 0)
                        print(f"   {file_path}: {extracted} items extracted, {created} memories created")
            
            if result.get('errors'):
                print("\n⚠️  Errors encountered:")
                for error in result['errors']:
                    print(f"   {error}")
                    
        else:
            print(f"❌ Build failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error building memories: {e}")


def _cross_reference_memory(args, memory_manager):
    """
    Find cross-references and common patterns across agent memories.
    
    WHY: Different agents may have learned similar information or there may be
    knowledge gaps that can be identified through cross-referencing.
    
    Args:
        args: Command arguments with optional query
        memory_manager: AgentMemoryManager instance
    """
    print("🔗 Memory Cross-Reference Analysis")
    print("-" * 80)
    
    query = getattr(args, 'query', None)
    
    try:
        if query:
            print(f"🔍 Searching for: '{query}'")
        else:
            print("🔍 Analyzing all agent memories for patterns...")
            
        result = memory_manager.cross_reference_memories(query)
        
        if result.get("success") is False:
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            return
        
        # Display common patterns
        common_patterns = result.get("common_patterns", [])
        if common_patterns:
            print(f"\n🔄 Common patterns found ({len(common_patterns)}):")
            for pattern in common_patterns[:10]:  # Show top 10
                agents = ', '.join(pattern['agents'])
                print(f"   • {pattern['pattern']}")
                print(f"     Found in: {agents} ({pattern['count']} instances)")
        else:
            print("\n🔄 No common patterns found")
        
        # Display query matches if query was provided
        if query and result.get("query_matches"):
            print(f"\n🎯 Query matches for '{query}':")
            for match in result["query_matches"]:
                print(f"   📋 {match['agent']}:")
                for line in match['matches'][:3]:  # Show first 3 matches
                    print(f"      • {line}")
        
        # Display agent correlations
        correlations = result.get("agent_correlations", {})
        if correlations:
            print(f"\n🤝 Agent knowledge correlations:")
            sorted_correlations = sorted(correlations.items(), key=lambda x: x[1], reverse=True)
            for agents, count in sorted_correlations[:5]:  # Show top 5
                print(f"   {agents}: {count} common items")
        else:
            print("\n🤝 No significant correlations found")
            
    except Exception as e:
        print(f"❌ Error during cross-reference analysis: {e}")


def _show_memories(args, memory_manager):
    """
    Show agent memories in a user-friendly format with cross-references and patterns.
    
    WHY: Users need to see agent memories in a readable format to understand
    what agents have learned and identify common patterns across agents.
    
    DESIGN DECISION: Added --raw flag to output structured JSON data for
    programmatic processing, enabling external tools and scripts to access
    all agent memories in a structured format.
    
    Args:
        args: Command arguments with optional agent_id, format, and raw flag
        memory_manager: AgentMemoryManager instance
    """
    agent_id = getattr(args, 'agent_id', None)
    format_type = getattr(args, 'format', 'detailed')
    raw_output = getattr(args, 'raw', False)
    
    try:
        if raw_output:
            # Output structured JSON data
            if agent_id:
                # Get single agent memory in raw format
                _output_single_agent_raw(agent_id, memory_manager)
            else:
                # Get all agent memories in raw format
                _output_all_memories_raw(memory_manager)
        else:
            # Normal user-friendly display
            print("🧠 Agent Memories Display")
            print("-" * 80)
            
            if agent_id:
                _show_single_agent_memory(agent_id, format_type, memory_manager)
            else:
                _show_all_agent_memories(format_type, memory_manager)
                
    except Exception as e:
        if raw_output:
            # Output error in JSON format for consistency
            error_output = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(error_output, indent=2))
        else:
            print(f"❌ Error showing memories: {e}")


def _show_single_agent_memory(agent_id, format_type, memory_manager):
    """Show memory for a single agent in the specified format."""
    memory_content = memory_manager.load_agent_memory(agent_id)
    
    if not memory_content:
        print(f"📭 No memory found for agent: {agent_id}")
        return
    
    print(f"🤖 Agent: {agent_id}")
    print("-" * 40)
    
    if format_type == 'full':
        print(memory_content)
    else:
        # Parse and display memory sections
        sections = _parse_memory_content(memory_content)
        
        for section_name, items in sections.items():
            if items:
                print(f"\n📚 {section_name} ({len(items)} items):")
                for i, item in enumerate(items[:5], 1):  # Show first 5 items
                    print(f"   {i}. {item}")
                if len(items) > 5:
                    print(f"   ... and {len(items) - 5} more")


def _show_all_agent_memories(format_type, memory_manager):
    """Show memories for all agents with cross-references."""
    # Get all available agent memory files
    memory_dir = memory_manager.memories_dir
    if not memory_dir.exists():
        print("📁 No memory directory found")
        return
    
    memory_files = list(memory_dir.glob("*_agent.md"))
    if not memory_files:
        print("📭 No agent memories found")
        return
    
    print(f"📊 Found memories for {len(memory_files)} agents")
    print()
    
    agent_memories = {}
    total_items = 0
    
    # Load all agent memories
    for file_path in sorted(memory_files):
        agent_id = file_path.stem.replace('_agent', '')
        try:
            memory_content = memory_manager.load_agent_memory(agent_id)
            if memory_content:
                sections = _parse_memory_content(memory_content)
                agent_memories[agent_id] = sections
                
                # Count items
                item_count = sum(len(items) for items in sections.values())
                total_items += item_count
                
                if format_type == 'summary':
                    print(f"🤖 {agent_id}")
                    print(f"   📚 {len(sections)} sections, {item_count} total items")
                    
                    # Show section summary
                    for section_name, items in sections.items():
                        if items:
                            print(f"      • {section_name}: {len(items)} items")
                    print()
                elif format_type == 'detailed':
                    print(f"🤖 {agent_id}")
                    print(f"   📚 {len(sections)} sections, {item_count} total items")
                    
                    for section_name, items in sections.items():
                        if items:
                            print(f"\n   📖 {section_name}:")
                            for item in items[:3]:  # Show first 3 items
                                print(f"      • {item}")
                            if len(items) > 3:
                                print(f"      ... and {len(items) - 3} more")
                    print()
        except Exception as e:
            print(f"❌ Error loading memory for {agent_id}: {e}")
    
    print(f"📊 Total: {total_items} memory items across {len(agent_memories)} agents")
    
    # Show cross-references if we have multiple agents
    if len(agent_memories) > 1:
        print("\n🔗 Cross-References and Common Patterns:")
        _find_common_patterns(agent_memories)


def _parse_memory_content(content):
    """Parse memory content into sections and items."""
    sections = {}
    current_section = None
    current_items = []
    
    for line in content.split('\n'):
        line = line.strip()
        
        if line.startswith('## ') and not line.startswith('## Memory Usage'):
            # New section
            if current_section and current_items:
                sections[current_section] = current_items.copy()
            
            current_section = line[3:].strip()
            current_items = []
        elif line.startswith('- ') and current_section:
            # Item in current section
            item = line[2:].strip()
            if item and len(item) > 5:  # Filter out very short items
                current_items.append(item)
    
    # Add final section
    if current_section and current_items:
        sections[current_section] = current_items
    
    return sections


def _find_common_patterns(agent_memories):
    """Find common patterns across agent memories."""
    pattern_count = {}
    agent_patterns = {}
    
    # Collect all patterns and which agents have them
    for agent_id, sections in agent_memories.items():
        agent_patterns[agent_id] = set()
        
        for section_name, items in sections.items():
            for item in items:
                # Normalize item for comparison (lowercase, basic cleanup)
                normalized = item.lower().strip()
                if len(normalized) > 10:  # Skip very short items
                    pattern_count[normalized] = pattern_count.get(normalized, 0) + 1
                    agent_patterns[agent_id].add(normalized)
    
    # Find patterns that appear in multiple agents
    common_patterns = [(pattern, count) for pattern, count in pattern_count.items() if count > 1]
    common_patterns.sort(key=lambda x: x[1], reverse=True)
    
    if common_patterns:
        print("\n🔄 Most Common Patterns:")
        for pattern, count in common_patterns[:5]:
            # Find which agents have this pattern
            agents_with_pattern = [agent for agent, patterns in agent_patterns.items() 
                                   if pattern in patterns]
            print(f"   • {pattern[:80]}{'...' if len(pattern) > 80 else ''}")
            print(f"     Found in: {', '.join(agents_with_pattern)} ({count} agents)")
            print()
    else:
        print("   No common patterns found across agents")
    
    # Show agent similarities
    print("\n🤝 Agent Knowledge Similarity:")
    agents = list(agent_memories.keys())
    for i, agent1 in enumerate(agents):
        for agent2 in agents[i+1:]:
            common_items = len(agent_patterns[agent1] & agent_patterns[agent2])
            if common_items > 0:
                total_items = len(agent_patterns[agent1] | agent_patterns[agent2])
                similarity = (common_items / total_items) * 100 if total_items > 0 else 0
                print(f"   {agent1} ↔ {agent2}: {common_items} common items ({similarity:.1f}% similarity)")


def _route_memory_command(args, memory_manager):
    """
    Test memory command routing logic.
    
    WHY: Users and developers need to understand how memory commands are routed
    to appropriate agents for debugging and customization purposes.
    
    Args:
        args: Command arguments with content to route
        memory_manager: AgentMemoryManager instance
    """
    print("🎯 Memory Command Routing Test")
    print("-" * 80)
    
    content = getattr(args, 'content', None)
    if not content:
        print("❌ No content provided for routing analysis")
        print("   Usage: memory route --content 'your content here'")
        return
        
    try:
        print(f"📝 Analyzing content: '{content[:100]}{'...' if len(content) > 100 else ''}'")
        
        result = memory_manager.route_memory_command(content)
        
        if result.get("success") is False:
            print(f"❌ Routing failed: {result.get('error', 'Unknown error')}")
            return
        
        target_agent = result.get("target_agent", "unknown")
        section = result.get("section", "unknown")
        confidence = result.get("confidence", 0.0)
        reasoning = result.get("reasoning", "No reasoning provided")
        
        print(f"\n🎯 Routing Decision:")
        print(f"   Target Agent: {target_agent}")
        print(f"   Section: {section}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Reasoning: {reasoning}")
        
        # Show agent scores if available
        agent_scores = result.get("agent_scores", {})
        if agent_scores:
            print(f"\n📊 Agent Relevance Scores:")
            sorted_scores = sorted(
                [(agent, data['score']) for agent, data in agent_scores.items()],
                key=lambda x: x[1], reverse=True
            )
            for agent, score in sorted_scores[:5]:  # Show top 5
                print(f"   {agent}: {score:.3f}")
                # Show matched keywords if available
                if agent in agent_scores and agent_scores[agent].get('matched_keywords'):
                    keywords = ', '.join(agent_scores[agent]['matched_keywords'][:3])
                    print(f"      Keywords: {keywords}")
        
    except Exception as e:
        print(f"❌ Error routing memory command: {e}")


def _display_single_optimization_result(result):
    """Display optimization results for a single agent."""
    agent_id = result.get("agent_id", "unknown")
    original_size = result.get("original_size", 0)
    optimized_size = result.get("optimized_size", 0)
    size_reduction = result.get("size_reduction", 0)
    size_reduction_percent = result.get("size_reduction_percent", 0)
    
    print(f"✅ Optimization completed for {agent_id}")
    print(f"   Original size: {original_size:,} bytes")
    print(f"   Optimized size: {optimized_size:,} bytes")
    print(f"   Size reduction: {size_reduction:,} bytes ({size_reduction_percent}%)")
    
    duplicates = result.get("duplicates_removed", 0)
    consolidated = result.get("items_consolidated", 0)
    reordered = result.get("items_reordered", 0)
    
    if duplicates > 0:
        print(f"   Duplicates removed: {duplicates}")
    if consolidated > 0:
        print(f"   Items consolidated: {consolidated}")
    if reordered > 0:
        print(f"   Sections reordered: {reordered}")
    
    backup_path = result.get("backup_created")
    if backup_path:
        print(f"   Backup created: {backup_path}")


def _display_bulk_optimization_results(result):
    """Display optimization results for all agents."""
    summary = result.get("summary", {})
    
    print(f"✅ Bulk optimization completed")
    print(f"   Agents processed: {summary.get('agents_processed', 0)}")
    print(f"   Agents optimized: {summary.get('agents_optimized', 0)}")
    print(f"   Total size before: {summary.get('total_size_before', 0):,} bytes")
    print(f"   Total size after: {summary.get('total_size_after', 0):,} bytes")
    print(f"   Total reduction: {summary.get('total_size_reduction', 0):,} bytes ({summary.get('total_size_reduction_percent', 0)}%)")
    print(f"   Total duplicates removed: {summary.get('total_duplicates_removed', 0)}")
    print(f"   Total items consolidated: {summary.get('total_items_consolidated', 0)}")
    
    # Show per-agent summary
    agents_results = result.get("agents", {})
    if agents_results:
        print(f"\n📊 Per-agent results:")
        for agent_id, agent_result in agents_results.items():
            if agent_result.get("success"):
                reduction = agent_result.get("size_reduction_percent", 0)
                duplicates = agent_result.get("duplicates_removed", 0)
                consolidated = agent_result.get("items_consolidated", 0)
                
                status_parts = []
                if duplicates > 0:
                    status_parts.append(f"{duplicates} dupes")
                if consolidated > 0:
                    status_parts.append(f"{consolidated} consolidated")
                
                status = f" ({', '.join(status_parts)})" if status_parts else ""
                print(f"   {agent_id}: {reduction}% reduction{status}")
            else:
                error = agent_result.get("error", "Unknown error")
                print(f"   {agent_id}: ❌ {error}")


def _output_all_memories_raw(memory_manager):
    """
    Output all agent memories in raw JSON format.
    
    WHY: Provides programmatic access to all agent memories for external tools,
    scripts, or APIs that need to process or analyze the complete memory state.
    
    Args:
        memory_manager: AgentMemoryManager instance
    """
    try:
        raw_data = memory_manager.get_all_memories_raw()
        print(json.dumps(raw_data, indent=2, ensure_ascii=False))
    except Exception as e:
        error_output = {
            "success": False,
            "error": f"Failed to retrieve all memories: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(error_output, indent=2))


def _output_single_agent_raw(agent_id, memory_manager):
    """
    Output single agent memory in raw JSON format.
    
    WHY: Provides programmatic access to a specific agent's memory for
    targeted analysis or processing by external tools.
    
    Args:
        agent_id: ID of the agent to retrieve memory for
        memory_manager: AgentMemoryManager instance
    """
    try:
        # Get all memories and extract the specific agent
        all_memories = memory_manager.get_all_memories_raw()
        
        if not all_memories.get("success", False):
            error_output = {
                "success": False,
                "error": all_memories.get("error", "Failed to retrieve memories"),
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(error_output, indent=2))
            return
        
        agents = all_memories.get("agents", {})
        if agent_id not in agents:
            error_output = {
                "success": False,
                "error": f"No memory found for agent: {agent_id}",
                "available_agents": list(agents.keys()),
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(error_output, indent=2))
            return
        
        # Return single agent data with metadata
        single_agent_output = {
            "success": True,
            "timestamp": all_memories["timestamp"],
            "agent": agents[agent_id]
        }
        
        print(json.dumps(single_agent_output, indent=2, ensure_ascii=False))
        
    except Exception as e:
        error_output = {
            "success": False,
            "error": f"Failed to retrieve memory for agent {agent_id}: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(error_output, indent=2))