"""
Ollama Model Provider Implementation for Claude MPM Framework
=============================================================

WHY: Enables local model execution via Ollama for privacy-sensitive content
analysis. Provides cost-effective alternative to cloud APIs with full control
over model selection and hosting.

DESIGN DECISION: Uses direct HTTP API calls to Ollama service rather than
heavyweight LangChain dependency. Keeps implementation lightweight and focused.

ARCHITECTURE:
- Direct integration with Ollama API (http://localhost:11434 by default)
- Task-specific model mapping based on research recommendations
- Automatic model availability checking and validation
- Graceful degradation when Ollama not available

RECOMMENDED MODELS (from research):
- SEO Analysis: llama3.3:70b (comprehensive analysis)
- Readability: gemma2:9b (fast, accurate)
- Grammar: qwen3:14b (specialized for grammar)
- Summarization: mistral:7b (concise summaries)
- Keyword Extraction: seoassistant (specialized SEO tool)
- General: gemma2:9b (good default balance)
"""

import asyncio
from typing import Any, Dict, List, Optional

import aiohttp

from claude_mpm.services.core.interfaces.model import ModelCapability, ModelResponse
from claude_mpm.services.model.base_provider import BaseModelProvider


class OllamaProvider(BaseModelProvider):
    """
    Ollama local model provider.

    WHY: Provides privacy-preserving local content analysis without sending
    data to cloud services. Cost-effective for high-volume processing.

    Configuration:
        host: Ollama API endpoint (default: http://localhost:11434)
        timeout: Request timeout in seconds (default: 30)
        models: Dict mapping capabilities to model names (optional)

    Usage:
        provider = OllamaProvider(config={
            "host": "http://localhost:11434",
            "models": {
                "seo_analysis": "llama3.3:70b"
            }
        })

        if await provider.is_available():
            response = await provider.analyze_content(
                content="Your content",
                task=ModelCapability.SEO_ANALYSIS
            )
    """

    # Default model mappings based on research recommendations
    DEFAULT_MODELS: Dict[ModelCapability, str] = {
        ModelCapability.SEO_ANALYSIS: "llama3.3:70b",
        ModelCapability.READABILITY: "gemma2:9b",
        ModelCapability.GRAMMAR: "qwen3:14b",
        ModelCapability.SUMMARIZATION: "mistral:7b",
        ModelCapability.KEYWORD_EXTRACTION: "seoassistant",
        ModelCapability.ACCESSIBILITY: "gemma2:9b",
        ModelCapability.SENTIMENT: "gemma2:9b",
        ModelCapability.GENERAL: "gemma2:9b",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Ollama provider.

        Args:
            config: Configuration dict with:
                - host: Ollama API endpoint
                - timeout: Request timeout in seconds
                - models: Custom model mappings
        """
        super().__init__(provider_name="ollama", config=config or {})

        self.host = self.get_config("host", "http://localhost:11434")
        self.timeout = self.get_config("timeout", 30)

        # Merge custom models with defaults
        custom_models = self.get_config("models", {})
        self.model_mapping = self.DEFAULT_MODELS.copy()
        if custom_models:
            # Convert string keys to ModelCapability if needed
            for key, value in custom_models.items():
                if isinstance(key, str):
                    try:
                        capability = ModelCapability(key)
                        self.model_mapping[capability] = value
                    except ValueError:
                        self.log_warning(f"Unknown capability in config: {key}")
                else:
                    self.model_mapping[key] = value

        self._session: Optional[aiohttp.ClientSession] = None
        self._available_models: List[str] = []

    async def initialize(self) -> bool:
        """
        Initialize Ollama provider.

        Returns:
            True if initialization successful
        """
        self.log_info(f"Initializing Ollama provider at {self.host}")

        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)

        # Check availability
        if not await self.is_available():
            self.log_warning("Ollama service not available")
            self._initialized = False
            return False

        # Fetch available models
        self._available_models = await self.get_available_models()
        self.log_info(f"Found {len(self._available_models)} available models")

        self._initialized = True
        return True

    async def shutdown(self) -> None:
        """Shutdown provider and cleanup resources."""
        self.log_info("Shutting down Ollama provider")

        if self._session and not self._session.closed:
            await self._session.close()

        self._shutdown = True

    async def is_available(self) -> bool:
        """
        Check if Ollama service is available.

        WHY: Enables auto-fallback routing. Returns False if service
        is not running or unreachable.

        Returns:
            True if Ollama is reachable and functional
        """
        try:
            # Ensure we have a session
            if not self._session or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=5)
                self._session = aiohttp.ClientSession(timeout=timeout)

            # Try to fetch tags (models list)
            async with self._session.get(f"{self.host}/api/tags") as response:
                if response.status == 200:
                    return True
                self.log_warning(f"Ollama returned status {response.status}")
                return False

        except aiohttp.ClientError as e:
            self.log_debug(f"Ollama not available: {e}")
            return False
        except Exception as e:
            self.log_warning(f"Error checking Ollama availability: {e}")
            return False

    async def get_available_models(self) -> List[str]:
        """
        List available models from Ollama.

        Returns:
            List of model names (e.g., ["llama3.3:70b", "gemma2:9b"])
        """
        try:
            if not self._session or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=5)
                self._session = aiohttp.ClientSession(timeout=timeout)

            async with self._session.get(f"{self.host}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return [model["name"] for model in data.get("models", [])]
                self.log_error(f"Failed to fetch models: status {response.status}")
                return []

        except Exception as e:
            self.log_error(f"Error fetching available models: {e}")
            return []

    def get_supported_capabilities(self) -> List[ModelCapability]:
        """
        Return all supported capabilities.

        WHY: Ollama supports all capabilities, routing to different models.

        Returns:
            List of all ModelCapability values
        """
        return list(ModelCapability)

    def _get_model_for_task(self, task: ModelCapability) -> str:
        """
        Get optimal model for task.

        Args:
            task: Task capability

        Returns:
            Model name from mapping
        """
        return self.model_mapping.get(
            task, self.DEFAULT_MODELS[ModelCapability.GENERAL]
        )

    async def analyze_content(
        self,
        content: str,
        task: ModelCapability,
        model: Optional[str] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Analyze content using Ollama model.

        Args:
            content: Text content to analyze
            task: Type of analysis
            model: Optional specific model (overrides task mapping)
            **kwargs: Additional options:
                - temperature: Sampling temperature (0.0-1.0)
                - max_tokens: Maximum response tokens
                - stream: Enable streaming (not yet implemented)

        Returns:
            ModelResponse with analysis results
        """
        # Validate content
        if not self.validate_content(content, max_length=100000):
            return self.create_response(
                success=False,
                model=model or "unknown",
                task=task,
                error="Invalid content provided",
            )

        # Check if initialized
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            return self.create_response(
                success=False,
                model=model or "unknown",
                task=task,
                error="Ollama provider not initialized",
            )

        # Select model
        selected_model = model or self._get_model_for_task(task)

        # Check if model is available
        if selected_model not in self._available_models:
            self.log_warning(
                f"Model {selected_model} not found. "
                f"Available: {', '.join(self._available_models[:5])}..."
            )
            return self.create_response(
                success=False,
                model=selected_model,
                task=task,
                error=f"Model {selected_model} not available in Ollama",
            )

        # Generate prompt
        prompt = self.get_task_prompt(task, content)

        # Call Ollama API with retry logic
        return await self.analyze_with_retry(
            self._call_ollama,
            prompt,
            task,
            selected_model,
            **kwargs,
        )

    async def _call_ollama(
        self,
        prompt: str,
        task: ModelCapability,
        model: str,
        **kwargs,
    ) -> ModelResponse:
        """
        Internal method to call Ollama API.

        Args:
            prompt: Generated prompt
            task: Task capability
            model: Model to use
            **kwargs: Additional options

        Returns:
            ModelResponse
        """
        try:
            # Prepare request
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,  # TODO: Implement streaming
                "options": {},
            }

            # Add optional parameters
            if "temperature" in kwargs:
                payload["options"]["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                payload["options"]["num_predict"] = kwargs["max_tokens"]

            # Make request
            async with self._session.post(
                f"{self.host}/api/generate",
                json=payload,
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result_text = data.get("response", "")

                    # Extract metadata
                    metadata = {
                        "model": model,
                        "total_duration": data.get("total_duration", 0)
                        / 1e9,  # ns to s
                        "load_duration": data.get("load_duration", 0) / 1e9,
                        "prompt_eval_count": data.get("prompt_eval_count", 0),
                        "eval_count": data.get("eval_count", 0),
                    }

                    return self.create_response(
                        success=True,
                        model=model,
                        task=task,
                        result=result_text,
                        metadata=metadata,
                    )
                error_text = await response.text()
                return self.create_response(
                    success=False,
                    model=model,
                    task=task,
                    error=f"Ollama API error {response.status}: {error_text}",
                )

        except asyncio.TimeoutError:
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error=f"Request timeout after {self.timeout}s",
            )
        except Exception as e:
            return self.create_response(
                success=False,
                model=model,
                task=task,
                error=f"Request failed: {e!s}",
            )

    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get detailed information about a model.

        Args:
            model: Model name

        Returns:
            Dictionary with model information
        """
        try:
            if not self._session or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=5)
                self._session = aiohttp.ClientSession(timeout=timeout)

            async with self._session.post(
                f"{self.host}/api/show",
                json={"name": model},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "name": model,
                        "modelfile": data.get("modelfile", ""),
                        "parameters": data.get("parameters", ""),
                        "template": data.get("template", ""),
                        "details": data.get("details", {}),
                    }
                return {
                    "name": model,
                    "error": f"Status {response.status}",
                }

        except Exception as e:
            return {
                "name": model,
                "error": str(e),
            }


__all__ = ["OllamaProvider"]
