# Enum Migration Guide

**Status**: Living Document
**Last Updated**: 2025-10-25
**Phase**: Phase 3A In Progress (Batch 23 Complete: Enum Consolidation Initiative)
**Recent**: Batch 23 completed enum consolidation (StepStatus → OperationResult), 1 new OperationResult value added (WARNING), 5 files migrated (deployment pipeline steps), Phase 3B Complete (AgentCategory validation), Phase 3C Complete (Enum expansions)

## Table of Contents

1. [Overview](#overview)
2. [Available Enums](#available-enums)
3. [Migration Patterns](#migration-patterns)
4. [Common Use Cases](#common-use-cases)
5. [Testing Guidelines](#testing-guidelines)
6. [Troubleshooting](#troubleshooting)

## Overview

Claude MPM has migrated from magic strings to type-safe enums across the codebase. This guide helps developers understand and use the new enum system effectively.

### Why Enums?

**Problems with Magic Strings:**
- No IDE autocomplete
- Typos caught only at runtime
- Inconsistent values across codebase
- Hard to track all usages

**Benefits of Enums:**
- Type safety and compile-time checks
- IDE autocomplete and refactoring support
- Centralized value definitions
- Clear documentation of valid values

### Import Location

All core enums are located in:
```python
from claude_mpm.core.enums import (
    OperationResult,
    OutputFormat,
    ServiceState,
    ValidationSeverity,
    ModelTier,
    AgentCategory,
)
```

## Available Enums

### 1. OperationResult

**Purpose**: Standardize operation outcomes across all services
**Coverage**: ~876 occurrences replaced

```python
class OperationResult(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"
    SKIPPED = "skipped"
```

**Usage Examples:**
```python
# Before (Magic Strings)
if result["status"] == "success":
    return {"status": "success", "data": data}

# After (Type-Safe Enum)
if result["status"] == OperationResult.SUCCESS:
    return {"status": OperationResult.SUCCESS, "data": data}
```

**Dict Keys Pattern:**
```python
# Common pattern in service responses
{
    "success": True,           # Boolean flag
    "status": OperationResult.SUCCESS,  # Enum value
    "message": "Operation completed"
}
```

### 2. OutputFormat

**Purpose**: Standardize CLI output format handling
**Coverage**: 103 CLI occurrences replaced

```python
class OutputFormat(StrEnum):
    JSON = "json"
    YAML = "yaml"
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    CSV = "csv"
```

**Usage Examples:**
```python
# Before (Magic Strings)
if args.format == "json":
    output = json.dumps(data)
elif args.format == "yaml":
    output = yaml.dump(data)

# After (Type-Safe Enum)
if args.format == OutputFormat.JSON:
    output = json.dumps(data)
elif args.format == OutputFormat.YAML:
    output = yaml.dump(data)
```

**CLI Argument Defaults:**
```python
# Before
parser.add_argument("--format", default="text")

# After
parser.add_argument("--format", default=OutputFormat.TEXT)
```

**Case-Insensitive Comparison:**
```python
# Handle user input that may vary in case
if str(args.format).lower() == OutputFormat.JSON:
    # Process JSON output
```

### 3. ServiceState

**Purpose**: Track service lifecycle states
**Coverage**: ~45 service files

```python
class ServiceState(StrEnum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"
```

**Usage Examples:**
```python
# Before (Magic Strings)
self.state = "running"
if self.state == "error":
    self.restart()

# After (Type-Safe Enum)
self.state = ServiceState.RUNNING
if self.state == ServiceState.ERROR:
    self.restart()
```

**Health Check Pattern:**
```python
def get_health_status(self) -> Dict[str, Any]:
    return {
        "state": self.state,  # ServiceState enum
        "healthy": self.state == ServiceState.RUNNING,
        "uptime": self._get_uptime(),
    }
```

### 4. ValidationSeverity

**Purpose**: Standardize validation and error severity levels
**Coverage**: Unified services, validators, error handlers

```python
class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
```

**Usage Examples:**
```python
# Before (Magic Strings)
@dataclass
class ValidationResult:
    severity: str = "error"  # Unclear valid values

# After (Type-Safe Enum)
@dataclass
class ValidationResult:
    severity: str = ValidationSeverity.ERROR  # Clear, documented

# Severity-based logic
if result.severity == ValidationSeverity.CRITICAL:
    alert_operations_team()
elif result.severity == ValidationSeverity.ERROR:
    log_error(result.message)
elif result.severity == ValidationSeverity.WARNING:
    log_warning(result.message)
```

**Integration with Analysis Results:**
```python
@dataclass
class AnalysisResult:
    success: bool
    findings: List[Dict[str, Any]] = field(default_factory=list)
    severity: str = ValidationSeverity.INFO  # Default to info level
    recommendations: List[str] = field(default_factory=list)
```

### 5. ModelTier

**Purpose**: Normalize Claude model names to standard tiers
**Special Feature**: Includes `normalize()` class method

```python
class ModelTier(StrEnum):
    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"

    @classmethod
    def normalize(cls, model_name: str) -> "ModelTier":
        """Intelligently convert any model variant to canonical tier."""
        normalized = model_name.lower().strip()

        # Direct match
        for tier in cls:
            if tier.value == normalized:
                return tier

        # Substring match
        if "opus" in normalized:
            return cls.OPUS
        elif "sonnet" in normalized:
            return cls.SONNET
        elif "haiku" in normalized:
            return cls.HAIKU

        # Default fallback
        return cls.SONNET
```

**Usage Examples:**
```python
# Before (Manual Normalization - 56 lines of code)
MODEL_MAPPINGS = {
    "claude-3-5-sonnet-20241022": "sonnet",
    "claude-3-5-sonnet-20240620": "sonnet",
    "claude-3-opus-20240229": "opus",
    # ... 23 more mappings
}

def _normalize_model(model: str) -> str:
    if model in MODEL_MAPPINGS:
        return MODEL_MAPPINGS[model]
    # ... 25 more lines of normalization logic
    return "sonnet"

# After (Enum-Based - 3 lines)
def _normalize_model(self, model: str) -> str:
    """Normalize model name using ModelTier enum."""
    return ModelTier.normalize(model).value
```

**Handles Multiple Formats:**
```python
# All of these work correctly:
ModelTier.normalize("claude-opus-4-20250514")  # → ModelTier.OPUS
ModelTier.normalize("SONNET")                  # → ModelTier.SONNET
ModelTier.normalize("  haiku  ")               # → ModelTier.HAIKU (whitespace handled)
ModelTier.normalize("claude-3-sonnet")         # → ModelTier.SONNET (substring match)
ModelTier.normalize("unknown-model")           # → ModelTier.SONNET (safe default)
```

### 6. AgentCategory

**Purpose**: Categorize agents by functional domain
**Coverage**: Agent configuration and routing

```python
class AgentCategory(StrEnum):
    ENGINEER = "engineer"
    QA = "qa"
    RESEARCH = "research"
    OPS = "ops"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    DATA = "data"
```

**Usage Examples:**
```python
# Before (Magic Strings)
if agent_type == "engineer":
    route_to_engineering_team(agent)

# After (Type-Safe Enum)
if agent_category == AgentCategory.ENGINEER:
    route_to_engineering_team(agent)
```

## Enum Consolidation Progress

### Overview

In addition to migrating magic strings to enums, we are consolidating duplicate enum definitions throughout the codebase. Multiple modules had created their own service state enums with similar or identical values, leading to inconsistency and maintenance overhead.

### Consolidated Enums

#### StepStatus → OperationResult (Batch 23)

**Date**: 2025-10-25
**Status**: ✅ Complete

**What Changed**:
- Removed redundant `StepStatus` enum from `src/claude_mpm/services/agents/deployment/pipeline/steps/base_step.py`
- Migrated all deployment pipeline steps to use core `OperationResult` enum
- Enhanced `OperationResult` enum with WARNING state for partial success scenarios

**Enum Values Added to OperationResult**:
```python
class OperationResult(StrEnum):
    WARNING = "warning"  # Added from StepStatus for partial success with issues
    # ... existing states ...
```

**Value Mapping**:
- `StepStatus.SUCCESS` → `OperationResult.SUCCESS`
- `StepStatus.FAILURE` → `OperationResult.FAILED`
- `StepStatus.SKIPPED` → `OperationResult.SKIPPED`
- `StepStatus.WARNING` → `OperationResult.WARNING` (new value added)

**Files Modified**: 5
- `src/claude_mpm/services/agents/deployment/pipeline/steps/base_step.py` (removed StepStatus enum, updated StepResult class)
- `src/claude_mpm/services/agents/deployment/pipeline/steps/target_directory_step.py` (3 occurrences)
- `src/claude_mpm/services/agents/deployment/pipeline/steps/configuration_step.py` (3 occurrences)
- `src/claude_mpm/services/agents/deployment/pipeline/steps/agent_processing_step.py` (5 occurrences)
- `src/claude_mpm/services/agents/deployment/pipeline/steps/validation_step.py` (4 occurrences)
- `src/claude_mpm/core/enums.py` (added 1 new result value)

**Benefits**:
- Unified operation result semantics across deployment pipeline and core services
- Consistent status reporting between pipeline steps and general operations
- Improved type safety for deployment status handling
- Reduced duplicate enum definitions

**Migration Pattern**:
```python
# Before (Duplicate Enum)
from .base_step import StepStatus

return StepResult(
    status=StepStatus.SUCCESS,
    message="Step completed successfully"
)

# After (Consolidated Enum)
from claude_mpm.core.enums import OperationResult

return StepResult(
    status=OperationResult.SUCCESS,
    message="Step completed successfully"
)
```

#### MCPServiceState → ServiceState (Batch 22)

**Date**: 2025-10-25
**Status**: ✅ Complete

**What Changed**:
- Removed redundant `MCPServiceState` enum from `src/claude_mpm/services/mcp_gateway/core/base.py`
- Migrated all MCP Gateway services to use core `ServiceState` enum
- Enhanced `ServiceState` enum with initialization states (UNINITIALIZED, INITIALIZING, INITIALIZED)

**Enum Values Added to ServiceState**:
```python
class ServiceState(StrEnum):
    UNINITIALIZED = "uninitialized"   # Added from MCPServiceState
    INITIALIZING = "initializing"     # Added from MCPServiceState
    INITIALIZED = "initialized"       # Added from MCPServiceState
    # ... existing states ...
```

**Files Modified**: 2
- `src/claude_mpm/services/mcp_gateway/core/base.py` (17 occurrences)
- `src/claude_mpm/services/mcp_gateway/core/__init__.py` (2 occurrences)
- `src/claude_mpm/core/enums.py` (added 3 new state values)

**Benefits**:
- Single source of truth for service lifecycle states
- Consistent state management across MCP Gateway and core services
- Improved type safety and IDE support
- Reduced maintenance overhead

**Migration Pattern**:
```python
# Before (Duplicate Enum)
from .base import MCPServiceState

self._state = MCPServiceState.INITIALIZING
if self._state == MCPServiceState.RUNNING:
    # ...

# After (Consolidated Enum)
from claude_mpm.core.enums import ServiceState

self._state = ServiceState.INITIALIZING
if self._state == ServiceState.RUNNING:
    # ...
```

### Future Consolidations

As we discover other duplicate enum definitions, they will be documented here:
- [ ] Check for duplicate OperationResult-like enums in services
- [ ] Check for duplicate OutputFormat enums in CLI modules
- [ ] Check for duplicate ValidationSeverity enums in validators

## Migration Patterns

### Pattern 1: Simple String Replacement

**When to Use**: Direct string literal replacement

```python
# Before
status = "success"
if status == "error":
    handle_error()

# After
status = OperationResult.SUCCESS
if status == OperationResult.ERROR:
    handle_error()
```

### Pattern 2: Dict Keys with Enum Values

**When to Use**: Service responses, configuration objects

```python
# Before
return {
    "success": True,
    "status": "completed",
    "format": "json"
}

# After
return {
    "success": True,
    "status": OperationResult.SUCCESS,
    "format": OutputFormat.JSON
}
```

**Note**: Keep boolean `success` key as-is; it's not an enum value.

### Pattern 3: Default Parameters

**When to Use**: Function/method defaults, dataclass fields

```python
# Before
def process_output(format: str = "text") -> str:
    ...

@dataclass
class Config:
    output_format: str = "json"

# After
def process_output(format: str = OutputFormat.TEXT) -> str:
    ...

@dataclass
class Config:
    output_format: str = OutputFormat.JSON
```

### Pattern 4: Replace-All Pattern

**When to Use**: Multiple identical occurrences in one file

```python
# Use Edit tool with replace_all=true
Edit(
    file_path="...",
    old_string='severity="error"',
    new_string='severity=ValidationSeverity.ERROR',
    replace_all=True
)
```

### Pattern 5: Case-Insensitive Comparison

**When to Use**: CLI arguments, user input

```python
# Before
if args.format.lower() == "json":
    ...

# After
if str(args.format).lower() == OutputFormat.JSON:
    ...
```

### Pattern 6: Enum Normalization Method

**When to Use**: Complex value normalization (model names, etc.)

```python
# Before: Manual mapping dictionary + normalization logic
MODEL_MAPPINGS = {...}  # 26 lines
def normalize():        # 30 lines
    ...

# After: Single enum method call
def normalize(model: str) -> str:
    return ModelTier.normalize(model).value
```

## Common Use Cases

### Use Case 1: CLI Command Output Formatting

```python
from claude_mpm.core.enums import OutputFormat

class MyCommand(BaseCommand):
    def run(self, args):
        # Get output format
        output_format = args.format

        # Type-safe comparison
        if str(output_format).lower() == OutputFormat.JSON:
            return json.dumps(self.data)
        elif str(output_format).lower() == OutputFormat.YAML:
            return yaml.dump(self.data)
        else:
            return str(self.data)
```

### Use Case 2: Service Health Monitoring

```python
from claude_mpm.core.enums import ServiceState

class MyService:
    def __init__(self):
        self.state = ServiceState.IDLE

    async def start(self):
        self.state = ServiceState.STARTING
        try:
            await self._initialize()
            self.state = ServiceState.RUNNING
        except Exception as e:
            self.state = ServiceState.ERROR
            raise

    def is_healthy(self) -> bool:
        return self.state == ServiceState.RUNNING
```

### Use Case 3: Validation with Severity Levels

```python
from claude_mpm.core.enums import ValidationSeverity

@dataclass
class ValidationRule:
    type: ValidationType
    severity: str = ValidationSeverity.ERROR
    message: Optional[str] = None

def validate(value, rule):
    if not is_valid(value):
        if rule.severity == ValidationSeverity.CRITICAL:
            raise CriticalValidationError(rule.message)
        elif rule.severity == ValidationSeverity.ERROR:
            return ValidationResult(valid=False, errors=[rule.message])
        elif rule.severity == ValidationSeverity.WARNING:
            return ValidationResult(valid=True, warnings=[rule.message])
```

### Use Case 4: Model Configuration

```python
from claude_mpm.core.enums import ModelTier

class AgentConfig:
    def __init__(self, model: str):
        # Normalize any model string to standard tier
        self.model_tier = ModelTier.normalize(model)
        self.model_display = model

    def get_model_config(self) -> Dict[str, Any]:
        return {
            "tier": self.model_tier.value,  # "opus", "sonnet", or "haiku"
            "display_name": self.model_display
        }
```

### Use Case 5: Operation Result Tracking

```python
from claude_mpm.core.enums import OperationResult

async def deploy_agent(agent_id: str) -> Dict[str, Any]:
    try:
        await _deploy_files(agent_id)
        await _configure_agent(agent_id)

        return {
            "success": True,
            "status": OperationResult.SUCCESS,
            "agent_id": agent_id
        }
    except PartialDeploymentError as e:
        return {
            "success": False,
            "status": OperationResult.PARTIAL,
            "error": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "status": OperationResult.ERROR,
            "error": str(e)
        }
```

## Testing Guidelines

### Test Import and Basic Usage

```python
def test_enum_import():
    """Verify enum can be imported."""
    from claude_mpm.core.enums import OperationResult
    assert OperationResult.SUCCESS == "success"
```

### Test String Compatibility

```python
def test_enum_string_compatibility():
    """Verify enums work as strings."""
    status = OperationResult.SUCCESS

    # Can be used as string
    assert str(status) == "success"

    # Can be compared to strings
    assert status == "success"

    # Works in dicts
    result = {"status": status}
    assert result["status"] == "success"
```

### Test Enum Methods

```python
def test_model_tier_normalize():
    """Test ModelTier.normalize() method."""
    # Direct tier names
    assert ModelTier.normalize("opus") == ModelTier.OPUS
    assert ModelTier.normalize("sonnet") == ModelTier.SONNET

    # Full model identifiers
    assert ModelTier.normalize("claude-opus-4-20250514") == ModelTier.OPUS

    # Case insensitive
    assert ModelTier.normalize("SONNET") == ModelTier.SONNET

    # Whitespace handling
    assert ModelTier.normalize("  haiku  ") == ModelTier.HAIKU

    # Unknown defaults to sonnet
    assert ModelTier.normalize("unknown") == ModelTier.SONNET
```

### Test Enum in Dataclasses

```python
def test_enum_in_dataclass():
    """Verify enums work in dataclasses."""
    from dataclasses import dataclass

    @dataclass
    class Result:
        status: str = OperationResult.SUCCESS
        format: str = OutputFormat.JSON

    r = Result()
    assert r.status == "success"
    assert r.format == "json"
```

## Troubleshooting

### Issue: ImportError

**Problem:**
```python
ImportError: cannot import name 'ValidationSeverity' from 'claude_mpm.core.enums'
```

**Solution:**
Ensure you're importing from the correct location:
```python
# Correct
from claude_mpm.core.enums import ValidationSeverity

# Incorrect
from claude_mpm.enums import ValidationSeverity
```

### Issue: Type Mismatch in Comparisons

**Problem:**
```python
# This might fail if args.format is already an enum
if args.format == OutputFormat.JSON:
```

**Solution:**
Use string conversion for safety:
```python
if str(args.format).lower() == OutputFormat.JSON:
```

### Issue: Dict Key Type Issues

**Problem:**
```python
# Old code expects string, gets enum
data = {"status": OperationResult.SUCCESS}
assert data["status"] == "success"  # Works due to StrEnum
```

**Explanation:**
StrEnum automatically converts to string in comparisons. This is intentional for backward compatibility.

### Issue: Enum in JSON Serialization

**Problem:**
```python
json.dumps({"status": OperationResult.SUCCESS})
# May fail with some JSON encoders
```

**Solution:**
StrEnum automatically serializes as string, but if issues occur:
```python
import json

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, StrEnum):
            return obj.value
        return super().default(obj)

json.dumps({"status": OperationResult.SUCCESS}, cls=EnumEncoder)
```

### Issue: ModelTier.normalize() Unexpected Default

**Problem:**
```python
# Unknown model defaults to SONNET
tier = ModelTier.normalize("custom-model-v2")
assert tier == ModelTier.SONNET  # Might be unexpected
```

**Solution:**
This is intentional behavior. Document your model naming or add explicit handling:
```python
model_name = "custom-model-v2"
if "custom" in model_name:
    tier = ModelTier.OPUS  # Explicit handling
else:
    tier = ModelTier.normalize(model_name)
```

## Migration Checklist

When migrating a file to use enums:

- [ ] Add import: `from claude_mpm.core.enums import <EnumName>`
- [ ] Replace magic strings with enum values
- [ ] Update default parameters to use enum values
- [ ] Replace string comparisons with enum comparisons
- [ ] Add `.value` where string output is explicitly needed
- [ ] Test import works: `python -c "from <module> import ..."`
- [ ] Run linters: `make lint-fix && make quality`
- [ ] Commit with descriptive message following Conventional Commits

## Additional Resources

- **Enum Source**: `src/claude_mpm/core/enums.py`
- **Enum Tests**: `tests/core/test_enums.py` (67 comprehensive tests)
- **Phase 1 Migration**: CLI layer (analyze.py, analyze_code.py, aggregate.py, config.py, agent_manager.py, memory.py)
- **Phase 2 Migration**: Services (interfaces.py, unified_analyzer.py, validation_strategy.py, frontmatter_validator.py, mcp_check.py)

## Version History

- **v1.0.0** (2025-10-25): Initial migration guide after Phase 1 & 2 completion
  - 6 core enums created
  - 103 CLI strings migrated
  - 67 comprehensive tests (100% pass rate)
  - ModelTier.normalize() deployed (56 lines → 3 lines)
  - ValidationSeverity integrated into unified services

---

**Questions or Issues?**

If you encounter issues not covered in this guide, please:
1. Check the enum source code: `src/claude_mpm/core/enums.py`
2. Review test cases: `tests/core/test_enums.py`
3. Search for similar patterns in recently migrated files
4. Ask in project discussion channels
