"""
Profile parsing and extraction functionality.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import ProfileTier, ProfileStatus, AgentProfile

logger = logging.getLogger(__name__)


class ProfileParser:
    """Parses agent profile files and extracts metadata."""
    
    async def parse_profile_file(self, profile_path: Path, tier: ProfileTier) -> AgentProfile:
        """Parse agent profile file with enhanced metadata extraction."""
        try:
            content = profile_path.read_text(encoding='utf-8')
            
            # Extract profile metadata
            name = self._extract_agent_name(profile_path.stem)
            role = self._extract_role(content)
            capabilities = self._extract_capabilities(content)
            authority_scope = self._extract_authority_scope(content)
            context_preferences = self._extract_context_preferences(content)
            escalation_criteria = self._extract_escalation_criteria(content)
            integration_patterns = self._extract_integration_patterns(content)
            quality_standards = self._extract_quality_standards(content)
            communication_style = self._extract_communication_style(content)
            
            # Extract enhanced metadata
            prompt_template_id = self._extract_prompt_template_id(content)
            training_enabled = self._extract_training_enabled(content)
            
            # Get file statistics
            stat = profile_path.stat()
            
            return AgentProfile(
                name=name,
                tier=tier,
                path=profile_path,
                role=role,
                capabilities=capabilities,
                authority_scope=authority_scope,
                context_preferences=context_preferences,
                escalation_criteria=escalation_criteria,
                integration_patterns=integration_patterns,
                quality_standards=quality_standards,
                communication_style=communication_style,
                content=content,
                prompt_template_id=prompt_template_id,
                training_enabled=training_enabled,
                performance_metrics={
                    'file_size': stat.st_size,
                    'last_modified': stat.st_mtime
                },
                last_updated=datetime.fromtimestamp(stat.st_mtime)
            )
            
        except Exception as e:
            logger.error(f"Error parsing profile {profile_path}: {e}")
            raise
    
    def _extract_agent_name(self, filename: str) -> str:
        """Extract agent name from filename."""
        name = filename.lower()
        for suffix in ['-agent', '_agent', '-profile']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break
        return name
    
    def _extract_role(self, content: str) -> str:
        """Extract primary role from profile content."""
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('## Role') or line.startswith('# Role'):
                lines = content.split('\n')
                idx = lines.index(line)
                for i in range(idx + 1, len(lines)):
                    next_line = lines[i].strip()
                    if next_line and not next_line.startswith('#'):
                        return next_line
            elif line.startswith('**Role**:') or line.startswith('**Primary Role**:'):
                return line.split(':', 1)[1].strip().strip('*')
        return "Specialized Agent"
    
    def _extract_capabilities(self, content: str) -> List[str]:
        """Extract capabilities from profile content."""
        capabilities = []
        in_capabilities_section = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if any(header in line.lower() for header in ['## capabilities', '## core capabilities', 
                                                         '## responsibilities', '## functions']):
                in_capabilities_section = True
                continue
            
            if in_capabilities_section and line.startswith('##'):
                break
            
            if in_capabilities_section and line.startswith('- **'):
                capability = line[4:].split('**:')[0].strip('*')
                if capability:
                    capabilities.append(capability)
            elif in_capabilities_section and (line.startswith('- ') or line.startswith('* ')):
                capability = line[2:].strip()
                if capability and not capability.startswith('#'):
                    capabilities.append(capability)
        
        return capabilities[:10]
    
    def _extract_authority_scope(self, content: str) -> List[str]:
        """Extract authority scope from profile content."""
        authority = []
        in_authority_section = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if any(header in line.lower() for header in ['## authority', '## authority scope', 
                                                         '## permissions', '## writing']):
                in_authority_section = True
                continue
            
            if in_authority_section and line.startswith('##'):
                break
            
            if in_authority_section and line.startswith('- **'):
                auth_item = line[4:].split('**:')[0].strip('*')
                if auth_item:
                    authority.append(auth_item)
            elif in_authority_section and (line.startswith('- ') or line.startswith('* ')):
                auth_item = line[2:].strip()
                if auth_item and not auth_item.startswith('#'):
                    authority.append(auth_item)
        
        return authority[:8]
    
    def _extract_context_preferences(self, content: str) -> Dict[str, Any]:
        """Extract context preferences from profile content."""
        preferences = {}
        in_context_section = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if any(header in line.lower() for header in ['## context preferences', '## context']):
                in_context_section = True
                continue
            
            if in_context_section and line.startswith('##'):
                break
            
            if in_context_section and line.startswith('- **'):
                parts = line[4:].split('**:', 1)
                if len(parts) == 2:
                    key = parts[0].strip('*').lower().replace(' ', '_')
                    value = parts[1].strip()
                    preferences[key] = value
        
        return preferences
    
    def _extract_escalation_criteria(self, content: str) -> List[str]:
        """Extract escalation criteria from profile content."""
        criteria = []
        in_escalation_section = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if any(header in line.lower() for header in ['## escalation', '## escalation criteria']):
                in_escalation_section = True
                continue
            
            if in_escalation_section and line.startswith('##'):
                break
            
            if in_escalation_section and line.startswith('- **'):
                criterion = line[4:].split('**:')[0].strip('*')
                if criterion:
                    criteria.append(criterion)
            elif in_escalation_section and (line.startswith('- ') or line.startswith('* ')):
                criterion = line[2:].strip()
                if criterion and not criterion.startswith('#'):
                    criteria.append(criterion)
        
        return criteria[:6]
    
    def _extract_integration_patterns(self, content: str) -> Dict[str, str]:
        """Extract integration patterns from profile content."""
        patterns = {}
        in_integration_section = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if any(header in line.lower() for header in ['## integration', '## integration patterns']):
                in_integration_section = True
                continue
            
            if in_integration_section and line.startswith('##'):
                break
            
            if in_integration_section and line.startswith('- **With '):
                parts = line[9:].split('**:', 1)
                if len(parts) == 2:
                    agent = parts[0].strip().lower()
                    description = parts[1].strip()
                    patterns[agent] = description
        
        return patterns
    
    def _extract_quality_standards(self, content: str) -> List[str]:
        """Extract quality standards from profile content."""
        standards = []
        in_standards_section = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if any(header in line.lower() for header in ['## quality standards', '## quality']):
                in_standards_section = True
                continue
            
            if in_standards_section and line.startswith('##'):
                break
            
            if in_standards_section and line.startswith('- **'):
                standard = line[4:].split('**:')[0].strip('*')
                if standard:
                    standards.append(standard)
            elif in_standards_section and (line.startswith('- ') or line.startswith('* ')):
                standard = line[2:].strip()
                if standard and not standard.startswith('#'):
                    standards.append(standard)
        
        return standards[:5]
    
    def _extract_communication_style(self, content: str) -> Dict[str, str]:
        """Extract communication style from profile content."""
        style = {}
        in_communication_section = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if any(header in line.lower() for header in ['## communication', '## communication style']):
                in_communication_section = True
                continue
            
            if in_communication_section and line.startswith('##'):
                break
            
            if in_communication_section and line.startswith('- **'):
                parts = line[4:].split('**:', 1)
                if len(parts) == 2:
                    key = parts[0].strip('*').lower()
                    value = parts[1].strip()
                    style[key] = value
        
        return style
    
    def _extract_prompt_template_id(self, content: str) -> Optional[str]:
        """Extract prompt template ID from profile content."""
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('**Template ID**:'):
                return line.split(':', 1)[1].strip()
        return None
    
    def _extract_training_enabled(self, content: str) -> bool:
        """Extract training enabled flag from profile content."""
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('**Training Enabled**:'):
                return line.split(':', 1)[1].strip().lower() == 'true'
        return True  # Default to enabled