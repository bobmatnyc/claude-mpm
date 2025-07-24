# Claude-MPM Codebase Visualizations

# Module Dependency Graph

```mermaid
graph TD
    hooks --> utils
    orchestration --> _version
    services --> hooks
    services --> core
    services --> utils
    
    %% Styling
    classDef core fill:#f9f,stroke:#333,stroke-width:2px
    classDef service fill:#bbf,stroke:#333,stroke-width:2px
    classDef agent fill:#bfb,stroke:#333,stroke-width:2px
    
    class core core
    class services service
    class agents agent
```
# Architectural Layers

```mermaid
graph TB
    subgraph Presentation Layer
        CLI[CLI Interface]
    end
    
    subgraph Application Layer
        ORCH[Orchestration]
        HOOKS[Hooks]
    end
    
    subgraph Domain Layer
        AGENTS[Agents]
        SERVICES[Services]
    end
    
    subgraph Infrastructure Layer
        CORE[Core]
        CONFIG[Config]
        UTILS[Utils]
    end
    
    CLI --> ORCH
    ORCH --> HOOKS
    ORCH --> AGENTS
    AGENTS --> SERVICES
    SERVICES --> CORE
    HOOKS --> SERVICES
    CORE --> CONFIG
    CORE --> UTILS
```
# Key Class Hierarchies

```mermaid
classDiagram
    ABC <|-- IServiceContainer
    ABC <|-- IConfigurationService
    ABC <|-- IConfigurationManager
    ABC <|-- ICacheService
    ABC <|-- IHealthMonitor
    ABC <|-- IAgentRegistry
    ABC <|-- IPromptCache
    ABC <|-- ITemplateManager
    ABC <|-- IServiceFactory
    ABC <|-- IStructuredLogger
    ABC <|-- IServiceLifecycle
    ABC <|-- IErrorHandler
    ABC <|-- IPerformanceMonitor
    ABC <|-- IEventBus
    ABC <|-- BaseService
    ABC <|-- EnhancedBaseService
    ABC <|-- BaseHook
    ABC <|-- BaseSectionGenerator
    Exception <|-- ConfigAliasError
    Exception <|-- GitOperationError
    ConfigAliasError <|-- AliasNotFoundError
    ConfigAliasError <|-- DuplicateAliasError
    ConfigAliasError <|-- InvalidDirectoryError
    Enum <|-- LaunchMode
    Enum <|-- AgentPriority
    Enum <|-- TaskStatus
    Enum <|-- WorktreeStatus
    Enum <|-- PromptTemplate
    Enum <|-- HookType
    Enum <|-- ProcessStatus
    Enum <|-- BaseAgentSection
    Enum <|-- LifecycleOperation
    Enum <|-- LifecycleState
    Enum <|-- ProfileTier
    Enum <|-- ProfileStatus
    Enum <|-- BranchStrategyType
    Enum <|-- BranchType
    Enum <|-- VersionBumpType
    Enum <|-- ConflictType
    Enum <|-- ResolutionStrategy
    Enum <|-- ModificationType
    Enum <|-- ModificationTier
    Enum <|-- ParentDirectoryAction
    Enum <|-- ParentDirectoryContext
    Enum <|-- DeploymentContext
    IServiceLifecycle <|-- EnhancedBaseService
    str <|-- AgentPriority
    str <|-- TaskStatus
    str <|-- WorktreeStatus
    str <|-- BaseAgentSection
    BaseHook <|-- SubmitHook
    BaseHook <|-- PreDelegationHook
    BaseHook <|-- PostDelegationHook
    BaseHook <|-- TicketExtractionHook
    PostDelegationHook <|-- ResultValidatorHook
    PostDelegationHook <|-- ResultMetricsHook
    TicketExtractionHook <|-- AutoTicketExtractionHook
    TicketExtractionHook <|-- TicketPriorityAnalyzerHook
    PreDelegationHook <|-- ContextFilterHook
    PreDelegationHook <|-- AgentCapabilityEnhancerHook
    class BaseService {
        +__init__()
        +start()
        +stop()
        +restart()
        +health_check()
    }
    class AgentRegistry {
        +__init__()
        +discover_agents()
        +get_agent()
        +list_agents()
        +listAgents()
    }
```
# Code Hotspots

```mermaid
graph TD
    subgraph Complex Functions
    F0["main<br/>Complexity: 12"]
    F0:::complex
    F1["test_claude_modes<br/>Complexity: 11"]
    F1:::complex
    F2["main<br/>Complexity: 16"]
    F2:::complex
    F3["run_session<br/>Complexity: 19"]
    F3:::complex
    F4["_load_framework_content<br/>Complexity: 23"]
    F4:::complex
    end
    
    subgraph God Classes
    C0["EnhancedBaseService<br/>34 methods"]
    C0:::godclass
    C1["SharedPromptCache<br/>21 methods"]
    C1:::godclass
    C2["AgentLifecycleManager<br/>27 methods"]
    C2:::godclass
    C3["BranchStrategyManager<br/>23 methods"]
    C3:::godclass
    C4["SemanticVersionManager<br/>22 methods"]
    C4:::godclass
    C5["ConflictResolutionManager<br/>23 methods"]
    C5:::godclass
    C6["ParentDirectoryManager<br/>26 methods"]
    C6:::godclass
    end
    
    subgraph High Coupling
    HC0["subprocess_orchestrator.py<br/>29 imports"]
    HC0:::coupling
    HC1["orchestrator.py<br/>28 imports"]
    HC1:::coupling
    HC2["cli.py<br/>26 imports"]
    HC2:::coupling
    end
    
    classDef complex fill:#f99,stroke:#333,stroke-width:2px
    classDef godclass fill:#ff9,stroke:#333,stroke-width:2px
    classDef coupling fill:#9ff,stroke:#333,stroke-width:2px
```

# Improvement Roadmap

```mermaid
gantt
    title Claude-MPM Improvement Roadmap
    dateFormat YYYY-MM-DD
    section Phase 1 - Foundation
    Code Complexity Reduction :a1, 2025-01-01, 30d
    Test Coverage Improvement :a2, after a1, 30d
    
    section Phase 2 - Architecture
    Layer Refactoring :b1, after a2, 20d
    Dependency Injection :b2, after b1, 20d
    API Consolidation :b3, after b1, 15d
    
    section Phase 3 - Optimization
    Performance Tuning :c1, after b2, 15d
    Async Optimization :c2, after c1, 10d
    Caching Strategy :c3, after c1, 10d
```

## Key Insights from Visualizations

1. **Module Dependencies**: The codebase shows clear separation between layers
2. **Architecture**: Well-defined layers with orchestration at the top
3. **Hotspots**: Several areas need refactoring for maintainability
4. **Improvement Path**: Phased approach starting with complexity reduction

## Next Steps

1. Create epic tickets for each improvement phase
2. Prioritize complexity reduction in identified hotspots
3. Establish metrics for tracking improvement progress
4. Set up automated quality gates to prevent regression