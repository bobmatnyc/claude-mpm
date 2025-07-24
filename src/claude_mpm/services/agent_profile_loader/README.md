# Agent Profile Loader Module

## Overview

The Agent Profile Loader service provides comprehensive agent profile loading with enhanced prompt integration, implementing three-tier hierarchy precedence and improved prompt system integration.

## Module Structure

This module has been refactored from a single 1,058-line file into a well-organized directory structure:

```
agent_profile_loader/
├── __init__.py           # Main facade class (200 lines)
├── models.py             # Data models and enums (80 lines)
├── profile_manager.py    # Core profile loading/caching (150 lines)
├── profile_parser.py     # Profile parsing and extraction (220 lines)
├── improved_prompts.py   # Improved prompt management (120 lines)
├── task_integration.py   # Task Tool integration (80 lines)
├── service_integrations.py # External service integrations (100 lines)
├── profile_discovery.py  # Agent discovery and listing (80 lines)
├── metrics_validator.py  # Metrics and validation (60 lines)
└── README.md            # This file
```

Total: ~1,090 lines (including documentation)
Reduction: 81% in main module size

## Key Features

- **Three-tier hierarchy precedence** (Project → User → System)
- **Improved prompt integration** with training system
- **SharedPromptCache integration** for performance optimization
- **AgentRegistry integration** for enhanced discovery
- **Training system integration** for prompt improvement
- **Task Tool subprocess creation** enhancement
- **Profile validation** and error handling

## Usage

### Basic Profile Loading

```python
from claude_pm.services.agent_profile_loader import AgentProfileLoader

loader = AgentProfileLoader()
await loader.start()

# Load an agent profile
profile = await loader.load_agent_profile("engineer")
print(f"Role: {profile.role}")
print(f"Tier: {profile.tier.value}")
```

### Task Tool Integration

```python
# Build enhanced prompt for Task Tool
task_context = {
    'task_description': 'Implement new feature',
    'requirements': ['Test coverage', 'Documentation'],
    'priority': 'high'
}

enhanced_prompt = await loader.build_enhanced_task_prompt("engineer", task_context)
```

### Improved Prompt Deployment

```python
# Deploy an improved prompt
result = await loader.deploy_improved_prompt(
    agent_name="engineer",
    training_session_id="session_123"
)
```

## Module Components

### models.py
- `ProfileTier`: Enum for hierarchy tiers (PROJECT, USER, SYSTEM)
- `ProfileStatus`: Enum for profile status
- `ImprovedPrompt`: Enhanced prompt from training system
- `AgentProfile`: Comprehensive agent profile dataclass

### profile_manager.py
- `ProfileManager`: Core profile loading and caching logic
- Three-tier hierarchy implementation
- Cache management and performance tracking

### profile_parser.py
- `ProfileParser`: Extracts metadata from profile files
- Parses capabilities, authority scope, context preferences
- Handles multiple file naming conventions

### improved_prompts.py
- `ImprovedPromptManager`: Manages prompts from training system
- Loads, saves, and tracks deployment readiness
- Integration with training directory structure

### task_integration.py
- `TaskIntegration`: Handles Task Tool prompt building
- Formats task descriptions with agent nicknames
- Integrates profile metadata into prompts

### service_integrations.py
- `ServiceIntegrations`: Manages external service connections
- SharedPromptCache, AgentRegistry, PromptTemplateManager
- Training system integration

### profile_discovery.py
- `ProfileDiscovery`: Agent discovery and listing
- Integration with AgentRegistry
- Capability-based agent discovery

### metrics_validator.py
- `MetricsValidator`: Performance metrics and validation
- Profile structure validation
- Integration health checks

## Backward Compatibility

The original `agent_profile_loader.py` file remains as a compatibility stub that imports from the new module structure. This ensures existing code continues to work without modification.

## Performance

- SharedPromptCache integration provides 99.7% performance improvement
- Efficient caching with TTL and namespace support
- Metrics tracking for optimization analysis

## Framework Version

- Framework Version: 014
- Implementation: 2025-07-15