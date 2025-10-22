# Auto-Configuration Architecture

**Version**: 4.10.0+
**Last Updated**: 2025-10-21

## Overview

The Auto-Configuration feature is a comprehensive system for automatically detecting project toolchains and recommending appropriate agents. It implements a service-oriented architecture with multiple phases, utilizing Strategy and Observer design patterns.

### Design Goals

1. **Extensibility**: Easy to add new languages and frameworks
2. **Reliability**: High-confidence detection with evidence tracking
3. **Performance**: Caching and lazy loading for efficiency
4. **Maintainability**: Clear separation of concerns
5. **Testability**: Comprehensive test coverage (207 tests, 76% coverage)

### Architecture Principles

- **Service-Oriented**: Five specialized services with clear responsibilities
- **Interface-Based**: All services implement explicit interfaces
- **Dependency Injection**: Loose coupling through constructor injection
- **Strategy Pattern**: Pluggable detection strategies per language
- **Observer Pattern**: Progress tracking during deployment

## Five-Phase Architecture

The auto-configuration system was built incrementally across five phases:

### Phase 1: Interfaces and Data Models

**Objective**: Establish contracts and data structures

**Components:**
- `IToolchainAnalyzer` - Interface for toolchain detection
- `IAgentRecommender` - Interface for agent recommendation
- `IAutoConfigManager` - Interface for orchestration
- Data models: `ToolchainAnalysis`, `AgentRecommendation`, `ConfigurationResult`

**Location**: `/src/claude_mpm/services/core/`
- `interfaces/project.py` - Toolchain analyzer interface
- `interfaces/agents.py` - Recommender and manager interfaces
- `models/toolchain.py` - Toolchain data models
- `models/agent_config.py` - Configuration data models

### Phase 2: Toolchain Detection

**Objective**: Detect languages, frameworks, and deployment targets

**Components:**
- `ToolchainAnalyzerService` - Orchestrates detection strategies
- `IToolchainDetectionStrategy` - Interface for language-specific detection
- Language strategies: Python, Node.js, Rust, Go
- Evidence-based confidence scoring

**Location**: `/src/claude_mpm/services/project/`
- `toolchain_analyzer.py` - Main analyzer service
- `detection_strategies/` - Language-specific strategies
  - `python_strategy.py` - Python detection
  - `nodejs_strategy.py` - Node.js detection
  - `rust_strategy.py` - Rust detection
  - `go_strategy.py` - Go detection

### Phase 3: Agent Recommendation Engine

**Objective**: Map detected toolchain to appropriate agents

**Components:**
- `AgentRecommenderService` - Recommends agents based on toolchain
- Confidence scoring algorithm
- Multi-factor recommendation logic
- Agent capability matching

**Location**: `/src/claude_mpm/services/agents/`
- `recommender.py` - Agent recommendation service

### Phase 4: Auto-Configuration Orchestration

**Objective**: Coordinate detection, recommendation, and deployment

**Components:**
- `AutoConfigManagerService` - Orchestrates entire workflow
- `IDeploymentObserver` - Interface for progress tracking
- Configuration validation
- State persistence and rollback

**Location**: `/src/claude_mpm/services/agents/`
- `auto_config_manager.py` - Main orchestration service
- `observers.py` - Observer implementations

### Phase 5: CLI Integration

**Objective**: User-friendly command-line interface

**Components:**
- `AutoConfigureCommand` - CLI command handler
- `RichProgressObserver` - Rich console progress display
- Interactive and non-interactive modes
- JSON output support

**Location**: `/src/claude_mpm/cli/commands/`
- `auto_configure.py` - CLI command implementation

## Component Architecture

### Service Layer

```
┌─────────────────────────────────────────────────────────────┐
│                 AutoConfigManagerService                     │
│  (Orchestrates entire auto-configuration workflow)          │
└─────────────────┬──────────────┬─────────────┬──────────────┘
                  │              │             │
      ┌───────────▼────┐  ┌──────▼──────┐  ┌──▼─────────────┐
      │ Toolchain      │  │ Agent       │  │ Agent          │
      │ Analyzer       │  │ Recommender │  │ Deployment     │
      │ Service        │  │ Service     │  │ Service        │
      └───────┬────────┘  └──────┬──────┘  └────────────────┘
              │                  │
    ┌─────────▼─────────┐       │
    │ Detection         │       │
    │ Strategies        │       │
    │ (Python, Node.js, │       │
    │  Rust, Go)        │       │
    └───────────────────┘       │
                        ┌───────▼────────┐
                        │ Agent Registry │
                        └────────────────┘
```

### Strategy Pattern Implementation

Each language has its own detection strategy:

```python
class IToolchainDetectionStrategy(ABC):
    """Interface for language-specific detection strategies."""

    @abstractmethod
    def detect(self, project_path: Path) -> ToolchainAnalysis:
        """Detect language, version, frameworks, and deployment targets."""
        pass

    @abstractmethod
    def get_language_name(self) -> str:
        """Return the language name this strategy detects."""
        pass

    @abstractmethod
    def calculate_confidence(self, evidence: Dict[str, any]) -> float:
        """Calculate confidence score based on evidence."""
        pass
```

**Strategies:**
- `PythonDetectionStrategy` - Detects Python via requirements.txt, pyproject.toml
- `NodeJSDetectionStrategy` - Detects Node.js via package.json
- `RustDetectionStrategy` - Detects Rust via Cargo.toml
- `GoDetectionStrategy` - Detects Go via go.mod

### Observer Pattern Implementation

Progress tracking during agent deployment:

```python
class IDeploymentObserver(ABC):
    """Interface for observing agent deployment progress."""

    @abstractmethod
    def on_agent_deployment_started(
        self, agent_id: str, agent_name: str, index: int, total: int
    ) -> None:
        """Called when agent deployment starts."""
        pass

    @abstractmethod
    def on_agent_deployment_completed(
        self, agent_id: str, agent_name: str, success: bool, error: Optional[str]
    ) -> None:
        """Called when agent deployment completes."""
        pass

    @abstractmethod
    def on_deployment_completed(
        self, success_count: int, failure_count: int, duration_ms: float
    ) -> None:
        """Called when all deployments complete."""
        pass
```

**Implementations:**
- `NullObserver` - No-op implementation for testing
- `RichProgressObserver` - Rich console progress bars

## Service Details

### ToolchainAnalyzerService

**Responsibility**: Detect project technologies with confidence scoring

**Key Methods:**

```python
def analyze_project(self, project_path: str) -> ToolchainAnalysis:
    """Analyze project and return detected toolchain."""

def register_strategy(self, name: str, strategy: IToolchainDetectionStrategy) -> None:
    """Register a new detection strategy."""

def get_supported_languages(self) -> List[str]:
    """Get list of supported languages."""
```

**Detection Process:**

1. Run all registered detection strategies in parallel
2. Collect evidence from each strategy
3. Calculate confidence scores per component
4. Aggregate results into `ToolchainAnalysis`
5. Cache results for 5 minutes

**Confidence Scoring:**

Each strategy calculates confidence based on:
- File presence (e.g., package.json exists = +0.4)
- File validity (e.g., valid JSON = +0.3)
- Version detection (e.g., version found = +0.2)
- Dependencies/frameworks (e.g., specific libs = +0.1 per lib)

**Caching:**

```python
# Cache key: project_path
# TTL: 5 minutes
# Invalidation: Automatic on expiry
```

### AgentRecommenderService

**Responsibility**: Recommend agents based on detected toolchain

**Key Methods:**

```python
def recommend_agents(
    self, toolchain: ToolchainAnalysis, min_confidence: float = 0.8
) -> List[AgentRecommendation]:
    """Recommend agents based on toolchain analysis."""

def get_agent_for_language(self, language: str) -> Optional[str]:
    """Get primary agent ID for a specific language."""

def get_agents_for_framework(self, framework: str) -> List[str]:
    """Get agents specialized for a framework."""
```

**Recommendation Algorithm:**

```python
def calculate_recommendation_confidence(
    agent: AgentMetadata,
    toolchain: ToolchainAnalysis
) -> float:
    """
    Calculate recommendation confidence using multi-factor scoring:

    1. Language Match (40%):
       - Primary language match: 0.4
       - Secondary language match: 0.2

    2. Framework Match (30%):
       - Exact framework match: 0.3
       - Related framework: 0.15

    3. Capability Match (20%):
       - Required capabilities present: 0.2
       - Partial capabilities: 0.1

    4. Deployment Target (10%):
       - Deployment configuration match: 0.1

    Total confidence = sum of all factors (0.0-1.0)
    """
```

**Agent Mapping:**

| Language | Primary Agent | Framework Agents |
|----------|--------------|------------------|
| Python | python-engineer | fastapi-specialist, django-specialist |
| Node.js | nodejs-engineer | nextjs-engineer, react-specialist |
| Rust | rust-engineer | actix-specialist |
| Go | go-engineer | gin-specialist |
| TypeScript | typescript-engineer | nextjs-engineer, react-specialist |

### AutoConfigManagerService

**Responsibility**: Orchestrate detection, recommendation, and deployment

**Key Methods:**

```python
def preview_configuration(
    self, project_path: str, min_confidence: float = 0.8
) -> ConfigurationPreview:
    """Preview what would be configured without deploying."""

def execute_configuration(
    self,
    project_path: str,
    min_confidence: float = 0.8,
    observer: Optional[IDeploymentObserver] = None
) -> ConfigurationResult:
    """Execute full auto-configuration with agent deployment."""

def validate_configuration(
    self, preview: ConfigurationPreview
) -> ValidationResult:
    """Validate configuration before deployment."""
```

**Workflow:**

```
1. Analyze Project
   └─> ToolchainAnalyzerService.analyze_project()

2. Recommend Agents
   └─> AgentRecommenderService.recommend_agents()

3. Validate Configuration
   └─> Validate recommendations (conflicts, dependencies)

4. Preview or Execute
   ├─> Preview: Return ConfigurationPreview
   └─> Execute:
       ├─> Deploy each agent
       ├─> Track progress via observer
       ├─> Handle failures gracefully
       └─> Return ConfigurationResult
```

**Error Handling:**

- **Partial Success**: Some agents deploy, others fail (returns PARTIAL_SUCCESS)
- **Complete Failure**: No agents deploy (returns FAILURE)
- **Validation Errors**: Stop before deployment (returns errors)
- **Rollback**: Failed deployments don't affect successful ones

### Detection Strategies

#### PythonDetectionStrategy

**Detection Files:**
- `requirements.txt` - pip dependencies
- `pyproject.toml` - Poetry/PEP 518 configuration
- `setup.py` - setuptools configuration
- `Pipfile` - Pipenv configuration

**Framework Detection:**
```python
frameworks_map = {
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "tornado": "Tornado",
    "pyramid": "Pyramid",
    "aiohttp": "aiohttp"
}
```

**Confidence Calculation:**
```python
confidence = 0.0
if requirements_txt_exists: confidence += 0.4
if pyproject_toml_exists: confidence += 0.3
if valid_syntax: confidence += 0.2
if version_detected: confidence += 0.1
# Max: 1.0
```

#### NodeJSDetectionStrategy

**Detection Files:**
- `package.json` - npm/yarn/pnpm configuration
- `package-lock.json` - npm lock file
- `yarn.lock` - Yarn lock file
- `pnpm-lock.yaml` - pnpm lock file

**Framework Detection:**
```python
frameworks_map = {
    "next": "Next.js",
    "react": "React",
    "vue": "Vue.js",
    "nuxt": "Nuxt.js",
    "express": "Express",
    "nestjs": "NestJS",
    "@angular/core": "Angular"
}
```

**Version Detection:**
```json
// package.json
{
  "engines": {
    "node": ">=18.0.0"  // Extracted
  }
}
```

#### RustDetectionStrategy

**Detection Files:**
- `Cargo.toml` - Cargo manifest
- `Cargo.lock` - Dependency lock file

**Framework Detection:**
```toml
# Cargo.toml
[dependencies]
actix-web = "4.0"  # Detected as Actix-web framework
rocket = "0.5"     # Detected as Rocket framework
axum = "0.6"       # Detected as Axum framework
```

**Edition Detection:**
```toml
# Cargo.toml
[package]
edition = "2021"  # Rust edition extracted
```

#### GoDetectionStrategy

**Detection Files:**
- `go.mod` - Go module file
- `go.sum` - Dependency checksums

**Framework Detection:**
```go
// go.mod
require (
    github.com/gin-gonic/gin v1.9.0  // Gin framework
    github.com/labstack/echo v4.0.0  // Echo framework
    github.com/gofiber/fiber v2.0.0  // Fiber framework
)
```

**Version Detection:**
```go
// go.mod
module myproject

go 1.21  // Go version extracted
```

## Data Models

### ToolchainAnalysis

Represents detected project toolchain:

```python
@dataclass
class ToolchainAnalysis:
    """Analysis result for project toolchain."""

    components: List[ToolchainComponent]  # Detected components
    primary_language: Optional[str]       # Main language
    frameworks: List[Framework]           # Detected frameworks
    deployment_targets: List[DeploymentTarget]  # Deployment configs
    confidence: float                     # Overall confidence (0.0-1.0)
    evidence: Dict[str, Any]              # Evidence collected
    timestamp: float                      # Detection timestamp
```

### ToolchainComponent

Individual detected component:

```python
@dataclass
class ToolchainComponent:
    """Individual toolchain component."""

    type: ComponentType           # LANGUAGE, FRAMEWORK, DEPLOYMENT
    name: str                     # Component name
    version: Optional[str]        # Version if detected
    confidence: float             # Confidence (0.0-1.0)
    evidence: Dict[str, Any]      # Evidence for detection
```

### AgentRecommendation

Agent recommendation with reasoning:

```python
@dataclass
class AgentRecommendation:
    """Recommendation for an agent."""

    agent_id: str                 # Agent identifier
    confidence: float             # Recommendation confidence (0.0-1.0)
    reasoning: str                # Human-readable reasoning
    capabilities: List[str]       # Matched capabilities
    metadata: Dict[str, Any]      # Additional metadata
```

### ConfigurationResult

Result of auto-configuration execution:

```python
@dataclass
class ConfigurationResult:
    """Result of auto-configuration."""

    status: ConfigurationStatus   # SUCCESS, PARTIAL_SUCCESS, FAILURE
    deployed_agents: List[str]    # Successfully deployed agent IDs
    failed_agents: List[str]      # Failed agent IDs
    errors: Dict[str, str]        # Error messages per agent
    toolchain: ToolchainAnalysis  # Detected toolchain
    recommendations: List[AgentRecommendation]  # All recommendations
    timestamp: float              # Execution timestamp
```

## Adding New Language Support

### Step 1: Create Detection Strategy

Create a new strategy class in `/src/claude_mpm/services/project/detection_strategies/`:

```python
"""
[Language] Detection Strategy
==============================

WHY: Detect [Language] projects via [detection files].

DESIGN DECISION: Strategy pattern for pluggable detection.
"""

from pathlib import Path
from typing import Dict, List, Optional

from ...core.models.toolchain import (
    ComponentType,
    Framework,
    ToolchainAnalysis,
    ToolchainComponent,
)
from .base import IToolchainDetectionStrategy


class LanguageDetectionStrategy(IToolchainDetectionStrategy):
    """Strategy for detecting [Language] projects."""

    def __init__(self):
        """Initialize the detection strategy."""
        self.language_name = "[Language]"

        # Define framework mappings
        self.frameworks_map = {
            "framework-package": "Framework Name",
            # Add more mappings
        }

    def get_language_name(self) -> str:
        """Return the language name."""
        return self.language_name

    def detect(self, project_path: Path) -> ToolchainAnalysis:
        """
        Detect [Language] toolchain.

        Args:
            project_path: Path to project directory

        Returns:
            ToolchainAnalysis with detected components
        """
        components = []
        evidence = {}

        # 1. Check for primary detection file
        config_file = project_path / "config-file.ext"
        if config_file.exists():
            # Parse configuration
            config = self._parse_config(config_file)
            evidence["config_file"] = str(config_file)

            # 2. Detect version
            version = self._extract_version(config)
            if version:
                evidence["version"] = version

            # 3. Detect frameworks
            frameworks = self._detect_frameworks(config)
            evidence["frameworks"] = [f.name for f in frameworks]

            # 4. Calculate confidence
            confidence = self._calculate_confidence(evidence)

            # 5. Create component
            component = ToolchainComponent(
                type=ComponentType.LANGUAGE,
                name=self.language_name,
                version=version,
                confidence=confidence,
                evidence=evidence,
            )
            components.append(component)

            # 6. Return analysis
            return ToolchainAnalysis(
                components=components,
                primary_language=self.language_name,
                frameworks=frameworks,
                deployment_targets=[],
                confidence=confidence,
                evidence=evidence,
                timestamp=time.time(),
            )

        # No detection
        return ToolchainAnalysis(
            components=[],
            primary_language=None,
            frameworks=[],
            deployment_targets=[],
            confidence=0.0,
            evidence={},
            timestamp=time.time(),
        )

    def _parse_config(self, config_file: Path) -> Dict:
        """Parse configuration file."""
        try:
            # Implement parsing logic
            pass
        except Exception:
            return {}

    def _extract_version(self, config: Dict) -> Optional[str]:
        """Extract language version from config."""
        # Implement version extraction
        pass

    def _detect_frameworks(self, config: Dict) -> List[Framework]:
        """Detect frameworks from dependencies."""
        frameworks = []
        dependencies = config.get("dependencies", {})

        for dep_name, dep_version in dependencies.items():
            if dep_name in self.frameworks_map:
                framework_name = self.frameworks_map[dep_name]
                frameworks.append(
                    Framework(
                        name=framework_name,
                        version=str(dep_version) if dep_version else None,
                        confidence=0.9,
                    )
                )

        return frameworks

    def _calculate_confidence(self, evidence: Dict) -> float:
        """Calculate confidence based on evidence."""
        confidence = 0.0

        # File exists
        if "config_file" in evidence:
            confidence += 0.4

        # Version detected
        if "version" in evidence:
            confidence += 0.3

        # Valid syntax
        if evidence.get("valid_syntax", False):
            confidence += 0.2

        # Frameworks detected
        if evidence.get("frameworks"):
            confidence += 0.1

        return min(confidence, 1.0)

    def calculate_confidence(self, evidence: Dict) -> float:
        """Public method for confidence calculation."""
        return self._calculate_confidence(evidence)
```

### Step 2: Register Strategy

Register in `ToolchainAnalyzerService.__init__()`:

```python
# In toolchain_analyzer.py
def _register_default_strategies(self) -> None:
    """Register default detection strategies."""
    self.register_strategy("nodejs", NodeJSDetectionStrategy())
    self.register_strategy("python", PythonDetectionStrategy())
    self.register_strategy("rust", RustDetectionStrategy())
    self.register_strategy("go", GoDetectionStrategy())
    self.register_strategy("language", LanguageDetectionStrategy())  # Add here
```

### Step 3: Add Agent Mappings

Update agent recommendation mappings in `AgentRecommenderService`:

```python
# In recommender.py
def _initialize_mappings(self) -> None:
    """Initialize language and framework to agent mappings."""
    self.language_to_agent = {
        "Python": "python-engineer",
        "JavaScript": "nodejs-engineer",
        "TypeScript": "typescript-engineer",
        "Rust": "rust-engineer",
        "Go": "go-engineer",
        "[Language]": "language-engineer",  # Add mapping
    }

    self.framework_to_agents = {
        "FastAPI": ["python-engineer", "fastapi-specialist"],
        "Next.js": ["nextjs-engineer", "react-specialist"],
        "[Framework]": ["language-engineer", "framework-specialist"],  # Add mapping
    }
```

### Step 4: Create Tests

Create comprehensive tests in `/tests/services/project/test_language_detection.py`:

```python
"""Tests for [Language] Detection Strategy."""

import pytest
from pathlib import Path
from claude_mpm.services.project.detection_strategies.language_strategy import (
    LanguageDetectionStrategy,
)


class TestLanguageDetectionStrategy:
    """Test suite for [Language] detection."""

    @pytest.fixture
    def strategy(self):
        """Create strategy instance."""
        return LanguageDetectionStrategy()

    def test_get_language_name(self, strategy):
        """Test language name retrieval."""
        assert strategy.get_language_name() == "[Language]"

    def test_detect_basic_project(self, tmp_path, strategy):
        """Test detection of basic [Language] project."""
        # Create config file
        config_file = tmp_path / "config.ext"
        config_file.write_text("""
        # Sample configuration
        """)

        # Run detection
        result = strategy.detect(tmp_path)

        # Assertions
        assert result.primary_language == "[Language]"
        assert len(result.components) > 0
        assert result.confidence > 0.0

    def test_detect_with_version(self, tmp_path, strategy):
        """Test version detection."""
        # Create config with version
        config_file = tmp_path / "config.ext"
        config_file.write_text("""
        version = "1.0.0"
        """)

        result = strategy.detect(tmp_path)

        assert result.components[0].version == "1.0.0"

    def test_detect_frameworks(self, tmp_path, strategy):
        """Test framework detection."""
        # Create config with framework dependencies
        config_file = tmp_path / "config.ext"
        config_file.write_text("""
        dependencies:
          - framework-package: 1.0.0
        """)

        result = strategy.detect(tmp_path)

        assert len(result.frameworks) > 0
        assert "Framework Name" in [f.name for f in result.frameworks]

    def test_no_detection(self, tmp_path, strategy):
        """Test when no [Language] project detected."""
        result = strategy.detect(tmp_path)

        assert result.primary_language is None
        assert len(result.components) == 0
        assert result.confidence == 0.0

    def test_confidence_calculation(self, strategy):
        """Test confidence score calculation."""
        # High confidence
        evidence_high = {
            "config_file": "config.ext",
            "version": "1.0.0",
            "valid_syntax": True,
            "frameworks": ["Framework"],
        }
        assert strategy.calculate_confidence(evidence_high) >= 0.9

        # Medium confidence
        evidence_medium = {
            "config_file": "config.ext",
            "version": "1.0.0",
        }
        assert 0.5 <= strategy.calculate_confidence(evidence_medium) < 0.9

        # Low confidence
        evidence_low = {"config_file": "config.ext"}
        assert strategy.calculate_confidence(evidence_low) < 0.5
```

### Step 5: Update Documentation

Add to user documentation (`docs/user/03-features/auto-configuration.md`):

```markdown
### Languages

| Language | Detection Methods | Version Detection | Confidence Factors |
|----------|------------------|-------------------|-------------------|
| **[Language]** | `config.ext`, `other-file` | Version field in config | File presence, syntax validity |
```

## Adding New Framework Detection

### Step 1: Update Strategy Framework Map

Add framework to language strategy's `frameworks_map`:

```python
# In language_strategy.py
self.frameworks_map = {
    "existing-framework": "Existing Framework",
    "new-framework": "New Framework Name",  # Add here
}
```

### Step 2: Add Agent Mapping

Update `AgentRecommenderService.framework_to_agents`:

```python
# In recommender.py
self.framework_to_agents = {
    "Existing Framework": ["language-engineer", "existing-specialist"],
    "New Framework Name": ["language-engineer", "new-framework-specialist"],  # Add
}
```

### Step 3: Create Specialized Agent (Optional)

If the framework warrants a specialized agent, create one following the [Agent Creation Guide](../developer/07-agent-system/creation-guide.md).

### Step 4: Test Framework Detection

Add tests for framework detection:

```python
def test_detect_new_framework(tmp_path, strategy):
    """Test detection of new framework."""
    config = tmp_path / "config.ext"
    config.write_text("""
    dependencies:
      new-framework: 1.0.0
    """)

    result = strategy.detect(tmp_path)

    frameworks = [f.name for f in result.frameworks]
    assert "New Framework Name" in frameworks
```

## Performance Considerations

### Caching Strategy

The toolchain analyzer uses multi-level caching:

```python
# Level 1: In-memory cache (5 minutes TTL)
self._cache: Dict[str, ToolchainAnalysis] = {}
self._cache_ttl = 300

# Cache key generation
cache_key = f"{project_path}:{hash(frozenset(os.listdir(project_path)))}"

# Cache lookup
if cache_key in self._cache:
    cached_result, timestamp = self._cache[cache_key]
    if time.time() - timestamp < self._cache_ttl:
        return cached_result
```

**Cache Invalidation:**
- Automatic after 5 minutes
- On file system changes (detected via directory hash)
- Manual clear on service restart

### Lazy Loading

Services are lazy-loaded to reduce startup time:

```python
@property
def auto_config_manager(self) -> AutoConfigManagerService:
    """Get auto-configuration manager (lazy loaded)."""
    if self._auto_config_manager is None:
        # Initialize only when first accessed
        self._auto_config_manager = AutoConfigManagerService(...)
    return self._auto_config_manager
```

### Parallel Detection

Detection strategies run in parallel for performance:

```python
# Pseudo-code
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {
        executor.submit(strategy.detect, project_path): name
        for name, strategy in self._strategies.items()
    }

    for future in as_completed(futures):
        result = future.result()
        # Process result
```

### File I/O Optimization

Minimize file system operations:

```python
# Bad: Multiple file reads
if (project_path / "file1").exists():
    with open(project_path / "file1") as f:
        content1 = f.read()
if (project_path / "file2").exists():
    with open(project_path / "file2") as f:
        content2 = f.read()

# Good: Batch file operations
files_to_read = ["file1", "file2"]
contents = {}
for filename in files_to_read:
    file_path = project_path / filename
    if file_path.exists():
        with open(file_path) as f:
            contents[filename] = f.read()
```

## Testing Guidelines

### Test Structure

Follow the 207-test suite structure:

```
tests/
└── services/
    ├── project/
    │   ├── test_toolchain_analyzer.py          # 45 tests
    │   ├── test_python_detection.py            # 38 tests
    │   ├── test_nodejs_detection.py            # 36 tests
    │   ├── test_rust_detection.py              # 32 tests
    │   └── test_go_detection.py                # 30 tests
    └── agents/
        ├── test_recommender.py                 # 41 tests
        ├── test_auto_config_manager.py         # 35 tests
        └── test_observers.py                   # 15 tests
```

### Test Categories

1. **Unit Tests**: Individual component testing
   - Strategy detection logic
   - Confidence calculation
   - Evidence collection

2. **Integration Tests**: Service interaction testing
   - Analyzer + Strategy integration
   - Recommender + Registry integration
   - Manager orchestration

3. **E2E Tests**: Full workflow testing
   - Preview configuration
   - Execute configuration
   - Error handling

### Test Fixtures

Use shared fixtures for consistency:

```python
@pytest.fixture
def sample_python_project(tmp_path):
    """Create a sample Python project."""
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("fastapi==0.104.1\nuvicorn==0.24.0")

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
    [tool.poetry]
    name = "test-project"
    version = "0.1.0"

    [tool.poetry.dependencies]
    python = "^3.11"
    fastapi = "^0.104.1"
    """)

    return tmp_path


@pytest.fixture
def sample_nodejs_project(tmp_path):
    """Create a sample Node.js project."""
    package_json = tmp_path / "package.json"
    package_json.write_text("""
    {
      "name": "test-app",
      "version": "1.0.0",
      "engines": {
        "node": ">=18.0.0"
      },
      "dependencies": {
        "next": "14.0.0",
        "react": "18.2.0"
      }
    }
    """)

    return tmp_path
```

### Coverage Goals

Maintain high test coverage:

- **Overall**: 76%+ (current: 76%)
- **Critical paths**: 90%+
- **Detection strategies**: 85%+
- **Recommendation logic**: 80%+

## Error Handling

### Graceful Degradation

Auto-configuration handles errors gracefully:

```python
try:
    # Attempt detection
    result = strategy.detect(project_path)
except FileNotFoundError:
    # File doesn't exist - return empty result
    return ToolchainAnalysis(components=[], confidence=0.0)
except PermissionError:
    # Can't read file - log and continue
    logger.warning(f"Permission denied: {file_path}")
    return ToolchainAnalysis(components=[], confidence=0.0)
except json.JSONDecodeError:
    # Invalid JSON - lower confidence
    return ToolchainAnalysis(components=[], confidence=0.3)
```

### Partial Success Handling

Deployment can partially succeed:

```python
result = ConfigurationResult(
    status=ConfigurationStatus.PARTIAL_SUCCESS,
    deployed_agents=["agent1", "agent2"],
    failed_agents=["agent3"],
    errors={"agent3": "Deployment failed: invalid config"},
)
```

### Validation Before Deployment

Validate configuration before executing:

```python
def validate_configuration(preview: ConfigurationPreview) -> ValidationResult:
    """Validate configuration before deployment."""
    issues = []

    # Check for conflicts
    if has_conflicting_agents(preview.recommendations):
        issues.append(ValidationIssue(
            severity=IssueSeverity.ERROR,
            message="Conflicting agents detected"
        ))

    # Check for missing dependencies
    if has_missing_dependencies(preview.recommendations):
        issues.append(ValidationIssue(
            severity=IssueSeverity.WARNING,
            message="Some agents have unmet dependencies"
        ))

    return ValidationResult(
        is_valid=len([i for i in issues if i.severity == "error"]) == 0,
        issues=issues
    )
```

## Best Practices

### For Strategy Implementation

1. **Evidence Collection**: Always collect detailed evidence for confidence scoring
2. **Error Handling**: Use try-except for file operations with graceful fallbacks
3. **Confidence Scoring**: Use consistent scoring methodology across strategies
4. **Version Detection**: Prioritize explicit version declarations over heuristics
5. **Framework Detection**: Match by package name, not file patterns

### For Agent Recommendation

1. **Multi-Factor Scoring**: Consider language, framework, capabilities, deployment
2. **Threshold Tuning**: Default 0.8 balances precision and recall
3. **Clear Reasoning**: Provide human-readable reasoning for each recommendation
4. **Capability Matching**: Verify agent capabilities match project needs
5. **Avoid Over-Recommendation**: Quality over quantity

### For Testing

1. **Realistic Fixtures**: Use real-world project structures in tests
2. **Edge Cases**: Test invalid files, missing files, permission errors
3. **Confidence Ranges**: Test all confidence levels (high, medium, low, none)
4. **Integration**: Test service interactions, not just isolated components
5. **Performance**: Include performance benchmarks for detection

## Security Considerations

### Path Traversal Prevention

Validate all file paths:

```python
def safe_read_file(project_path: Path, filename: str) -> Optional[str]:
    """Safely read a file within project directory."""
    # Resolve to absolute path
    file_path = (project_path / filename).resolve()

    # Ensure file is within project directory
    if not str(file_path).startswith(str(project_path.resolve())):
        raise ValueError(f"Path traversal attempt: {filename}")

    # Read file
    if file_path.exists():
        return file_path.read_text()
    return None
```

### Input Validation

Validate all configuration inputs:

```python
def validate_min_confidence(value: float) -> float:
    """Validate confidence threshold."""
    if not isinstance(value, (int, float)):
        raise TypeError("Confidence must be a number")
    if not 0.0 <= value <= 1.0:
        raise ValueError("Confidence must be between 0.0 and 1.0")
    return float(value)
```

### Safe Parsing

Use safe parsing for configuration files:

```python
import json
import toml

def safe_parse_json(file_path: Path) -> Dict:
    """Safely parse JSON file."""
    try:
        with open(file_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return {}
```

## Monitoring and Logging

### Structured Logging

Use structured logging for observability:

```python
logger.info(
    "Toolchain analysis completed",
    extra={
        "project_path": str(project_path),
        "detected_language": analysis.primary_language,
        "confidence": analysis.confidence,
        "frameworks": [f.name for f in analysis.frameworks],
        "duration_ms": duration_ms,
    }
)
```

### Metrics Collection

Track key metrics:

```python
# Detection metrics
metrics.increment("toolchain.detection.total")
metrics.histogram("toolchain.detection.duration_ms", duration_ms)
metrics.gauge("toolchain.detection.confidence", confidence)

# Recommendation metrics
metrics.increment("agent.recommendation.total")
metrics.gauge("agent.recommendation.count", len(recommendations))

# Deployment metrics
metrics.increment("agent.deployment.success", len(deployed_agents))
metrics.increment("agent.deployment.failure", len(failed_agents))
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm auto-configure --preview
```

## See Also

- [User Auto-Configuration Guide](../user/03-features/auto-configuration.md) - User-facing documentation
- [Agent System Guide](../AGENTS.md) - Complete agent development reference
- [Service Layer Guide](SERVICES.md) - Service development patterns
- [Testing Guide](TESTING.md) - Testing strategies and best practices
