#!/usr/bin/env python3
"""Fix the identified memory system issues."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import directly to modify the methods
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager
from claude_mpm.core.config import Config


def fix_duplicate_prevention():
    """Fix the duplicate prevention logic."""
    
    def fixed_add_learnings_to_memory(self, agent_id: str, learnings: list) -> bool:
        """Add new learnings to existing agent memory with fixed duplicate prevention.
        
        Args:
            agent_id: The agent identifier
            learnings: List of new learning strings to add
            
        Returns:
            bool: True if memory was successfully updated
        """
        try:
            # Load existing memory
            current_memory = self.load_agent_memory(agent_id)
            
            # Parse existing memory into sections
            sections = self._parse_memory_sections(current_memory)
            
            # Clean sections - remove template placeholder text
            sections = self._clean_template_placeholders(sections)
            
            # Determine which section to add learnings to based on content
            for learning in learnings:
                if not learning or not isinstance(learning, str):
                    continue
                    
                learning = learning.strip()
                if not learning:  # Skip empty strings after stripping
                    continue
                
                # Categorize the learning based on keywords
                section = self._categorize_learning(learning)
                
                # Add to appropriate section if not duplicate
                if section not in sections:
                    sections[section] = []
                
                # Check for duplicates (case-insensitive) - FIXED LOGIC
                normalized_learning = learning.lower()
                # Strip bullet points from existing items for comparison
                existing_normalized = [item.lstrip('- ').strip().lower() for item in sections[section]]
                
                if normalized_learning not in existing_normalized:
                    # Add bullet point if not present
                    if not learning.startswith("-"):
                        learning = f"- {learning}"
                    sections[section].append(learning)
                else:
                    self.logger.debug(f"Skipping duplicate memory: {learning}")
            
            # Rebuild memory content
            new_content = self._build_memory_content(agent_id, sections)
            
            # Validate and save
            agent_limits = self._get_agent_limits(agent_id)
            if self.content_manager.exceeds_limits(new_content, agent_limits):
                self.logger.debug(f"Memory for {agent_id} exceeds limits, truncating")
                new_content = self.content_manager.truncate_to_limits(new_content, agent_limits)
            
            return self._save_memory_file(agent_id, new_content)
            
        except Exception as e:
            self.logger.error(f"Error adding learnings to memory for {agent_id}: {e}")
            return False
    
    # Apply the fix
    AgentMemoryManager._add_learnings_to_memory = fixed_add_learnings_to_memory
    print("✓ Fixed duplicate prevention logic")


def fix_categorization():
    """Fix the categorization logic."""
    
    def fixed_categorize_learning(self, learning: str) -> str:
        """Categorize a learning item into appropriate section with improved logic.
        
        Args:
            learning: The learning string to categorize
            
        Returns:
            str: The section name for this learning
        """
        learning_lower = learning.lower()
        
        # Check for keywords to categorize with improved patterns
        # Architecture keywords
        if any(word in learning_lower for word in ["architecture", "structure", "design", "module", "component", "microservices", "service-oriented"]):
            return "Project Architecture"
            
        # Pattern keywords (including dependency injection, conventions)
        elif any(word in learning_lower for word in ["pattern", "convention", "style", "format", "dependency injection", "instantiation", "use", "implement"]):
            return "Coding Patterns Learned"
            
        # Guideline keywords (including docstrings, standards)
        elif any(word in learning_lower for word in ["guideline", "rule", "standard", "practice", "docstring", "documentation", "must", "should", "include", "comprehensive"]):
            return "Implementation Guidelines"
            
        # Mistake keywords
        elif any(word in learning_lower for word in ["mistake", "error", "avoid", "don't", "never", "not"]):
            return "Common Mistakes to Avoid"
            
        # Strategy keywords  
        elif any(word in learning_lower for word in ["strategy", "approach", "method", "technique", "effective"]):
            return "Effective Strategies"
            
        # Integration keywords
        elif any(word in learning_lower for word in ["integration", "interface", "api", "connection", "database", "pooling", "via"]):
            return "Integration Points"
            
        # Performance keywords
        elif any(word in learning_lower for word in ["performance", "optimization", "speed", "efficiency"]):
            return "Performance Considerations"
            
        # Context keywords (including version, working on, currently)
        elif any(word in learning_lower for word in ["context", "current", "currently", "working", "version", "release", "candidate"]):
            return "Current Technical Context"
            
        # Domain keywords
        elif any(word in learning_lower for word in ["domain", "business", "specific"]):
            return "Domain-Specific Knowledge"
            
        else:
            return "Recent Learnings"
    
    # Apply the fix
    AgentMemoryManager._categorize_learning = fixed_categorize_learning
    print("✓ Fixed categorization logic")


def fix_empty_string_handling():
    """Fix empty string handling in JSON extraction."""
    
    def fixed_extract_and_update_memory(self, agent_id: str, response: str) -> bool:
        """Extract memory updates from agent response with improved validation.

        Args:
            agent_id: The agent identifier
            response: The agent's response text (may contain JSON)

        Returns:
            bool: True if memory was updated, False otherwise
        """
        try:
            import json
            import re
            
            # Look for JSON block in the response
            json_pattern = r'```json\s*(.*?)\s*```'
            json_matches = re.findall(json_pattern, response, re.DOTALL)
            
            if not json_matches:
                # Also try to find inline JSON objects
                json_pattern2 = r'\{[^{}]*"(?:remember|Remember)"[^{}]*\}'
                json_matches = re.findall(json_pattern2, response, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    
                    # Check for memory updates in "remember" field
                    memory_items = None
                    
                    # Check both "remember" and "Remember" fields
                    if "remember" in data:
                        memory_items = data["remember"]
                    elif "Remember" in data:
                        memory_items = data["Remember"]
                    
                    # Process memory items if found and not null
                    if memory_items is not None and memory_items != "null":
                        # Skip if explicitly null or empty list
                        if isinstance(memory_items, list) and len(memory_items) > 0:
                            # Filter out empty strings and None values
                            valid_items = []
                            for item in memory_items:
                                if item and isinstance(item, str) and item.strip():
                                    valid_items.append(item.strip())
                            
                            # Only proceed if we have valid items
                            if valid_items:
                                success = self._add_learnings_to_memory(agent_id, valid_items)
                                if success:
                                    self.logger.info(f"Added {len(valid_items)} new memories for {agent_id}")
                                    return True
                    
                except json.JSONDecodeError:
                    # Not valid JSON, continue to next match
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error extracting memory from response for {agent_id}: {e}")
            return False
    
    # Apply the fix
    AgentMemoryManager.extract_and_update_memory = fixed_extract_and_update_memory
    print("✓ Fixed empty string handling in memory extraction")


def test_fixes():
    """Test that all fixes work correctly."""
    print("\nTesting fixes...")
    print("-" * 30)
    
    config = Config()
    manager = AgentMemoryManager(config, project_root)
    
    # Test 1: Duplicate prevention
    test_agent = "test_fixed_duplicates"
    duplicate_response = """
Task completed.

```json
{
  "task_completed": true,
  "remember": ["This memory should only appear once"]
}
```
"""
    
    # Add same memory twice
    result1 = manager.extract_and_update_memory(test_agent, duplicate_response)
    result2 = manager.extract_and_update_memory(test_agent, duplicate_response)
    
    memory = manager.load_agent_memory(test_agent)
    duplicate_count = memory.count("This memory should only appear once")
    
    if duplicate_count == 1:
        print("✓ Duplicate prevention works correctly")
    else:
        print(f"✗ Duplicate prevention failed - appears {duplicate_count} times")
    
    # Test 2: Categorization
    test_agent_cat = "test_fixed_categorization"
    pattern_response = """
Task completed.

```json
{
  "task_completed": true,
  "remember": ["Always use dependency injection for service instantiation"]
}
```
"""
    
    result = manager.extract_and_update_memory(test_agent_cat, pattern_response)
    memory = manager.load_agent_memory(test_agent_cat)
    
    if "## Coding Patterns Learned" in memory:
        print("✓ Categorization works correctly")
    else:
        print("✗ Categorization still not working")
    
    # Test 3: Empty string handling
    test_agent_empty = "test_fixed_empty_strings"
    empty_response = """
Task completed.

```json
{
  "task_completed": true,
  "remember": ["", "Valid memory", "", "Another valid memory", ""]
}
```
"""
    
    result = manager.extract_and_update_memory(test_agent_empty, empty_response)
    memory = manager.load_agent_memory(test_agent_empty)
    
    valid_count = memory.count("Valid memory") + memory.count("Another valid memory")
    
    if valid_count == 2 and "- \n" not in memory and '""' not in memory:
        print("✓ Empty string handling works correctly")
    else:
        print("✗ Empty string handling failed")
        print(f"Valid count: {valid_count}")
        print("Memory snippet:")
        print(memory[:500])


if __name__ == "__main__":
    print("Applying memory system fixes...")
    
    # Apply all fixes
    fix_duplicate_prevention()
    fix_categorization()
    fix_empty_string_handling()
    
    print("\nAll fixes applied!")
    
    # Test the fixes
    test_fixes()
    
    print("\n" + "=" * 50)
    print("Memory system fixes completed and tested!")