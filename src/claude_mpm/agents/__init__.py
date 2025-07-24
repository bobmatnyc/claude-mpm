"""
Claude PM Framework Agents Package

System-level agent implementations with Task Tool integration.
These agents provide specialized prompts and capabilities for PM orchestration.

Uses unified agent loader to load prompts from framework/agent-roles/*.md files
with fallback to Python constants for backward compatibility.
"""

# Import from unified agent loader
from .agent_loader import (
    get_documentation_agent_prompt,
    get_version_control_agent_prompt,
    get_qa_agent_prompt,
    get_research_agent_prompt,
    get_ops_agent_prompt,
    get_security_agent_prompt,
    get_engineer_agent_prompt,
    get_data_engineer_agent_prompt,
    list_available_agents,
    clear_agent_cache,
    validate_agent_files
)

# Import agent metadata (previously AGENT_CONFIG)
from .agents_metadata import (
    DOCUMENTATION_CONFIG,
    VERSION_CONTROL_CONFIG,
    QA_CONFIG,
    RESEARCH_CONFIG,
    OPS_CONFIG,
    SECURITY_CONFIG,
    ENGINEER_CONFIG,
    DATA_ENGINEER_CONFIG,
    ALL_AGENT_CONFIGS
)

# Available system agents
__all__ = [
    # Agent prompt functions
    'get_documentation_agent_prompt',
    'get_version_control_agent_prompt',
    'get_qa_agent_prompt',
    'get_research_agent_prompt',
    'get_ops_agent_prompt',
    'get_security_agent_prompt',
    'get_engineer_agent_prompt',
    'get_data_engineer_agent_prompt',
    # Agent utility functions
    'list_available_agents',
    'clear_agent_cache',
    'validate_agent_files',
    # Agent configs
    'DOCUMENTATION_CONFIG',
    'VERSION_CONTROL_CONFIG',
    'QA_CONFIG',
    'RESEARCH_CONFIG',
    'OPS_CONFIG',
    'SECURITY_CONFIG',
    'ENGINEER_CONFIG',
    'DATA_ENGINEER_CONFIG',
    'ALL_AGENT_CONFIGS',
    # System registry
    'SYSTEM_AGENTS'
]

# System agent registry
SYSTEM_AGENTS = {
    'documentation': {
        'prompt_function': get_documentation_agent_prompt,
        'config': DOCUMENTATION_CONFIG,
        'version': '2.0.0',
        'integration': 'claude_pm_framework'
    },
    'version_control': {
        'prompt_function': get_version_control_agent_prompt,
        'config': VERSION_CONTROL_CONFIG,
        'version': '2.0.0',
        'integration': 'claude_pm_framework'
    },
    'qa': {
        'prompt_function': get_qa_agent_prompt,
        'config': QA_CONFIG,
        'version': '2.0.0',
        'integration': 'claude_pm_framework'
    },
    'research': {
        'prompt_function': get_research_agent_prompt,
        'config': RESEARCH_CONFIG,
        'version': '2.0.0',
        'integration': 'claude_pm_framework'
    },
    'ops': {
        'prompt_function': get_ops_agent_prompt,
        'config': OPS_CONFIG,
        'version': '2.0.0',
        'integration': 'claude_pm_framework'
    },
    'security': {
        'prompt_function': get_security_agent_prompt,
        'config': SECURITY_CONFIG,
        'version': '2.0.0',
        'integration': 'claude_pm_framework'
    },
    'engineer': {
        'prompt_function': get_engineer_agent_prompt,
        'config': ENGINEER_CONFIG,
        'version': '2.0.0',
        'integration': 'claude_pm_framework'
    },
    'data_engineer': {
        'prompt_function': get_data_engineer_agent_prompt,
        'config': DATA_ENGINEER_CONFIG,
        'version': '2.0.0',
        'integration': 'claude_pm_framework'
    }
}
