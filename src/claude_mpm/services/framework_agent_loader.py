"""
Framework Agent Loader Service

Implements agent profile loading logic based on directory hierarchy:
1. Framework .claude-pm (next to agents/INSTRUCTIONS.md or CLAUDE.md): system, trained, user agents
2. Project .claude-pm (in project root): project agents

Loading precedence: Project → Framework (user → trained → system)
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class FrameworkAgentLoader:
    """Loads agent profiles from framework and project .claude-pm directories"""
    
    def __init__(self):
        self.framework_agents_dir = None
        self.project_agents_dir = None
        self._profile_cache = {}
        
    def initialize(self, framework_claude_md_path: Optional[str] = None):
        """
        Initialize loader with framework and project directory detection
        
        Args:
            framework_claude_md_path: Optional explicit path to agents/INSTRUCTIONS.md or CLAUDE.md
        """
        # Find framework .claude-pm directory (next to framework/CLAUDE.md)
        if framework_claude_md_path:
            framework_dir = Path(framework_claude_md_path).parent.parent
        else:
            framework_dir = self._find_framework_directory()
            
        if framework_dir:
            self.framework_agents_dir = framework_dir / ".claude-pm" / "agents"
            logger.info(f"Framework agents directory: {self.framework_agents_dir}")
        
        # Find project .claude-pm directory
        project_dir = self._find_project_directory()
        if project_dir:
            self.project_agents_dir = project_dir / ".claude-pm" / "agents"
            logger.info(f"Project agents directory: {self.project_agents_dir}")
    
    def _find_framework_directory(self) -> Optional[Path]:
        """Find directory containing agents/INSTRUCTIONS.md (or legacy CLAUDE.md)"""
        # Check if we're running from a wheel installation
        try:
            import claude_pm
            package_path = Path(claude_pm.__file__).parent
            path_str = str(package_path.resolve())
            if 'site-packages' in path_str or 'dist-packages' in path_str:
                # For wheel installations, check data directory
                data_instructions = package_path / "data" / "agents" / "INSTRUCTIONS.md"
                data_claude = package_path / "data" / "agents" / "CLAUDE.md"
                if data_instructions.exists() or data_claude.exists():
                    return package_path / "data"
        except Exception:
            pass
        
        current = Path.cwd()
        
        # Check current directory and parents
        for path in [current] + list(current.parents):
            framework_instructions = path / "agents" / "INSTRUCTIONS.md"
            framework_claude = path / "agents" / "CLAUDE.md"  # Legacy
            if framework_instructions.exists() or framework_claude.exists():
                return path
                
        return None
    
    def _find_project_directory(self) -> Optional[Path]:
        """Find project directory containing .claude-pm"""
        current = Path.cwd()
        
        # Check current directory and parents for .claude-pm
        for path in [current] + list(current.parents):
            claude_pm_dir = path / ".claude-pm"
            if claude_pm_dir.exists():
                return path
                
        return None
    
    def load_agent_profile(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """
        Load agent profile with precedence: Project → Framework (user → trained → system)
        
        Args:
            agent_type: Agent type (Engineer, Documenter, QA, etc.)
            
        Returns:
            Agent profile dictionary or None if not found
        """
        # Check cache first
        cache_key = agent_type.lower()
        if cache_key in self._profile_cache:
            return self._profile_cache[cache_key]
        
        profile = None
        
        # 1. Try project agents first (highest precedence)
        if self.project_agents_dir:
            profile = self._load_profile_from_directory(
                self.project_agents_dir / "project", agent_type
            )
        
        # 2. Try framework agents (user → trained → system)
        if not profile and self.framework_agents_dir:
            # Framework user agents
            profile = self._load_profile_from_directory(
                self.framework_agents_dir / "user", agent_type
            )
            
            # Framework trained agents
            if not profile:
                profile = self._load_profile_from_directory(
                    self.framework_agents_dir / "trained", agent_type
                )
            
            # Framework system agents (fallback)
            if not profile:
                profile = self._load_profile_from_directory(
                    self.framework_agents_dir / "system", agent_type
                )
        
        # Cache result
        if profile:
            self._profile_cache[cache_key] = profile
            
        return profile
    
    def _load_profile_from_directory(self, directory: Path, agent_type: str) -> Optional[Dict[str, Any]]:
        """Load agent profile from specific directory"""
        if not directory.exists():
            return None
            
        profile_file = directory / f"{agent_type}.md"
        if not profile_file.exists():
            return None
            
        try:
            content = profile_file.read_text(encoding='utf-8')
            return self._parse_agent_profile(content, str(profile_file))
        except Exception as e:
            logger.error(f"Error loading profile {profile_file}: {e}")
            return None
    
    def _parse_agent_profile(self, content: str, source_path: str) -> Dict[str, Any]:
        """Parse agent profile markdown into structured data"""
        profile = {
            'source_path': source_path,
            'raw_content': content,
            'role': '',
            'capabilities': [],
            'context_preferences': {},
            'authority_scope': [],
            'quality_standards': [],
            'escalation_criteria': [],
            'integration_patterns': {}
        }
        
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            
            # Detect sections
            if line.startswith('## Role'):
                # Process previous section
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = 'role'
                current_content = []
            elif line.startswith('## Capabilities'):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = 'capabilities'
                current_content = []
            elif line.startswith('## Context Preferences'):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = 'context_preferences'
                current_content = []
            elif line.startswith('## Authority Scope'):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = 'authority_scope'
                current_content = []
            elif line.startswith('## Quality Standards'):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = 'quality_standards'
                current_content = []
            elif line.startswith('## Escalation Criteria'):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = 'escalation_criteria'
                current_content = []
            elif line.startswith('## Integration Patterns'):
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = 'integration_patterns'
                current_content = []
            elif line.startswith('#'):
                # Process previous section before starting new one
                if current_section and current_content:
                    self._process_section(profile, current_section, current_content)
                current_section = None
                current_content = []
            elif current_section and line:
                current_content.append(line)
        
        # Process final section
        if current_section and current_content:
            self._process_section(profile, current_section, current_content)
            
        return profile
    
    def _process_section(self, profile: Dict[str, Any], section: str, content: list):
        """Process section content into profile structure"""
        text = '\n'.join(content).strip()
        
        if section == 'role':
            profile['role'] = text
        elif section == 'capabilities':
            # Extract bullet points
            capabilities = []
            for line in content:
                if line.startswith('- **') and '**:' in line:
                    cap = line.split('**:')[0].replace('- **', '').strip()
                    capabilities.append(cap)
            profile['capabilities'] = capabilities
        elif section == 'context_preferences':
            # Extract Include/Exclude/Focus
            prefs = {}
            for line in content:
                if line.startswith('- **Include**:'):
                    prefs['include'] = line.replace('- **Include**:', '').strip()
                elif line.startswith('- **Exclude**:'):
                    prefs['exclude'] = line.replace('- **Exclude**:', '').strip()
                elif line.startswith('- **Focus**:'):
                    prefs['focus'] = line.replace('- **Focus**:', '').strip()
            profile['context_preferences'] = prefs
        elif section in ['authority_scope', 'quality_standards', 'escalation_criteria']:
            # Extract bullet points
            items = []
            for line in content:
                if line.startswith('- **') and '**:' in line:
                    item = line.split('**:')[0].replace('- **', '').strip()
                    items.append(item)
            profile[section] = items
        elif section == 'integration_patterns':
            # Extract With X: patterns
            patterns = {}
            for line in content:
                if line.startswith('- **With ') and '**:' in line:
                    agent = line.split('**:')[0].replace('- **With ', '').replace('**', '').strip()
                    desc = line.split('**:')[1].strip()
                    patterns[agent] = desc
            profile['integration_patterns'] = patterns
    
    def get_available_agents(self) -> Dict[str, list]:
        """Get list of available agents by tier"""
        agents = {
            'project': [],
            'framework_user': [],
            'framework_trained': [],
            'framework_system': []
        }
        
        # Project agents
        if self.project_agents_dir:
            project_dir = self.project_agents_dir / "project"
            if project_dir.exists():
                agents['project'] = [f.stem for f in project_dir.glob("*.md")]
        
        # Framework agents
        if self.framework_agents_dir:
            for tier in ['user', 'trained', 'system']:
                tier_dir = self.framework_agents_dir / tier
                if tier_dir.exists():
                    agents[f'framework_{tier}'] = [f.stem for f in tier_dir.glob("*.md")]
        
        return agents
    
    def generate_profile_loading_instruction(self, agent_type: str) -> str:
        """Generate instruction for subprocess to load its own profile"""
        profile = self.load_agent_profile(agent_type)
        
        if not profile:
            return f"""
**{agent_type} Agent**: No profile found. Operating with basic capabilities.

**Task Context**: Please proceed with the assigned task using standard practices.
"""
        
        instruction = f"""
**{agent_type} Agent Profile Loaded**

**Agent Identity**: {agent_type} Agent
**Profile Source**: {profile.get('source_path', 'Unknown')}
**Primary Role**: {profile.get('role', 'Not specified')}

**Core Capabilities**:
"""
        
        for capability in profile.get('capabilities', [])[:5]:  # Top 5 capabilities
            instruction += f"- **{capability}**: Primary capability area\n"
        
        instruction += f"""
**Context Preferences**:
- **Include**: {profile.get('context_preferences', {}).get('include', 'Not specified')}
- **Exclude**: {profile.get('context_preferences', {}).get('exclude', 'Not specified')}
- **Focus**: {profile.get('context_preferences', {}).get('focus', 'Not specified')}

**Authority Scope**:
"""
        
        for authority in profile.get('authority_scope', [])[:3]:  # Top 3 authorities
            instruction += f"- **{authority}**: Authorized operation area\n"
        
        instruction += f"""
**Quality Standards**: {len(profile.get('quality_standards', []))} standards defined
**Escalation Triggers**: {len(profile.get('escalation_criteria', []))} criteria defined
**Integration Partners**: {len(profile.get('integration_patterns', {}))} agent coordination patterns

Please operate according to your profile specifications and maintain quality standards.
"""
        
        return instruction.strip()