"""
Model Services Package for Claude MPM Framework
================================================

WHY: Provides hybrid local/cloud content processing with intelligent routing
and automatic fallback. Enables privacy-preserving local model execution via
Ollama with cloud fallback to Claude for reliability.

ARCHITECTURE:
- Interfaces: Core contracts for model providers and routing (IModelProvider, IModelRouter)
- Base Provider: Common functionality for all providers (BaseModelProvider)
- Providers: Ollama (local) and Claude (cloud) implementations
- Router: Intelligent routing with fallback logic (ModelRouter)
- Configuration: Centralized config management (model_config.py)

USAGE:

    Basic Usage with Auto-Routing:
    ```python
    from claude_mpm.services.model import ModelRouter
    from claude_mpm.services.core.interfaces.model import ModelCapability

    # Create router with default config (auto mode)
    router = ModelRouter()
    await router.initialize()

    # Analyze content (tries Ollama first, falls back to Claude)
    response = await router.analyze_content(
        content="Your article text here...",
        task=ModelCapability.SEO_ANALYSIS
    )

    if response.success:
        print(f"Analysis by {response.provider}:")
        print(response.result)
    ```

    Direct Provider Usage:
    ```python
    from claude_mpm.services.model import OllamaProvider

    # Use Ollama directly
    provider = OllamaProvider(config={
        "host": "http://localhost:11434"
    })

    if await provider.is_available():
        response = await provider.analyze_content(
            content="Text to analyze",
            task=ModelCapability.READABILITY
        )
    ```

    Configuration-Based Setup:
    ```python
    from claude_mpm.config.model_config import ModelConfigManager
    from claude_mpm.services.model import ModelRouter

    # Load config from file
    config = ModelConfigManager.load_config(".claude/configuration.yaml")
    router_config = ModelConfigManager.get_router_config(config)

    # Create router with loaded config
    router = ModelRouter(config=router_config)
    await router.initialize()
    ```

PROVIDER STRATEGIES:
- AUTO: Try Ollama first, fallback to Claude (default)
- OLLAMA: Local-only, fail if unavailable (privacy mode)
- CLAUDE: Cloud-only, always use Claude
- PRIVACY: Like OLLAMA with privacy-focused messages

RECOMMENDED MODELS (Ollama):
- SEO Analysis: llama3.3:70b - Comprehensive SEO insights
- Readability: gemma2:9b - Fast, accurate readability scoring
- Grammar: qwen3:14b - Specialized grammar checking
- Summarization: mistral:7b - Concise, effective summaries
- Keyword Extraction: seoassistant - SEO-specialized model

CONFIGURATION:
See claude_mpm.config.model_config for detailed configuration options.

Example configuration.yaml:
```yaml
content_agent:
  model_provider: auto

  ollama:
    enabled: true
    host: http://localhost:11434
    fallback_to_cloud: true
    models:
      seo_analysis: llama3.3:70b
      readability: gemma2:9b

  claude:
    enabled: true
    model: claude-3-5-sonnet-20241022
```

PHASE 1 STATUS (Current):
✅ Core interfaces and contracts defined
✅ Base provider with common functionality
✅ Ollama provider with direct API integration
✅ Claude provider (Phase 1: mock responses)
✅ Router with intelligent fallback logic
✅ Configuration management with validation
⏳ Claude API integration (Phase 2)
⏳ Content agent integration (Phase 2)
"""

# Re-export interfaces for convenience
from claude_mpm.services.core.interfaces.model import (
    IModelProvider,
    IModelRouter,
    ModelCapability,
    ModelProvider,
    ModelResponse,
)
from claude_mpm.services.model.base_provider import BaseModelProvider
from claude_mpm.services.model.claude_provider import ClaudeProvider
from claude_mpm.services.model.model_router import ModelRouter, RoutingStrategy
from claude_mpm.services.model.ollama_provider import OllamaProvider

__all__ = [  # noqa: RUF022 - Semantic grouping preferred over alphabetical
    # Base classes
    "BaseModelProvider",
    # Providers
    "ClaudeProvider",
    "OllamaProvider",
    # Router
    "ModelRouter",
    "RoutingStrategy",
    # Interfaces
    "IModelProvider",
    "IModelRouter",
    # Data types
    "ModelCapability",
    "ModelProvider",
    "ModelResponse",
]

# Version and metadata
__version__ = "1.0.0"
__phase__ = "1"
__status__ = "Core Infrastructure Complete"
