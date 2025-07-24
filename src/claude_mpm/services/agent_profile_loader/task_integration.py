"""
Task Tool integration functionality.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from .models import AgentProfile

logger = logging.getLogger(__name__)


class TaskIntegration:
    """Handles Task Tool integration for agent profiles."""
    
    async def build_enhanced_task_prompt(self, profile: AgentProfile, task_context: Dict[str, Any]) -> str:
        """Build enhanced Task Tool prompt with improved prompt integration."""
        try:
            # Get effective prompt (improved or original)
            effective_prompt = profile.get_effective_prompt()
            
            # Build enhanced prompt
            enhanced_prompt = f"""**{profile.nickname}**: {task_context.get('task_description', 'Task execution')}

TEMPORAL CONTEXT: Today is {datetime.now().strftime('%B %d, %Y')}. Apply date awareness to task execution.

**Enhanced Agent Profile Integration**: 
- **Role**: {profile.role}
- **Tier**: {profile.tier.value.title()} ({profile.path.parent.name})
- **Profile ID**: {profile.profile_id}
- **Status**: {profile.status.value}
- **Prompt Version**: {profile.prompt_version}
- **Training Enhanced**: {'Yes' if profile.has_improved_prompt else 'No'}

**Core Capabilities**:
{chr(10).join(f"- {cap}" for cap in profile.capabilities[:5])}

**Authority Scope**:
{chr(10).join(f"- {auth}" for auth in profile.authority_scope[:4])}

**Task Requirements**:
{chr(10).join(f"- {req}" for req in task_context.get('requirements', []))}

**Context Preferences**:
{chr(10).join(f"- {key.replace('_', ' ').title()}: {value}" for key, value in profile.context_preferences.items())}

**Quality Standards**:
{chr(10).join(f"- {std}" for std in profile.quality_standards[:3])}

**Integration Patterns**:
{chr(10).join(f"- With {agent.title()}: {desc}" for agent, desc in profile.integration_patterns.items())}

**Enhanced Prompt Context**:
{effective_prompt}

**Authority**: {profile.role} operations with enhanced prompt integration
**Priority**: {task_context.get('priority', 'medium')}
**Framework Integration**: AgentProfileLoader with improved prompt system (99.7% performance optimization)

**Profile-Enhanced Context**: This subprocess operates with enhanced context from {profile.tier.value}-tier agent profile, providing specialized knowledge, improved prompt integration, and performance optimization for optimal task execution.
"""
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Error building enhanced task prompt: {e}")
            raise
    
    def format_task_description(self, profile: AgentProfile, task: str) -> str:
        """Format task description with agent nickname."""
        return f"**{profile.nickname}**: {task}"
    
    def extract_task_requirements(self, task_context: Dict[str, Any]) -> list:
        """Extract and format task requirements."""
        requirements = task_context.get('requirements', [])
        if isinstance(requirements, str):
            requirements = [req.strip() for req in requirements.split(',')]
        return requirements[:5]  # Limit to top 5 requirements