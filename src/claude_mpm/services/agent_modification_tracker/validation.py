#!/usr/bin/env python3
"""
Modification validation for agent files.

This module handles validation of agent modifications to ensure correctness
and detect conflicts.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List

from .models import AgentModification


class ModificationValidator:
    """Validator for agent modifications."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def validate_modification(self, 
                                  modification: AgentModification,
                                  active_modifications: Dict[str, AgentModification]) -> None:
        """Validate agent modification for correctness."""
        try:
            # Syntax validation for Python files
            if modification.file_path.endswith('.py'):
                await self._validate_python_syntax(modification)
            
            # Structure validation for Markdown files
            elif modification.file_path.endswith('.md'):
                await self._validate_markdown_structure(modification)
            
            # Check for conflicts with other modifications
            await self._check_modification_conflicts(modification, active_modifications)
            
            if not modification.validation_errors:
                modification.validation_status = "valid"
            else:
                modification.validation_status = "invalid"
                
        except Exception as e:
            modification.validation_status = "error"
            modification.validation_errors.append(f"Validation error: {e}")
    
    async def _validate_python_syntax(self, modification: AgentModification) -> None:
        """Validate Python file syntax."""
        try:
            file_path = Path(modification.file_path)
            if file_path.exists():
                content = file_path.read_text(encoding='utf-8')
                compile(content, modification.file_path, 'exec')
        except SyntaxError as e:
            modification.validation_errors.append(f"Python syntax error: {e}")
        except Exception as e:
            modification.validation_errors.append(f"Python validation error: {e}")
    
    async def _validate_markdown_structure(self, modification: AgentModification) -> None:
        """Validate Markdown file structure."""
        try:
            file_path = Path(modification.file_path)
            if file_path.exists():
                content = file_path.read_text(encoding='utf-8')
                
                # Check for required sections
                required_sections = ['# ', '## Role', '## Capabilities']
                missing_sections = []
                
                for section in required_sections:
                    if section not in content:
                        missing_sections.append(section)
                
                if missing_sections:
                    modification.validation_errors.append(
                        f"Missing required sections: {', '.join(missing_sections)}"
                    )
                
        except Exception as e:
            modification.validation_errors.append(f"Markdown validation error: {e}")
    
    async def _check_modification_conflicts(self, 
                                          modification: AgentModification,
                                          active_modifications: Dict[str, AgentModification]) -> None:
        """Check for conflicts with other modifications."""
        # Check for recent modifications to the same file
        recent_mods = [
            mod for mod in active_modifications.values()
            if (mod.file_path == modification.file_path and 
                mod.modification_id != modification.modification_id and
                (time.time() - mod.timestamp) < 60)  # Within last minute
        ]
        
        if recent_mods:
            modification.validation_errors.append(
                f"Potential conflict: {len(recent_mods)} recent modifications to same file"
            )
    
    def get_validation_stats(self, modifications: List[AgentModification]) -> Dict[str, int]:
        """Get validation statistics for modifications."""
        stats = {
            'valid': 0,
            'invalid': 0,
            'pending': 0,
            'error': 0
        }
        
        for mod in modifications:
            status = mod.validation_status
            if status in stats:
                stats[status] += 1
            else:
                stats['error'] += 1
        
        return stats