#!/usr/bin/env python3
"""
Specialized agent support for modification tracking.

This module handles special processing for specialized agent types and
their unique metadata requirements.
"""

import logging
from typing import Dict, Any, Optional

from claude_mpm.services.agent_registry_service import AgentRegistry
from .models import AgentModification


class SpecializedAgentHandler:
    """Handler for specialized agent modifications and metadata."""
    
    def __init__(self, agent_registry: Optional[AgentRegistry] = None):
        self.logger = logging.getLogger(__name__)
        self.agent_registry = agent_registry
    
    async def handle_specialized_change(self, modification: AgentModification) -> None:
        """
        Handle specialized agent modifications for ISS-0118 integration.
        
        Args:
            modification: Agent modification record
        """
        try:
            self.logger.info(f"Handling specialized agent change: {modification.agent_name} ({modification.modification_type.value})")
            
            if not self.agent_registry:
                self.logger.warning("No agent registry available for specialized agent handling")
                return
            
            # Force registry refresh to pick up specialized agent changes
            self.agent_registry.clear_cache()
            
            # Re-discover agents to update specialized metadata
            await self.agent_registry.discover_agents(force_refresh=True)
            
            # Get updated agent metadata if available
            updated_metadata = await self.agent_registry.get_agent(modification.agent_name)
            if updated_metadata:
                # Log specialized agent information
                if updated_metadata.specializations:
                    self.logger.info(f"Agent specializations: {', '.join(updated_metadata.specializations)}")
                
                if updated_metadata.is_hybrid:
                    self.logger.info(f"Hybrid agent types: {', '.join(updated_metadata.hybrid_types)}")
                
                if updated_metadata.frameworks:
                    self.logger.info(f"Agent frameworks: {', '.join(updated_metadata.frameworks)}")
                
                # Store specialized metadata in modification record
                modification.metadata.update({
                    'specialized_type': updated_metadata.type,
                    'specializations': updated_metadata.specializations,
                    'frameworks': updated_metadata.frameworks,
                    'domains': updated_metadata.domains,
                    'roles': updated_metadata.roles,
                    'is_hybrid': updated_metadata.is_hybrid,
                    'hybrid_types': updated_metadata.hybrid_types,
                    'complexity_level': updated_metadata.complexity_level,
                    'validation_score': updated_metadata.validation_score
                })
            
        except Exception as e:
            self.logger.error(f"Error handling specialized agent change: {e}")
    
    def classify_agent_type(self, file_path: str, metadata: Dict[str, Any]) -> str:
        """
        Classify agent type based on file path and metadata.
        
        Args:
            file_path: Path to agent file
            metadata: File metadata
            
        Returns:
            Agent type classification
        """
        # Check for specialized patterns in file name
        file_name = file_path.lower()
        
        if 'architect' in file_name:
            return 'architecture'
        elif 'integration' in file_name:
            return 'integration'
        elif 'performance' in file_name:
            return 'performance'
        elif 'ui' in file_name or 'ux' in file_name:
            return 'ui_ux'
        elif 'monitor' in file_name:
            return 'monitoring'
        elif 'migrate' in file_name or 'migration' in file_name:
            return 'migration'
        elif 'automate' in file_name or 'automation' in file_name:
            return 'automation'
        elif 'validate' in file_name or 'validation' in file_name:
            return 'validation'
        
        # Check metadata for type hints
        if 'classes' in metadata:
            classes = metadata.get('classes', [])
            for class_name in classes:
                if 'Architect' in class_name:
                    return 'architecture'
                elif 'Integration' in class_name:
                    return 'integration'
                elif 'Performance' in class_name:
                    return 'performance'
        
        # Default to generic agent type
        return 'agent'
    
    def extract_specializations(self, metadata: Dict[str, Any]) -> list[str]:
        """Extract specializations from agent metadata."""
        specializations = []
        
        # Check for framework imports
        imports = metadata.get('imports', [])
        for import_name in imports:
            if 'flask' in import_name or 'django' in import_name:
                specializations.append('web_framework')
            elif 'tensorflow' in import_name or 'torch' in import_name:
                specializations.append('machine_learning')
            elif 'pandas' in import_name or 'numpy' in import_name:
                specializations.append('data_analysis')
        
        # Check for async capabilities
        if metadata.get('async_functions'):
            specializations.append('async_processing')
        
        # Check for specific class patterns
        classes = metadata.get('classes', [])
        for class_name in classes:
            if 'API' in class_name:
                specializations.append('api_integration')
            elif 'Database' in class_name or 'DB' in class_name:
                specializations.append('database')
        
        return list(set(specializations))
    
    def determine_complexity_level(self, metadata: Dict[str, Any]) -> str:
        """Determine agent complexity level based on metadata."""
        lines_of_code = metadata.get('lines_of_code', 0)
        num_classes = len(metadata.get('classes', []))
        num_functions = len(metadata.get('functions', []))
        
        # Simple heuristic for complexity
        if lines_of_code > 1000 or num_classes > 10 or num_functions > 50:
            return 'high'
        elif lines_of_code > 500 or num_classes > 5 or num_functions > 25:
            return 'medium'
        else:
            return 'low'