"""
Agent Validation Module
Handles agent validation and quality checks

Created: 2025-07-19
Purpose: Agent validation functionality
"""

import logging
from pathlib import Path
from typing import Dict, List, Any

from .metadata import AgentMetadata
from .utils import COMPATIBLE_COMBINATIONS

logger = logging.getLogger(__name__)


class AgentValidator:
    """Handles agent validation and quality checks"""
    
    def validate_agents(self, agents: Dict[str, AgentMetadata]) -> Dict[str, AgentMetadata]:
        """
        Enhanced agent validation with specialized agent verification for ISS-0118.
        
        Args:
            agents: Dictionary of agents to validate
            
        Returns:
            Validated agents dictionary with validation scores
        """
        validated = {}
        
        for name, metadata in agents.items():
            try:
                validation_score = 0.0
                validation_errors = []
                
                # Basic file validation
                if not Path(metadata.path).exists():
                    metadata.validated = False
                    metadata.error_message = "File not found"
                    metadata.validation_score = 0.0
                    validated[name] = metadata
                    continue
                
                validation_score += 10  # File exists
                
                # Content validation for markdown files
                try:
                    with open(metadata.path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Basic markdown validation
                    if metadata.path.endswith('.md'):
                        # Check for required sections
                        required_sections = ['Primary Role', 'Core Capabilities']
                        for section in required_sections:
                            if f"## 🎯 {section}" in content or f"## 🔧 {section}" in content:
                                validation_score += 10
                            else:
                                validation_errors.append(f"Missing required section: {section}")
                    else:
                        # Python syntax validation (if any Python agents remain)
                        compile(content, metadata.path, 'exec')
                        validation_score += 20  # Valid syntax
                except SyntaxError as e:
                    validation_errors.append(f"Syntax error: {e}")
                    validation_score -= 10
                except Exception as e:
                    validation_errors.append(f"Content error: {e}")
                
                # Enhanced validation for specialized agents
                validation_score += self._validate_specialized_agent(metadata, content)
                
                # Hybrid agent validation
                if metadata.is_hybrid:
                    validation_score += self._validate_hybrid_agent(metadata)
                
                # Capability consistency validation
                validation_score += self._validate_capability_consistency(metadata)
                
                # Framework compatibility validation
                validation_score += self._validate_framework_compatibility(metadata)
                
                # Set validation results
                metadata.validation_score = max(0.0, min(100.0, validation_score))
                metadata.validated = validation_score >= 50.0  # 50% threshold
                
                if validation_errors:
                    metadata.error_message = "; ".join(validation_errors)
                else:
                    metadata.error_message = None
                
                validated[name] = metadata
                
            except Exception as e:
                logger.warning(f"Validation error for agent {name}: {e}")
                metadata.validated = False
                metadata.error_message = str(e)
                metadata.validation_score = 0.0
                validated[name] = metadata
        
        return validated
    
    def _validate_specialized_agent(self, metadata: AgentMetadata, content: str) -> float:
        """
        Validate specialized agent requirements and capabilities.
        
        Args:
            metadata: Agent metadata
            content: Agent file content
            
        Returns:
            Validation score contribution
        """
        score = 0.0
        
        # Validate specialization alignment
        if metadata.specializations:
            score += 15  # Has specializations
            
            # Check if specializations align with agent type
            type_alignment = any(spec.lower() in metadata.type.lower() or 
                               metadata.type.lower() in spec.lower() 
                               for spec in metadata.specializations)
            if type_alignment:
                score += 10
        
        # Validate framework usage
        if metadata.frameworks:
            score += 10  # Uses frameworks
            
            # Check for proper import statements
            for framework in metadata.frameworks:
                if framework.lower() in content.lower():
                    score += 2  # Framework properly imported
        
        # Validate domain expertise
        if metadata.domains:
            score += 8  # Has domain expertise
        
        # Validate role definitions
        if metadata.roles:
            score += 7  # Has defined roles
        
        return score
    
    def _validate_hybrid_agent(self, metadata: AgentMetadata) -> float:
        """
        Validate hybrid agent configuration.
        
        Args:
            metadata: Agent metadata
            
        Returns:
            Validation score contribution
        """
        score = 0.0
        
        if metadata.is_hybrid and metadata.hybrid_types:
            # Bonus for being hybrid
            score += 5
            
            # Validate hybrid type consistency
            if len(metadata.hybrid_types) >= 2:
                score += 10  # Valid hybrid combination
            
            # Check for capability coverage across types
            type_coverage = len(set(metadata.hybrid_types))
            score += type_coverage * 2  # Coverage bonus
        
        return score
    
    def _validate_capability_consistency(self, metadata: AgentMetadata) -> float:
        """
        Validate capability consistency with agent type and specializations.
        
        Args:
            metadata: Agent metadata
            
        Returns:
            Validation score contribution
        """
        score = 0.0
        
        # Basic capability validation
        if metadata.capabilities:
            score += len(metadata.capabilities) * 0.5  # Base capability score
            
            # Check for consistent naming
            consistent_caps = sum(1 for cap in metadata.capabilities 
                                if not cap.startswith('_'))
            score += consistent_caps * 0.3
        
        # Validate complexity assessment
        complexity_levels = ['basic', 'intermediate', 'advanced', 'expert']
        if metadata.complexity_level in complexity_levels:
            score += 5
            
            # Bonus for higher complexity with sufficient capabilities
            complexity_index = complexity_levels.index(metadata.complexity_level)
            expected_caps = (complexity_index + 1) * 5
            if len(metadata.capabilities) >= expected_caps:
                score += 5
        
        return score
    
    def _validate_framework_compatibility(self, metadata: AgentMetadata) -> float:
        """
        Validate framework compatibility and integration.
        
        Args:
            metadata: Agent metadata
            
        Returns:
            Validation score contribution
        """
        score = 0.0
        
        if metadata.frameworks:
            # Validate framework combinations
            for framework in metadata.frameworks:
                if framework in COMPATIBLE_COMBINATIONS:
                    compatible_techs = COMPATIBLE_COMBINATIONS[framework]
                    compatibility_score = sum(1 for tech in compatible_techs 
                                            if any(tech in cap.lower() for cap in metadata.capabilities))
                    score += compatibility_score * 2
        
        return score