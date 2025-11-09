# Detailed Refactoring Checklist

**Generated**: 2025-11-08 12:23:04 EST
**Purpose**: Granular task breakdown for code review action items
**Parent Document**: `CODE_REVIEW_ACTION_PLAN.md`

---

## Priority 1: Quick Wins Checklist

### Task 1.1: Fix Wildcard Imports

**File 1: `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/interfaces.py`**

- [ ] Open file in editor
- [ ] Locate wildcard import (around line 36)
- [ ] Identify all symbols actually used from import
- [ ] Replace `from .module import *` with explicit imports
- [ ] Format imports alphabetically
- [ ] Run `ruff check` on file
- [ ] Run tests: `pytest tests/core/`
- [ ] Commit change

**File 2: `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/core/interfaces.py`**

- [ ] Open file in editor
- [ ] Locate wildcard import
- [ ] Identify all symbols actually used from import
- [ ] Replace with explicit imports
- [ ] Format imports alphabetically
- [ ] Run `ruff check` on file
- [ ] Run tests: `pytest tests/services/`
- [ ] Commit change

**Verification:**
```bash
# Search for remaining wildcard imports
grep -r "from .* import \*" src/claude_mpm/ --include="*.py"

# Should return nothing
```

---

### Task 1.2: Fix Print Statements in MCP Mode

**Step 1: Identify All Print Statements**

- [ ] Run search command:
  ```bash
  grep -rn "print(" src/claude_mpm/services/mcp/ --include="*.py" > print_audit.txt
  ```
- [ ] Review each print statement
- [ ] Categorize: Remove vs Convert to logging

**Step 2: Replace Print Statements**

For each file with print statements:

- [ ] File: `_________________`
  - [ ] Line __: Print statement identified
  - [ ] Determine appropriate log level (debug/info/warning/error)
  - [ ] Replace with `logger.___("...")`
  - [ ] Test MCP mode: `pytest tests/ -k mcp`
  - [ ] Verify no stdout pollution

**Step 3: Verification**

- [ ] Run: `grep -rn "print(" src/claude_mpm/services/mcp/ --include="*.py"`
- [ ] Should return 0 results
- [ ] Test MCP mode functionality
- [ ] Verify JSON protocol not corrupted
- [ ] Commit changes

---

### Task 1.3: Fix Magic Number Logging Levels

**File: `/Users/masa/Projects/claude-mpm/scripts/download_skills_api.py`**

- [ ] Open file at line 391
- [ ] Locate `logger.setLevel(10)`
- [ ] Add import: `import logging` (if not present)
- [ ] Replace with: `logger.setLevel(logging.DEBUG)`
- [ ] Check for other magic numbers in same file
- [ ] Run: `ruff check scripts/download_skills_api.py`
- [ ] Test script functionality
- [ ] Commit change

**Search for Other Occurrences:**
```bash
# Find other magic number setLevel calls
grep -rn "setLevel([0-9]" src/claude_mpm/ scripts/ --include="*.py"
```

- [ ] Fix any additional occurrences found
- [ ] Document in commit message

---

## Priority 2: Short-Term Refactoring Checklist

### Task 2.1: Refactor `mpm_init.py` (2,093 lines)

**Phase 1: Analysis and Planning**

- [ ] Read through entire file
- [ ] Identify logical sections (install, update, cleanup, validation)
- [ ] Map dependencies between sections
- [ ] Create module structure plan
- [ ] Document refactoring approach

**Phase 2: Create Module Structure**

- [ ] Create directory: `src/claude_mpm/cli/commands/mpm_init/`
- [ ] Create `__init__.py` (main command entry point)
- [ ] Create `install.py` (installation logic)
- [ ] Create `update.py` (update logic)
- [ ] Create `cleanup.py` (cleanup logic)
- [ ] Create `validation.py` (validation logic)
- [ ] Create `utils.py` (shared utilities)

**Phase 3: Extract Base Classes and Common Patterns**

- [ ] Identify repeated patterns
- [ ] Create base classes if needed
- [ ] Extract common utilities to `utils.py`
- [ ] Document interfaces

**Phase 4: Move Installation Logic**

- [ ] Copy install-related code to `install.py`
- [ ] Update imports in `install.py`
- [ ] Remove from original file
- [ ] Test: `pytest tests/ -k install`
- [ ] Commit: "refactor(mpm-init): extract installation logic"

**Phase 5: Move Update Logic**

- [ ] Copy update-related code to `update.py`
- [ ] Update imports in `update.py`
- [ ] Remove from original file
- [ ] Test: `pytest tests/ -k update`
- [ ] Commit: "refactor(mpm-init): extract update logic"

**Phase 6: Move Cleanup Logic**

- [ ] Copy cleanup-related code to `cleanup.py`
- [ ] Update imports in `cleanup.py`
- [ ] Remove from original file
- [ ] Test: `pytest tests/ -k cleanup`
- [ ] Commit: "refactor(mpm-init): extract cleanup logic"

**Phase 7: Move Validation Logic**

- [ ] Copy validation-related code to `validation.py`
- [ ] Update imports in `validation.py`
- [ ] Remove from original file
- [ ] Test: `pytest tests/ -k validation`
- [ ] Commit: "refactor(mpm-init): extract validation logic"

**Phase 8: Update Main Module**

- [ ] Keep only command orchestration in `__init__.py`
- [ ] Import from submodules
- [ ] Update command routing
- [ ] Verify all imports correct
- [ ] Test: `pytest tests/`
- [ ] Commit: "refactor(mpm-init): complete module restructure"

**Phase 9: Update Dependent Files**

- [ ] Search for imports of `mpm_init`
  ```bash
  grep -r "from.*mpm_init import" src/claude_mpm/ --include="*.py"
  ```
- [ ] Update imports in dependent files
- [ ] Test full CLI: `python -m claude_mpm --help`
- [ ] Test all mpm-init commands
- [ ] Commit: "refactor(mpm-init): update imports"

**Phase 10: Cleanup and Documentation**

- [ ] Remove original monolithic file (if fully migrated)
- [ ] Add module-level docstrings
- [ ] Update architecture docs
- [ ] Add migration notes to changelog
- [ ] Final test: `pytest tests/`
- [ ] Commit: "refactor(mpm-init): finalize restructure"

---

### Task 2.2: Refactor `code_tree_analyzer.py` (1,825 lines)

**Phase 1: Analysis**

- [ ] Read through entire file
- [ ] Identify logical sections:
  - [ ] Tree building
  - [ ] Analysis logic
  - [ ] Language parsers
  - [ ] Formatters
  - [ ] Utilities
- [ ] Map dependencies
- [ ] Plan module structure

**Phase 2: Create Module Structure**

- [ ] Create directory: `src/claude_mpm/core/code_tree/`
- [ ] Create `__init__.py` (public API)
- [ ] Create `analyzer.py` (main analyzer)
- [ ] Create `tree_builder.py` (tree construction)
- [ ] Create `formatters.py` (output formatting)
- [ ] Create `language_parsers.py` (language-specific logic)
- [ ] Create `utils.py` (shared utilities)

**Phase 3: Extract Tree Building Logic**

- [ ] Move tree-related classes to `tree_builder.py`
- [ ] Update imports
- [ ] Test tree building functionality
- [ ] Commit: "refactor(code-tree): extract tree builder"

**Phase 4: Extract Language Parsers**

- [ ] Move language-specific code to `language_parsers.py`
- [ ] Create parser registry/factory
- [ ] Update imports
- [ ] Test parsing functionality
- [ ] Commit: "refactor(code-tree): extract language parsers"

**Phase 5: Extract Formatters**

- [ ] Move formatting logic to `formatters.py`
- [ ] Create formatter interface
- [ ] Update imports
- [ ] Test output formatting
- [ ] Commit: "refactor(code-tree): extract formatters"

**Phase 6: Extract Utilities**

- [ ] Move helper functions to `utils.py`
- [ ] Update imports across modules
- [ ] Test utility functions
- [ ] Commit: "refactor(code-tree): extract utilities"

**Phase 7: Update Main Analyzer**

- [ ] Keep orchestration in `analyzer.py`
- [ ] Import from submodules
- [ ] Update public API in `__init__.py`
- [ ] Test: `pytest tests/core/`
- [ ] Commit: "refactor(code-tree): update main analyzer"

**Phase 8: Update Imports**

- [ ] Find all imports of `code_tree_analyzer`
  ```bash
  grep -r "from.*code_tree_analyzer import" src/claude_mpm/ --include="*.py"
  ```
- [ ] Update to use new module structure
- [ ] Test all dependent functionality
- [ ] Commit: "refactor(code-tree): update imports"

**Phase 9: Documentation**

- [ ] Add module docstrings
- [ ] Document parser plugin system
- [ ] Update architecture docs
- [ ] Add examples
- [ ] Final test: `pytest tests/`
- [ ] Commit: "refactor(code-tree): add documentation"

---

### Task 2.3: Thread Safety Audit of Singletons

**Phase 1: Identify All Singletons**

- [ ] Search for singleton patterns:
  ```bash
  grep -rn "def __new__" src/claude_mpm/ --include="*.py"
  grep -rn "_instance.*=" src/claude_mpm/ --include="*.py"
  grep -rn "class.*Singleton" src/claude_mpm/ --include="*.py"
  ```
- [ ] Create list of all singleton classes
- [ ] Document current implementation

**Singleton Inventory:**

| File | Class | Current Implementation | Thread-Safe? |
|------|-------|----------------------|--------------|
| `___` | `___` | `___` | ☐ |
| `___` | `___` | `___` | ☐ |
| `___` | `___` | `___` | ☐ |

**Phase 2: Create Thread-Safe Singleton Metaclass**

- [ ] Create `src/claude_mpm/core/patterns.py`
- [ ] Implement `ThreadSafeSingletonMeta`
- [ ] Add comprehensive docstring
- [ ] Add example usage
- [ ] Test with concurrent access

**Implementation:**
```python
import threading
from typing import Dict, Type

class ThreadSafeSingletonMeta(type):
    """Thread-safe singleton metaclass using double-checked locking."""

    _instances: Dict[Type, object] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        # First check (no lock)
        if cls not in cls._instances:
            # Acquire lock for initialization
            with cls._lock:
                # Second check (with lock)
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]
```

**Phase 3: Update Each Singleton**

For each singleton class:

- [ ] Class: `_________________`
  - [ ] Back up original implementation
  - [ ] Apply `ThreadSafeSingletonMeta`
  - [ ] Remove custom singleton logic if any
  - [ ] Add thread safety documentation
  - [ ] Write concurrency test
  - [ ] Run test: `pytest tests/`
  - [ ] Commit: "fix(singleton): make ___ thread-safe"

**Phase 4: Add Concurrency Tests**

- [ ] Create `tests/concurrency/test_singletons.py`
- [ ] Test each singleton with concurrent access
- [ ] Verify only one instance created
- [ ] Test race conditions
- [ ] Document thread safety guarantees

**Test Template:**
```python
import threading
import pytest
from claude_mpm.core.patterns import ThreadSafeSingletonMeta

def test_singleton_thread_safety():
    """Test singleton is thread-safe under concurrent access."""
    instances = []

    def create_instance():
        instance = MySingleton()
        instances.append(instance)

    threads = [threading.Thread(target=create_instance) for _ in range(100)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # All instances should be the same object
    assert len(set(id(inst) for inst in instances)) == 1
```

**Phase 5: Documentation**

- [ ] Update architecture docs
- [ ] Document thread safety guarantees
- [ ] Add to developer guide
- [ ] Update class docstrings
- [ ] Final commit: "docs(singleton): add thread safety documentation"

---

## Priority 3: Medium-Term Refactoring Checklist

### Task 3.1: Config Class Refactoring (984 lines)

**Phase 1: Analysis**

- [ ] Read through `src/claude_mpm/core/config.py`
- [ ] Identify responsibilities:
  - [ ] Configuration loading
  - [ ] Configuration validation
  - [ ] Default values management
  - [ ] Configuration access/getters
  - [ ] Configuration updates/setters
- [ ] Map dependencies
- [ ] Design new structure

**Phase 2: Create Module Structure**

- [ ] Create directory: `src/claude_mpm/core/config/`
- [ ] Create `__init__.py` (public API)
- [ ] Create `loader.py` (loading logic)
- [ ] Create `validator.py` (validation logic)
- [ ] Create `schema.py` (configuration schema)
- [ ] Create `defaults.py` (default values)
- [ ] Create `models.py` (data models)

**Phase 3: Extract Default Values**

- [ ] Move all default constants to `defaults.py`
- [ ] Organize by category
- [ ] Add documentation for each default
- [ ] Test: defaults accessible
- [ ] Commit: "refactor(config): extract default values"

**Phase 4: Create Configuration Schema**

- [ ] Define configuration schema in `schema.py`
- [ ] Use dataclasses or pydantic for models
- [ ] Document each field
- [ ] Add type hints
- [ ] Test: schema validates correct config
- [ ] Commit: "refactor(config): add configuration schema"

**Phase 5: Extract Configuration Models**

- [ ] Create typed models in `models.py`
- [ ] Replace dict-based config with typed models
- [ ] Add validation in model
- [ ] Test: models work correctly
- [ ] Commit: "refactor(config): add configuration models"

**Phase 6: Extract Loader**

- [ ] Move loading logic to `loader.py`
- [ ] Support multiple formats (YAML, JSON, ENV)
- [ ] Add error handling
- [ ] Test: loading from various sources
- [ ] Commit: "refactor(config): extract loader"

**Phase 7: Extract Validator**

- [ ] Move validation logic to `validator.py`
- [ ] Create validation rules
- [ ] Add helpful error messages
- [ ] Test: validation catches errors
- [ ] Commit: "refactor(config): extract validator"

**Phase 8: Create Main Config Class**

- [ ] Simplify main `Config` class in `__init__.py`
- [ ] Coordinate loader and validator
- [ ] Provide clean public API
- [ ] Maintain backward compatibility
- [ ] Test: existing code works
- [ ] Commit: "refactor(config): simplify main class"

**Phase 9: Update Imports**

- [ ] Find all config imports:
  ```bash
  grep -r "from.*config import" src/claude_mpm/ --include="*.py"
  ```
- [ ] Update to use new module
- [ ] Test all dependent code
- [ ] Commit: "refactor(config): update imports"

**Phase 10: Documentation**

- [ ] Add module docstrings
- [ ] Document configuration schema
- [ ] Add migration guide
- [ ] Update architecture docs
- [ ] Final test: `pytest tests/`
- [ ] Commit: "refactor(config): add documentation"

---

### Task 3.2: Large File Refactoring (5 files)

**Phase 1: Identify Large Files**

- [ ] Run command:
  ```bash
  find src/claude_mpm -name "*.py" -type f -exec wc -l {} + | \
    awk '$1 > 1000 {print $1, $2}' | \
    sort -rn > large_files.txt
  ```
- [ ] Review `large_files.txt`
- [ ] Prioritize files for refactoring

**Large Files Inventory:**

| Priority | File | Lines | Complexity | Estimated Effort |
|----------|------|-------|------------|------------------|
| 1 | `___` | ___ | High/Med/Low | __ hours |
| 2 | `___` | ___ | High/Med/Low | __ hours |
| 3 | `___` | ___ | High/Med/Low | __ hours |
| 4 | `___` | ___ | High/Med/Low | __ hours |
| 5 | `___` | ___ | High/Med/Low | __ hours |

**Phase 2: For Each Large File**

**File 1: `_________________`**

- [ ] Analyze file structure
- [ ] Identify logical sections
- [ ] Plan module breakdown
- [ ] Create module structure
- [ ] Extract sections incrementally
- [ ] Update imports
- [ ] Test after each extraction
- [ ] Document refactoring
- [ ] Commit with descriptive message

**File 2: `_________________`**

- [ ] Analyze file structure
- [ ] Identify logical sections
- [ ] Plan module breakdown
- [ ] Create module structure
- [ ] Extract sections incrementally
- [ ] Update imports
- [ ] Test after each extraction
- [ ] Document refactoring
- [ ] Commit with descriptive message

**File 3: `_________________`**

- [ ] Analyze file structure
- [ ] Identify logical sections
- [ ] Plan module breakdown
- [ ] Create module structure
- [ ] Extract sections incrementally
- [ ] Update imports
- [ ] Test after each extraction
- [ ] Document refactoring
- [ ] Commit with descriptive message

**File 4: `_________________`**

- [ ] Analyze file structure
- [ ] Identify logical sections
- [ ] Plan module breakdown
- [ ] Create module structure
- [ ] Extract sections incrementally
- [ ] Update imports
- [ ] Test after each extraction
- [ ] Document refactoring
- [ ] Commit with descriptive message

**File 5: `_________________`**

- [ ] Analyze file structure
- [ ] Identify logical sections
- [ ] Plan module breakdown
- [ ] Create module structure
- [ ] Extract sections incrementally
- [ ] Update imports
- [ ] Test after each extraction
- [ ] Document refactoring
- [ ] Commit with descriptive message

**Phase 3: Verification**

- [ ] Run command to verify no files >1,000 lines:
  ```bash
  find src/claude_mpm -name "*.py" -type f -exec wc -l {} + | \
    awk '$1 > 1000 {print $1, $2}'
  ```
- [ ] Should return no results
- [ ] All tests passing: `pytest tests/`
- [ ] Documentation updated
- [ ] Final commit: "refactor: complete large file restructuring"

---

### Task 3.3: Print Statement Migration Strategy

**Phase 1: Comprehensive Audit**

- [ ] Find all print statements:
  ```bash
  grep -rn "print(" src/claude_mpm/ --include="*.py" | \
    grep -v "# KEEP" > all_prints.txt
  ```
- [ ] Review each print statement
- [ ] Categorize:
  - CLI output (keep, use rich console)
  - Debugging (convert to logger.debug)
  - Status updates (convert to logger.info or progress bar)
  - Errors (convert to logger.error)

**Print Statement Inventory:**

| File | Line | Context | Action | Priority |
|------|------|---------|--------|----------|
| `___` | ___ | CLI output | Keep/Rich | Low |
| `___` | ___ | Debug | logger.debug | High |
| `___` | ___ | Status | logger.info | Med |
| `___` | ___ | Error | logger.error | High |

**Phase 2: Define Logging Strategy**

- [ ] Document logging levels usage:
  - DEBUG: Development/troubleshooting info
  - INFO: Progress/status updates
  - WARNING: Recoverable issues
  - ERROR: Error conditions
  - CRITICAL: System failures
- [ ] Document rich console usage for CLI
- [ ] Create migration examples
- [ ] Add to developer guide

**Phase 3: Replace Debug Prints**

- [ ] For each debug print:
  - [ ] File: `___`, Line: ___
    - [ ] Replace with `logger.debug(...)`
    - [ ] Test functionality
    - [ ] Commit: "fix: convert debug print to logging in ___"

**Phase 4: Replace Status Prints**

- [ ] For each status print:
  - [ ] File: `___`, Line: ___
    - [ ] Evaluate: logger.info or rich.progress?
    - [ ] Replace appropriately
    - [ ] Test functionality
    - [ ] Commit: "fix: convert status print to logging in ___"

**Phase 5: Enhance CLI Output**

- [ ] For each CLI print:
  - [ ] File: `___`, Line: ___
    - [ ] Consider using rich console
    - [ ] Add colors/formatting if helpful
    - [ ] Test user experience
    - [ ] Commit: "enhance: improve CLI output in ___"

**Phase 6: Add Progress Bars**

- [ ] Identify long-running operations
- [ ] Add rich.progress where appropriate
- [ ] Test progress display
- [ ] Commit: "enhance: add progress indicators"

**Phase 7: Documentation**

- [ ] Document logging strategy
- [ ] Add examples to developer guide
- [ ] Update contribution guidelines
- [ ] Commit: "docs: add logging guidelines"

**Phase 8: Verification**

- [ ] Run audit command again
- [ ] Verify only intentional prints remain
- [ ] All tests passing
- [ ] MCP mode tested (no stdout pollution)
- [ ] Final commit: "refactor: complete print statement migration"

---

## Priority 4: Long-Term Improvements Checklist

### Task 4.1: Type Hint Coverage Improvement

**Phase 1: Baseline Assessment**

- [ ] Run mypy on entire codebase:
  ```bash
  mypy src/claude_mpm/ --html-report mypy-report/
  ```
- [ ] Review HTML report
- [ ] Count total errors
- [ ] Categorize errors by type
- [ ] Set improvement goals

**Mypy Error Inventory:**

| Category | Count | Priority |
|----------|-------|----------|
| Missing return type | ___ | High |
| Missing parameter type | ___ | High |
| Using Any | ___ | Medium |
| Incompatible types | ___ | High |
| Other | ___ | Low |

**Phase 2: Fix High-Priority Errors**

- [ ] Fix missing return types:
  - [ ] File: `___`, Function: `___`
  - [ ] Add return type hint
  - [ ] Run mypy to verify
  - [ ] Repeat for all functions

- [ ] Fix missing parameter types:
  - [ ] File: `___`, Function: `___`
  - [ ] Add parameter type hints
  - [ ] Run mypy to verify
  - [ ] Repeat for all functions

**Phase 3: Create TypedDict Definitions**

- [ ] Identify complex dict returns
- [ ] Create TypedDict in `types.py`
- [ ] Replace dict[str, Any] with TypedDict
- [ ] Update function signatures
- [ ] Test type checking

**Example:**
```python
# Before
def get_config() -> dict[str, Any]:
    return {"key": "value", "count": 42}

# After
from typing import TypedDict

class ConfigDict(TypedDict):
    key: str
    count: int

def get_config() -> ConfigDict:
    return {"key": "value", "count": 42}
```

**Phase 4: Reduce Usage of Any**

- [ ] Find all uses of Any:
  ```bash
  grep -rn "Any" src/claude_mpm/ --include="*.py"
  ```
- [ ] Replace with specific types where possible
- [ ] Document remaining Any usage
- [ ] Run mypy to verify improvements

**Phase 5: Add Type Hints to New Code**

- [ ] Update coding guidelines
- [ ] Add pre-commit hook for type checking
- [ ] Review PRs for type hints
- [ ] Maintain >95% coverage going forward

**Phase 6: Documentation**

- [ ] Document type hinting standards
- [ ] Add examples to developer guide
- [ ] Update contribution guidelines
- [ ] Commit: "docs: add type hinting guidelines"

**Phase 7: Verification**

- [ ] Run mypy strict mode:
  ```bash
  mypy --strict src/claude_mpm/
  ```
- [ ] Generate coverage report
- [ ] Verify >95% coverage
- [ ] Document remaining gaps
- [ ] Final commit: "feat: achieve >95% type hint coverage"

---

### Task 4.2: Async/Await Optimization

**Phase 1: Identify I/O-Bound Operations**

- [ ] Audit codebase for I/O operations:
  - [ ] Network requests (HTTP, API calls)
  - [ ] File operations (reading, writing)
  - [ ] Database queries
  - [ ] External process calls

**I/O Operations Inventory:**

| Operation | File | Current | Async Benefit | Priority |
|-----------|------|---------|---------------|----------|
| GitHub API | `download_skills_api.py` | Sync | High | High |
| File I/O | `skills_service.py` | Sync | Medium | Medium |
| MCP calls | `mcp_gateway.py` | Async | N/A | N/A |
| Updates | `update_checker.py` | Sync | High | High |

**Phase 2: Add Async Dependencies**

- [ ] Add to `pyproject.toml`:
  ```toml
  aiohttp = "^3.9.0"  # Async HTTP
  aiofiles = "^23.2.0"  # Async file I/O
  ```
- [ ] Run: `poetry install`
- [ ] Update requirements

**Phase 3: Convert Network Operations**

**Example: GitHub API Downloads**

- [ ] Create async version in `download_skills_api.py`:
  ```python
  import aiohttp

  async def download_skill_async(self, url: str) -> bytes:
      async with aiohttp.ClientSession() as session:
          async with session.get(url, timeout=30) as response:
              return await response.read()

  async def download_skills_batch(self, urls: list[str]) -> list[bytes]:
      tasks = [self.download_skill_async(url) for url in urls]
      return await asyncio.gather(*tasks)
  ```

- [ ] Add async methods
- [ ] Keep sync methods for backward compatibility
- [ ] Test both sync and async versions
- [ ] Benchmark performance improvement
- [ ] Document async usage
- [ ] Commit: "feat: add async skill downloads"

**Phase 4: Convert File Operations**

**Example: Async File Reading**

- [ ] Create async file operations:
  ```python
  import aiofiles

  async def read_skill_metadata_async(self, path: Path) -> dict:
      async with aiofiles.open(path, 'r', encoding='utf-8') as f:
          content = await f.read()
      return self.parse_metadata(content)

  async def read_multiple_skills_async(
      self, paths: list[Path]
  ) -> list[dict]:
      tasks = [self.read_skill_metadata_async(p) for p in paths]
      return await asyncio.gather(*tasks)
  ```

- [ ] Add async file operations
- [ ] Keep sync versions for backward compatibility
- [ ] Test async operations
- [ ] Benchmark performance
- [ ] Commit: "feat: add async file operations"

**Phase 5: Update CLI Commands**

- [ ] Add async support to CLI:
  ```python
  import asyncio

  class SkillsCommand(BaseCommand):
      def run(self, args):
          if args.async_mode:
              return asyncio.run(self.run_async(args))
          return self.run_sync(args)

      async def run_async(self, args):
          # Async implementation
          pass

      def run_sync(self, args):
          # Sync implementation (backward compatible)
          pass
  ```

- [ ] Add async mode flag
- [ ] Implement async command versions
- [ ] Test both modes
- [ ] Update documentation
- [ ] Commit: "feat: add async mode to skills commands"

**Phase 6: Benchmarking**

- [ ] Create benchmarks:
  ```python
  import time

  def benchmark_sync():
      start = time.time()
      # Run sync version
      end = time.time()
      return end - start

  async def benchmark_async():
      start = time.time()
      # Run async version
      end = time.time()
      return end - start
  ```

- [ ] Run benchmarks
- [ ] Document performance improvements
- [ ] Add to test suite
- [ ] Commit: "perf: add async benchmarks"

**Phase 7: Documentation**

- [ ] Document async API usage
- [ ] Add async examples
- [ ] Update developer guide
- [ ] Add migration guide for users
- [ ] Commit: "docs: add async usage guide"

---

### Task 4.3: Docstring Standardization

**Phase 1: Choose Standard**

- [ ] Review options:
  - Google style (recommended)
  - NumPy style
  - Sphinx style
- [ ] Choose: **Google style** ✓
- [ ] Document decision
- [ ] Add to coding standards

**Phase 2: Create Templates**

- [ ] Create docstring templates:

**Function Template:**
```python
def function_name(param1: str, param2: int = 0) -> dict[str, Any]:
    """Brief one-line description.

    Longer description providing more detail about what the function
    does and how it works. Can span multiple paragraphs if needed.

    Args:
        param1: Description of first parameter.
        param2: Description of second parameter. Defaults to 0.

    Returns:
        Description of return value with structure details:
        {
            "key1": "description",
            "key2": "description"
        }

    Raises:
        ValueError: When param1 is empty.
        TypeError: When param2 is negative.

    Example:
        >>> result = function_name("test", 42)
        >>> print(result["key1"])
        expected_value

    Note:
        Any important implementation notes or warnings.
    """
    pass
```

**Class Template:**
```python
class ClassName:
    """Brief one-line description of class purpose.

    Longer description of what the class does, its responsibilities,
    and how it fits into the overall system.

    Attributes:
        attr1: Description of first attribute.
        attr2: Description of second attribute.

    Example:
        >>> obj = ClassName(param="value")
        >>> obj.method()
        result
    """
    pass
```

**Phase 3: Audit Existing Docstrings**

- [ ] Run pydocstyle:
  ```bash
  pydocstyle src/claude_mpm/ > docstring_issues.txt
  ```
- [ ] Review issues
- [ ] Categorize by severity
- [ ] Prioritize fixes

**Docstring Audit Results:**

| Category | Count | Priority |
|----------|-------|----------|
| Missing docstrings | ___ | High |
| Incomplete docstrings | ___ | Medium |
| Wrong format | ___ | Medium |
| Missing examples | ___ | Low |

**Phase 4: Add Missing Docstrings**

- [ ] For each file with missing docstrings:
  - [ ] File: `___`
    - [ ] Add module docstring
    - [ ] Add class docstrings
    - [ ] Add function docstrings
    - [ ] Run pydocstyle to verify
    - [ ] Commit: "docs: add docstrings to ___"

**Phase 5: Standardize Format**

- [ ] For each file with format issues:
  - [ ] File: `___`
    - [ ] Convert to Google style
    - [ ] Add missing sections (Args, Returns, Raises)
    - [ ] Add examples where helpful
    - [ ] Run pydocstyle to verify
    - [ ] Commit: "docs: standardize docstrings in ___"

**Phase 6: Add Examples**

- [ ] Identify complex functions
- [ ] Add example sections
- [ ] Test examples work correctly
- [ ] Commit: "docs: add docstring examples"

**Phase 7: Generate API Documentation**

- [ ] Install pdoc:
  ```bash
  poetry add --group dev pdoc
  ```
- [ ] Generate docs:
  ```bash
  pdoc --html --output-dir docs/api src/claude_mpm/
  ```
- [ ] Review generated docs
- [ ] Fix any rendering issues
- [ ] Add to CI/CD
- [ ] Commit: "docs: generate API documentation"

**Phase 8: Automation**

- [ ] Add pydocstyle to pre-commit:
  ```yaml
  - repo: https://github.com/PyCQA/pydocstyle
    rev: 6.3.0
    hooks:
      - id: pydocstyle
        args: [--convention=google]
  ```
- [ ] Update CI/CD to check docstrings
- [ ] Document standards in contribution guide
- [ ] Commit: "ci: enforce docstring standards"

---

## Progress Dashboard

### Overall Progress

**Priority 1** (Quick Wins):
```
Progress: [          ] 0% (0/3 tasks)
Estimated: 1 hour remaining
Status: Not started
```

**Priority 2** (Short-Term):
```
Progress: [          ] 0% (0/3 tasks)
Estimated: 1-2 days remaining
Status: Not started
```

**Priority 3** (Medium-Term):
```
Progress: [          ] 0% (0/3 tasks)
Estimated: 1-2 weeks remaining
Status: Not started
```

**Priority 4** (Long-Term):
```
Progress: [          ] 0% (0/3 tasks)
Estimated: Ongoing
Status: Not started
```

---

## How to Use This Checklist

### For Each Task:

1. **Read the entire task section** before starting
2. **Check off items** as you complete them
3. **Commit frequently** with descriptive messages
4. **Test after each step** to catch issues early
5. **Update this document** with any changes or additions
6. **Document any blockers** or issues encountered

### Task Status Indicators:

- [ ] Not started
- [→] In progress
- [x] Complete
- [!] Blocked/Issue
- [~] Skipped/Deferred

### Update Progress:

When you complete a task, update the progress dashboard:

```markdown
**Priority X** (Description):
```
Progress: [####      ] 40% (2/5 tasks)
Estimated: X hours remaining
Status: In progress - working on Task X.Y
```
```

---

## Notes and Blockers

### Current Blockers:
(None yet)

### Decisions Needed:
(None yet)

### Additional Issues Found:
(None yet)

---

*This checklist is a living document. Update it as you work!*
*Last updated: 2025-11-08 12:23:04 EST*
