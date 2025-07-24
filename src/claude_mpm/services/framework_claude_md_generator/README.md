# Framework CLAUDE.md Generator

This directory contains the refactored framework CLAUDE.md generator service, originally a single 1,267-line file.

## Structure

### Core Modules

- **`__init__.py`** (~250 lines) - Main facade class that coordinates all functionality
- **`version_manager.py`** (~100 lines) - Handles version parsing, incrementing, and comparison
- **`content_assembler.py`** (~120 lines) - Assembles sections and applies template variables
- **`content_validator.py`** (~80 lines) - Validates generated content structure and completeness
- **`deployment_manager.py`** (~80 lines) - Handles deployment to parent directories
- **`section_manager.py`** (~60 lines) - Manages section registration, ordering, and updates

### Section Generators

The `section_generators/` subdirectory contains individual generators for each section:

- **`__init__.py`** - Base classes and registry
- **`header.py`** - Header with version metadata
- **`role_designation.py`** - AI Assistant role designation
- **`agents.py`** (~570 lines) - Comprehensive agents documentation (largest section)
- **`todo_task_tools.py`** - Todo and Task Tools integration
- **`claude_pm_init.py`** - Claude-PM initialization procedures
- **`orchestration_principles.py`** - Core orchestration principles
- **`subprocess_validation.py`** - Subprocess validation protocol
- **`delegation_constraints.py`** - Critical delegation constraints
- **`environment_config.py`** - Environment configuration
- **`troubleshooting.py`** - Troubleshooting guide
- **`core_responsibilities.py`** - Core responsibilities list
- **`footer.py`** - Footer with metadata

## Usage

The API remains unchanged from the original implementation:

```python
from claude_pm.services.framework_claude_md_generator import FrameworkClaudeMdGenerator

# Create generator instance
generator = FrameworkClaudeMdGenerator()

# Generate content
content = generator.generate(
    current_content=existing_content,  # Optional: for version auto-increment
    template_variables={'PLATFORM': 'darwin', 'PYTHON_CMD': 'python3'}
)

# Deploy to parent directory
success, message = generator.deploy_to_parent(Path('/parent/dir'))

# Update a section
generator.update_section('agents', 'Custom agents content')

# Add custom section
generator.add_custom_section('custom', 'Custom content', after='agents')
```

## Design Benefits

1. **Modularity**: Each concern is separated into its own module
2. **Maintainability**: Smaller, focused modules are easier to understand and modify
3. **Testability**: Individual components can be tested in isolation
4. **Extensibility**: New section generators can be added easily
5. **Performance**: Section generators are loaded on demand
6. **Backward Compatibility**: Original API preserved through facade pattern

## Section Generator Pattern

To add a new section generator:

1. Create a new file in `section_generators/`
2. Inherit from `BaseSectionGenerator`
3. Implement the `generate()` method
4. Register in `section_generators/__init__.py`

Example:
```python
from . import BaseSectionGenerator

class CustomSectionGenerator(BaseSectionGenerator):
    def generate(self, data: Dict[str, Any]) -> str:
        return "## Custom Section\n\nContent here..."
```

## Refactoring Summary

- **Original**: 1,267 lines in a single file
- **Refactored**: ~250 lines in main module + well-organized submodules
- **Total line reduction**: Main module reduced by 80%
- **Improved organization**: 13 focused modules instead of 1 large file