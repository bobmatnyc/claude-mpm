# Single-Tier Agent System Architecture

Design decisions, rationale, and architecture for the single-tier agent system.

## Table of Contents

- [Executive Summary](#executive-summary)
- [Design Goals](#design-goals)
- [System Architecture](#system-architecture)
- [Design Decisions](#design-decisions)
- [Trade-Offs](#trade-offs)
- [Performance Characteristics](#performance-characteristics)
- [Future Enhancements](#future-enhancements)

## Executive Summary

The single-tier agent system replaces Claude MPM's complex 4-tier hierarchy with a simplified Git-based architecture. All agents deploy to a single location (`.claude/agents/`) with priority-based conflict resolution instead of tier-based precedence.

**Key Changes**:
- **4 tiers → 1 tier**: Simplified deployment model
- **Embedded templates → Git repositories**: All agents from version-controlled sources
- **Tier precedence → Priority numbers**: Clear, configurable conflict resolution
- **Static discovery → Dynamic sync**: ETag-based incremental updates

**Impact**:
- **Reduced Complexity**: ~2,000 LOC eliminated from multi-source discovery
- **Improved Clarity**: Single deployment location, clear precedence rules
- **Enhanced Flexibility**: Unlimited Git repositories with priority control
- **Better Performance**: ETag caching reduces bandwidth by 95%

## Design Goals

### Primary Goals

1. **Simplicity**: Reduce system complexity from 4-tier to 1-tier
2. **Transparency**: All agents from version-controlled Git sources
3. **Flexibility**: Support unlimited custom repositories with priority control
4. **Performance**: Efficient sync with ETag-based HTTP caching
5. **Compatibility**: Smooth migration path from old system

### Non-Goals

1. **Git clone support**: Use HTTP API only (no local git operations)
2. **Offline-first**: Rely on network with cache fallback
3. **Custom sync protocols**: GitHub HTTP only (for now)
4. **Complex version pinning**: Use branch/commit-based strategies later

## System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        User/CLI Layer                         │
│  Commands: source add/remove/sync, agents deploy-*           │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Configuration Layer                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ AgentSourceConfiguration                               │  │
│  │ - Load/save YAML                                       │  │
│  │ - Manage GitRepository list                            │  │
│  │ - System repo on/off                                   │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                        │
│  ┌─────────────────────────┐  ┌─────────────────────────┐   │
│  │ AgentSelectionService   │  │ SingleTierDeployment    │   │
│  │ - Minimal mode          │  │ - Sync all sources      │   │
│  │ - Auto-configure mode   │  │ - Deploy all agents     │   │
│  │ - Toolchain detection   │  │ - Priority resolution   │   │
│  └────────────┬────────────┘  └───────────┬─────────────┘   │
│               └────────────────────────────┘                  │
│                                │                              │
│                                ▼                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ GitSourceManager                                        │ │
│  │ - Multi-repository sync                                 │ │
│  │ - Agent discovery                                       │ │
│  │ - Cache management                                      │ │
│  └───────────────────────┬─────────────────────────────────┘ │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                       Data/Cache Layer                        │
│  ┌────────────────────┐  ┌──────────────────────────────┐   │
│  │ GitRepository      │  │ Local Cache                  │   │
│  │ - URL              │  │ ~/.claude-mpm/cache/         │   │
│  │ - Subdirectory     │  │ {owner}/{repo}/{subdir}/     │   │
│  │ - Priority         │  │ - Markdown agent files       │   │
│  │ - ETag             │  │ - ETag metadata              │   │
│  └────────────────────┘  └──────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**Configuration Layer**:
- Load/save YAML configuration
- Manage repository list
- Provide system repository
- Validate configuration

**Orchestration Layer**:
- Coordinate sync and deployment
- Implement selection strategies (minimal, auto-configure)
- Resolve priority conflicts
- Deploy to `.claude/agents/`

**Data Layer**:
- Model Git repositories
- Cache downloaded agents
- Track sync state (ETags)
- Discover cached agents

### Data Flow

**Startup Sync Flow**:

```
1. Application Startup
   │
   ├─> Load AgentSourceConfiguration
   │   └─> Parse YAML config
   │       └─> Create GitRepository instances
   │
   ├─> Get Enabled Repositories
   │   ├─> System repo (if not disabled)
   │   └─> Custom repos (if enabled)
   │
   ├─> Sync Repositories (GitSourceManager)
   │   │
   │   ├─> For each repository:
   │   │   ├─> Build raw GitHub URL
   │   │   ├─> Check ETag cache
   │   │   ├─> HTTP GET with If-None-Match
   │   │   ├─> Download if 200 OK (changed)
   │   │   ├─> Skip if 304 (unchanged)
   │   │   └─> Update cache and ETag
   │   │
   │   └─> Discover agents in cache
   │
   └─> Ready for Deployment
```

**Deployment Flow**:

```
1. Deploy Command (deploy-all, deploy-minimal, deploy-auto)
   │
   ├─> Determine Agent Set
   │   ├─> deploy-all: All available agents
   │   ├─> deploy-minimal: 6 core agents
   │   └─> deploy-auto: Toolchain-detected agents
   │
   ├─> Resolve Priority Conflicts
   │   ├─> Group agents by name
   │   ├─> For each name, select lowest priority
   │   └─> Build deployment map
   │
   ├─> Deploy Agents
   │   ├─> For each agent:
   │   │   ├─> Read from cache
   │   │   ├─> Write to .claude/agents/
   │   │   └─> Log deployment
   │   │
   │   └─> Report results
   │
   └─> Deployment Complete
```

## Design Decisions

### Decision 1: Git-Based Sources

**Decision**: Use Git repositories (via HTTP API) as the primary agent source.

**Rationale**:
- **Version Control**: Full history and change tracking
- **Collaboration**: Easy sharing and contribution
- **Distribution**: Simple HTTP access (no authentication for public repos)
- **Validation**: Markdown format with structured YAML frontmatter
- **Ecosystem**: Leverage existing GitHub infrastructure

**Alternatives Considered**:

1. **Embedded Templates** (old system)
   - ❌ Requires package updates to get new agents
   - ❌ No customization without forking
   - ❌ Version coupling with Claude MPM releases

2. **NPM Packages**
   - ❌ Requires Node.js ecosystem
   - ❌ Complex dependency management
   - ❌ Overkill for markdown files

3. **Dedicated Agent Registry**
   - ❌ Infrastructure overhead
   - ❌ Authentication complexity
   - ❌ Single point of failure

**Trade-Offs**:
- ✅ Pro: Version control and collaboration
- ✅ Pro: No infrastructure overhead
- ✅ Pro: Familiar workflow (Git)
- ⚠️ Con: Requires network for updates
- ⚠️ Con: GitHub-specific (for now)

### Decision 2: Single-Tier Deployment

**Decision**: Deploy all agents to one location (`.claude/agents/`) with priority-based resolution.

**Rationale**:
- **Simplicity**: One deployment location vs. four
- **Clarity**: Easy to inspect what's deployed
- **Predictability**: Priority numbers are explicit and clear
- **Maintainability**: Less code to manage (~2,000 LOC eliminated)

**Alternatives Considered**:

1. **Keep 4-Tier System**
   - ❌ Complex precedence rules (PROJECT > REMOTE > USER > SYSTEM)
   - ❌ Hard to understand which agent wins
   - ❌ Maintenance burden (discovery, cleanup, version comparison)

2. **2-Tier System** (project + user)
   - ⚠️ Still requires tier precedence logic
   - ⚠️ User-level agents less useful than Git repos
   - ✅ Simpler than 4-tier, but not as simple as 1-tier

3. **No Project-Level Override**
   - ❌ Reduces flexibility
   - ❌ Can't customize per-project
   - ❌ Not backward compatible

**Trade-Offs**:
- ✅ Pro: Dramatically simpler
- ✅ Pro: Clear precedence (priority numbers)
- ✅ Pro: Less code to maintain
- ⚠️ Con: Breaking change (migration required)
- ⚠️ Con: Priority conflicts less obvious than tiers

### Decision 3: Priority-Based Conflict Resolution

**Decision**: Use numeric priority (lower = higher precedence) instead of tier-based precedence.

**Rationale**:
- **Explicit**: Priority numbers are clear and configurable
- **Flexible**: Unlimited sources with fine-grained control
- **Predictable**: Well-understood algorithm (min priority wins)
- **Familiar**: Many systems use priority queues

**Alternatives Considered**:

1. **Tier-Based** (old system)
   - ❌ Limited to 4 tiers
   - ❌ Hard-coded precedence
   - ❌ No fine-grained control

2. **Last-Wins** (latest sync wins)
   - ❌ Non-deterministic
   - ❌ Unpredictable behavior
   - ❌ No user control

3. **Version-Based** (highest version wins)
   - ❌ Requires semantic versioning
   - ❌ Can't override with custom versions
   - ❌ Complex comparison logic

**Trade-Offs**:
- ✅ Pro: Explicit and configurable
- ✅ Pro: Unlimited sources
- ✅ Pro: Simple algorithm
- ⚠️ Con: Requires understanding priority ranges
- ⚠️ Con: Ties broken by order (not explicit)

### Decision 4: ETag-Based HTTP Caching

**Decision**: Use HTTP ETags for incremental sync with conditional requests.

**Rationale**:
- **Efficient**: ~95% bandwidth reduction after first sync
- **Standard**: HTTP 304 Not Modified is well-supported
- **Simple**: No custom protocol or state management
- **Fast**: 100-200ms sync time (mostly network latency)

**Alternatives Considered**:

1. **Git Clone**
   - ❌ Heavy: Full repository clone (~MB vs ~KB)
   - ❌ Complex: Requires git binary and state management
   - ❌ Slow: Initial clone takes seconds

2. **Polling Without Caching**
   - ❌ Wasteful: Re-downloads unchanged files
   - ❌ Slow: 500-800ms every sync
   - ❌ Bandwidth: ~200KB every sync

3. **Timestamp-Based**
   - ⚠️ Less reliable than content-based (ETag)
   - ⚠️ Requires server support for Last-Modified
   - ✅ Simpler than ETag (but less accurate)

**Trade-Offs**:
- ✅ Pro: Excellent bandwidth savings
- ✅ Pro: Fast sync times
- ✅ Pro: Standard HTTP protocol
- ⚠️ Con: Requires network for freshness check
- ⚠️ Con: GitHub-specific (for now)

### Decision 5: Subdirectory Support

**Decision**: Support pointing to subdirectories within repositories (monorepo support).

**Rationale**:
- **Flexibility**: Agents can live in larger repositories
- **Organization**: Tools/agents can be part of company monorepo
- **Practical**: Many organizations use monorepos
- **Simple**: Just changes the base URL path

**Alternatives Considered**:

1. **Repository Root Only**
   - ❌ Forces dedicated repositories
   - ❌ Less flexible for organizations
   - ❌ Harder to organize

2. **Multiple Path Support**
   - ⚠️ More complex configuration
   - ⚠️ Multiple sync operations per repo
   - ⚠️ Limited benefit over separate repos

**Trade-Offs**:
- ✅ Pro: Monorepo support
- ✅ Pro: Flexible organization
- ✅ Pro: Simple implementation
- ⚠️ Con: Slightly more complex cache path
- ⚠️ Con: Requires path normalization

### Decision 6: Agent Selection Modes

**Decision**: Provide three deployment modes: all, minimal, auto-configure.

**Rationale**:
- **Default (all)**: Maximum functionality, deploy everything
- **Minimal**: Smallest footprint, 6 core agents only
- **Auto-configure**: Smart default, detect toolchain and recommend agents

**Alternatives Considered**:

1. **All-Only**
   - ❌ No optimization for small projects
   - ❌ No toolchain-specific agents
   - ❌ Less user-friendly

2. **Profile-Based** (e.g., "python-dev", "react-dev")
   - ⚠️ Requires maintaining profiles
   - ⚠️ May not match user's stack
   - ✅ More predictable than auto-configure

**Trade-Offs**:
- ✅ Pro: Flexibility (user choice)
- ✅ Pro: Smart defaults (auto-configure)
- ✅ Pro: Minimal for simplicity
- ⚠️ Con: More modes to document
- ⚠️ Con: Auto-configure may miss custom toolchains

## Trade-Offs

### Simplicity vs. Flexibility

**Simplicity Gains**:
- Single deployment location (`.claude/agents/`)
- Priority-based resolution (clear algorithm)
- Git-based sources (no custom protocol)
- Fewer services (~2,000 LOC eliminated)

**Flexibility Maintained**:
- Unlimited Git repositories
- Per-repository priority control
- Subdirectory support (monorepos)
- Custom-only mode (disable system repo)

**Result**: Simplified architecture without sacrificing essential flexibility.

### Performance vs. Freshness

**Performance Optimizations**:
- ETag-based caching (95% bandwidth reduction)
- Incremental sync (only changed files)
- Fast sync times (100-200ms typical)
- Offline fallback (cached agents)

**Freshness Trade-Offs**:
- Sync on startup only (not continuous)
- Manual sync required for immediate updates
- Cache can be stale (until next sync)
- Force refresh available when needed

**Result**: Excellent performance with acceptable freshness trade-off.

### Breaking Changes vs. Backward Compatibility

**Breaking Changes**:
- 4-tier system removed
- User-level agents deprecated
- Configuration format changed
- CLI commands changed

**Compatibility Preserved**:
- Project-level agents still work
- Automatic migration on first run
- Gradual deprecation (user-level agents)
- Documentation for migration

**Result**: Necessary breaking changes with smooth migration path.

## Performance Characteristics

### Sync Performance

**First Sync** (no cache):
- **Operation**: Download all agents from all sources
- **Typical**: 500-800ms
- **Bandwidth**: ~200KB (48 agents, typical)
- **Network**: 10-50 HTTP requests

**Subsequent Sync** (cache hit):
- **Operation**: ETag check for all agents
- **Typical**: 100-200ms
- **Bandwidth**: ~2-5KB (HTTP headers only)
- **Network**: 10-50 HTTP requests (304 responses)

**Bandwidth Savings**: ~95-98% after first sync

### Deployment Performance

**Deploy All** (50 agents):
- **Operation**: Copy agents from cache to `.claude/agents/`
- **Typical**: 50-100ms
- **IO**: 50 file reads + 50 file writes
- **Blocking**: No network operations

**Deploy Minimal** (6 agents):
- **Operation**: Copy 6 agents from cache
- **Typical**: 10-20ms
- **IO**: 6 file reads + 6 file writes

**Deploy Auto-Configure**:
- **Operation**: Detect toolchain + copy matching agents
- **Typical**: 100-200ms
- **Detect**: 50-100ms (filesystem scan)
- **Deploy**: 50-100ms (file copy)

### Priority Resolution Performance

**Algorithm Complexity**: O(n log n) where n = number of sources
- Sort by priority: O(n log n)
- Iterate agents: O(m) where m = total agents
- Select per agent: O(n) worst case
- **Total**: O(n log n + m*n)

**Typical Performance**:
- 3 sources, 50 agents: <1ms
- 10 sources, 200 agents: ~5ms
- Negligible in practice

### Memory Usage

**Cache Size**:
- **Per Agent**: ~2-5KB (markdown file)
- **50 Agents**: ~100-250KB
- **Storage**: Negligible on modern systems

**Runtime Memory**:
- **Configuration**: <1KB (YAML data)
- **Repository List**: <1KB per repository
- **Agent Metadata**: ~1KB per agent
- **Total**: <1MB for typical usage

## Future Enhancements

### Near-Term (v5.1-v5.2)

**1. Private Repository Support**
- **Need**: Corporate users want private agents
- **Implementation**: GitHub token authentication
- **Complexity**: Medium (OAuth flow, token storage)
- **Priority**: High

**2. GitLab/Bitbucket Support**
- **Need**: Users on other Git platforms
- **Implementation**: Abstract Git provider interface
- **Complexity**: Medium (provider adapters)
- **Priority**: Medium

**3. Branch/Tag Support**
- **Need**: Pin to specific versions
- **Implementation**: Add `branch`/`tag` field to `GitRepository`
- **Complexity**: Low (URL modification)
- **Priority**: Medium

**4. Validation Improvements**
- **Need**: Catch configuration errors earlier
- **Implementation**: Schema validation, agent format checks
- **Complexity**: Low
- **Priority**: Low

### Mid-Term (v5.3-v6.0)

**5. Agent Profiles**
- **Need**: Pre-defined agent sets (e.g., "python-dev", "react-dev")
- **Implementation**: Profile configuration with agent lists
- **Complexity**: Medium
- **Priority**: Low

**6. Delta Sync**
- **Need**: Faster sync for large repositories
- **Implementation**: Rsync-style delta encoding
- **Complexity**: High
- **Priority**: Low (ETag caching already very efficient)

**7. Agent Marketplace**
- **Need**: Discover and share community agents
- **Implementation**: Web service with agent registry
- **Complexity**: Very High (infrastructure, moderation)
- **Priority**: Low

**8. Offline Mode Improvements**
- **Need**: Better offline experience
- **Implementation**: Cache expiration policy, stale indicators
- **Complexity**: Medium
- **Priority**: Low

### Long-Term (v6.1+)

**9. Agent Versioning System**
- **Need**: Pin specific agent versions
- **Implementation**: Semantic versioning with lockfile
- **Complexity**: High
- **Priority**: Low

**10. Distributed Sources**
- **Need**: Non-GitHub sources (S3, CDN, self-hosted)
- **Implementation**: Pluggable source adapters
- **Complexity**: High
- **Priority**: Low

**11. Agent Dependencies**
- **Need**: Agents that depend on other agents
- **Implementation**: Dependency graph resolution
- **Complexity**: Very High
- **Priority**: Very Low

### Rejected Enhancements

**Git Clone Support**
- **Why Rejected**: Too heavy, HTTP API sufficient
- **Alternative**: Use branch/tag support instead

**Real-Time Sync**
- **Why Rejected**: Complexity vs. benefit trade-off
- **Alternative**: Manual sync or startup sync sufficient

**Multi-Platform CLI**
- **Why Rejected**: Python CLI works everywhere
- **Alternative**: Homebrew (macOS), pip (universal)

## Implementation Notes

### Lessons Learned

**From 4-Tier System**:
- ✅ Multi-source discovery is powerful but complex
- ✅ Version comparison is useful but maintenance-heavy
- ✅ Cleanup logic is error-prone and hard to test
- ✅ Tier precedence confuses users

**From Single-Tier Implementation**:
- ✅ Priority numbers are clearer than tiers
- ✅ ETag caching is highly effective (95% savings)
- ✅ Composition over inheritance improves testability
- ✅ Subdirectory support is simple and valuable

### Testing Strategy

**Unit Tests**:
- Data models (GitRepository, AgentSourceConfiguration)
- Priority resolution algorithm
- Cache path generation
- Configuration validation

**Integration Tests**:
- Sync service with mock HTTP responses
- Deployment service with temporary directories
- Priority resolution with multiple sources
- Auto-configure with sample projects

**End-to-End Tests**:
- Full sync → deploy workflow
- Migration from 4-tier system
- CLI commands
- Cache persistence

## Related Documentation

- **[Single-Tier Agent System Guide](../guides/single-tier-agent-system.md)** - User guide
- **[Agent Sources API Reference](../reference/agent-sources-api.md)** - Technical API docs
- **Historical Research**: See `docs/_archive/` for archived migration notes
- **[Agent Synchronization Guide](../guides/agent-synchronization.md)** - Sync mechanism details
