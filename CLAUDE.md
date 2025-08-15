# Claude MPM Development Guidelines

This document provides development guidelines for the claude-mpm project codebase.

## Project Overview

Claude MPM (Multi-Agent Project Manager) is a framework that extends Claude Desktop with multi-agent orchestration capabilities, featuring a modern service-oriented architecture with interface-based contracts and dependency injection.

## Architecture (v3.8.2+)

Following the TSK-0053 refactoring, Claude MPM features:

- **Service-Oriented Architecture**: Five specialized service domains
- **Interface-Based Contracts**: All services implement explicit interfaces  
- **Dependency Injection**: Service container with automatic resolution
- **Performance Optimizations**: Lazy loading, multi-level caching, connection pooling
- **Security Framework**: Input validation, path traversal prevention, secure operations
- **Backward Compatibility**: Lazy imports maintain existing import paths

## Key Documentation

### Architecture and Development
- 🏗️ **Architecture Overview**: See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for service-oriented architecture
- 📁 **Project Structure**: See [docs/STRUCTURE.md](docs/STRUCTURE.md) for file organization
- 🔧 **Service Layer Guide**: See [docs/developer/SERVICES.md](docs/developer/SERVICES.md) for service development
- ⚡ **Performance Guide**: See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for optimization patterns
- 🔒 **Security Guide**: See [docs/SECURITY.md](docs/SECURITY.md) for security framework
- 🧪 **Testing Guide**: See [docs/TESTING.md](docs/TESTING.md) for testing strategies
- 📚 **Migration Guide**: See [docs/MIGRATION.md](docs/MIGRATION.md) for upgrade instructions

### Operations and Quality
- 🧪 **Quality Assurance**: See [docs/QA.md](docs/QA.md) for testing guidelines
- 🚀 **Deployment**: See [docs/DEPLOY.md](docs/DEPLOY.md) for versioning and deployment
- 📊 **Logging**: See [docs/RESPONSE_LOGGING_CONFIG.md](docs/RESPONSE_LOGGING_CONFIG.md) for response logging configuration
- 🔢 **Versioning**: See [docs/VERSIONING.md](docs/VERSIONING.md) for version management
- 🧠 **Memory System**: See [docs/MEMORY.md](docs/MEMORY.md) for agent memory management

## Development Guidelines

### Critical Principles

**🔴 NEVER ASSUME - ALWAYS VERIFY**
- **NEVER assume** file locations, configurations, or implementations
- **ALWAYS verify** by reading actual files and checking current state
- **ALWAYS check** existing code patterns before implementing
- **NEVER guess** at directory structures or file contents
- **ALWAYS confirm** dependencies and imports exist before using them

### Project Structure Requirements

1. **File Organization**: Always refer to `docs/STRUCTURE.md` when creating new files
   - **Scripts**: ALL scripts go in `/scripts/`, NEVER in project root
   - **Tests**: ALL tests go in `/tests/`, NEVER in project root
   - **Python modules**: Always under `/src/claude_mpm/`
   
2. **Import Conventions**: 
   - Use full package names: `from claude_mpm.module import ...`
   - Never use relative imports in main code
   - Check existing patterns before adding new imports

### Testing Requirements

**After significant changes, always run:**
```bash
# Quick E2E tests
./scripts/run_e2e_tests.sh

# Full test suite
./scripts/run_all_tests.sh

# Lint and type checks
./scripts/run_lint.sh
```

See [docs/QA.md](docs/QA.md) for detailed testing procedures.

### Key System Components

When modifying the codebase, understand these core systems:

1. **Framework Loader** (`src/claude_mpm/core/framework_loader.py`)
   - Loads PM instructions from `src/claude_mpm/agents/INSTRUCTIONS.md`
   - Manages agent discovery and capabilities
   - DO NOT duplicate CLAUDE.md content here

2. **Hook System** (`src/claude_mpm/hooks/`)
   - Extensibility through pre/post hooks
   - Response logging via `SubagentStop` and `Stop` events
   - Structured JSON responses for proper logging

3. **Services Layer** (`src/claude_mpm/services/`)
   - **Core Services**: Foundation interfaces and base classes
   - **Agent Services**: Agent lifecycle, deployment, and management
   - **Communication Services**: Real-time WebSocket and SocketIO
   - **Project Services**: Project analysis and workspace management
   - **Infrastructure Services**: Logging, monitoring, and error handling
   - **Legacy Structure**: Maintained for backward compatibility

4. **CLI System** (`src/claude_mpm/cli/`)
   - Modular command structure
   - See [CLI Architecture](src/claude_mpm/cli/README.md) for adding new commands

### Common Development Tasks

#### Adding a New Service
1. **Create Interface**: Define service contract in `src/claude_mpm/services/core/interfaces.py`
2. **Implement Service**: Create implementation in appropriate service domain
3. **Register Service**: Add to service container if using dependency injection
4. **Add Tests**: Create unit, integration, and interface compliance tests
5. **Update Documentation**: Document service in [docs/developer/SERVICES.md](docs/developer/SERVICES.md)

#### Service Development Patterns
```python
# 1. Define interface
class IMyService(ABC):
    @abstractmethod
    def my_operation(self, param: str) -> bool:
        pass

# 2. Implement service
class MyService(BaseService, IMyService):
    def __init__(self, dependency: IDependency):
        super().__init__("MyService")
        self.dependency = dependency
    
    async def initialize(self) -> bool:
        # Initialize service
        return True
    
    def my_operation(self, param: str) -> bool:
        # Implementation
        return True

# 3. Register in container
container.register(IMyService, MyService, singleton=True)

# 4. Test interface compliance
def test_service_implements_interface():
    service = MyService(mock_dependency)
    assert isinstance(service, IMyService)
```

#### Modifying PM Instructions
1. Edit `src/claude_mpm/agents/INSTRUCTIONS.md` for PM behavior
2. Edit `src/claude_mpm/agents/BASE_PM.md` for framework requirements
3. Test with `./claude-mpm run` in interactive mode
4. Update tests for PM behavior changes

#### Adding CLI Commands
1. Create command module in `src/claude_mpm/cli/commands/`
2. Register in `src/claude_mpm/cli/parser.py`
3. Follow existing command patterns
4. Use dependency injection for service access
5. Add comprehensive tests and documentation

#### Performance Optimization
1. **Identify Bottlenecks**: Use profiling tools and performance tests
2. **Implement Caching**: Add appropriate caching layers
3. **Lazy Loading**: Defer expensive operations until needed
4. **Connection Pooling**: Reuse expensive connections
5. **Monitor Metrics**: Track performance over time

## Common Issues and Solutions

### Architecture-Related Issues
1. **Service Resolution Errors**: Ensure services are registered in container before resolving
2. **Interface Compliance**: Verify services implement all required interface methods
3. **Circular Dependencies**: Use dependency injection and avoid circular imports
4. **Cache Performance**: Monitor cache hit rates and adjust TTL settings

### Legacy Compatibility Issues
1. **Import Errors**: Use new service paths or rely on lazy import compatibility
2. **Service Instantiation**: Use service container instead of direct instantiation
3. **Configuration Schema**: Update config files to new structure

### Performance Issues
1. **Slow Startup**: Check lazy loading implementation and cache warming
2. **Memory Usage**: Monitor service memory consumption and optimization
3. **Cache Misses**: Verify cache configuration and invalidation strategies

### Traditional Issues
1. **Import Errors**: Ensure virtual environment is activated and PYTHONPATH includes `src/`
2. **Hook Service Errors**: Check port availability (8080-8099)
3. **Version Errors**: Run `pip install -e .` to ensure proper installation
4. **Agent Loading**: Check `.claude/agents/` for deployed agents

## Contributing

### Code Quality Standards
1. **Follow Architecture**: Use service-oriented patterns and interface-based design
2. **Structure Compliance**: Follow the structure in `docs/STRUCTURE.md`
3. **Interface Design**: Define clear contracts for all services
4. **Dependency Injection**: Use service container for loose coupling
5. **Performance**: Implement caching and lazy loading where appropriate
6. **Security**: Follow security guidelines in `docs/SECURITY.md`

### Testing Requirements
1. **Unit Tests**: Test individual services and components (85%+ coverage)
2. **Integration Tests**: Test service interactions and interfaces
3. **Performance Tests**: Verify caching and optimization features
4. **Security Tests**: Validate input validation and security measures
5. **E2E Tests**: Test complete user workflows

### Documentation Standards
1. **Service Documentation**: Document all interfaces and implementations
2. **Architecture Updates**: Keep architecture docs current
3. **Migration Guides**: Document breaking changes and upgrade paths
4. **Performance Metrics**: Document performance expectations and benchmarks

### Version Management

Claude MPM uses a dual tracking system as of v3.9.5:
- **VERSION file**: Contains semantic version only (e.g., "3.9.5")
- **BUILD_NUMBER file**: Contains serial build number only (e.g., "275")
- **Combined display**: Three formats for different contexts:
  - Development: `3.9.5+build.275` (PEP 440 compliant)
  - UI/Logging: `v3.9.5-build.275` (user-friendly)
  - PyPI Release: `3.9.5` (clean semantic version)

Use [Conventional Commits](https://www.conventionalcommits.org/) for automatic versioning:
- `feat:` for new features (minor version bump)
- `fix:` for bug fixes (patch version bump)
- `feat!:` or `BREAKING CHANGE:` for breaking changes (major version bump)
- `perf:` for performance improvements
- `refactor:` for code refactoring
- `docs:` for documentation updates

Build numbers increment automatically with every substantial code change via git hooks.

## Deployment Process

See [docs/DEPLOY.md](docs/DEPLOY.md) for the complete deployment process:
- Version management with `./scripts/manage_version.py`
- Building and publishing to PyPI
- Creating GitHub releases
- Post-deployment verification

## TSK-0053 Refactoring Achievements

The service layer architecture refactoring delivered:

### Technical Achievements
- **Service-Oriented Architecture**: Complete redesign with five specialized service domains
- **Interface-Based Contracts**: All major services implement explicit interfaces
- **Dependency Injection**: Service container with automatic dependency resolution
- **50-80% Performance Improvement**: Through lazy loading and intelligent caching
- **Enhanced Security**: Comprehensive input validation and sanitization framework
- **Backward Compatibility**: Lazy imports maintain existing import paths

### Quality Improvements
- **Better Testability**: Interface-based architecture enables easy mocking and testing
- **Improved Maintainability**: Clear separation of concerns and service boundaries
- **Enhanced Reliability**: Comprehensive testing with 85%+ coverage target
- **Developer Experience**: Rich documentation and migration guides

### Future-Proofing
- **Scalability**: Service-oriented design supports future growth
- **Extensibility**: Plugin architecture through interfaces and hooks
- **Modularity**: Clear service boundaries enable independent development
- **Performance**: Intelligent caching and resource optimization foundations

## v3.9.5 Updates

### Version Tracking System Enhancement
- **BUILD_NUMBER file**: Replaces BUILDVERSION for cleaner naming
- **Dual tracking**: VERSION (semantic) + BUILD_NUMBER (serial)
- **Three display formats**: Development, UI/Logging, and PyPI Release
- **Automatic incrementing**: Git hooks increment build numbers for code changes

### New Features
- **cleanup-memory command**: New CLI command to manage Claude conversation history
- **Memory management**: Addresses 2GB+ memory usage from large .claude.json files
- **Archive system**: Safely archive old conversations while keeping recent ones active

## Important Notes

- This file (CLAUDE.md) contains ONLY development guidelines for this project
- Framework features and usage are documented in the framework itself
- Claude Desktop automatically reads this file - keep it focused on development tasks
- Do not include end-user documentation or framework features here
- The refactored architecture enables faster development and better code quality