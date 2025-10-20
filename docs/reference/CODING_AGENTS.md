# Coding Agents Catalog

**Version**: 4.10.0
**Last Updated**: 2025-10-20
**Status**: Production

## Overview

Claude MPM features a comprehensive suite of 8 specialized coding agents, each optimized for specific programming languages, frameworks, and development paradigms. This catalog provides complete information about available coding agents, their capabilities, and when to use them.

## 🆕 What's New in v4.10.0

- **NEW**: Java Engineer v1.0.0 - Java 21 LTS with Spring Boot 3.x specialist
- Total coding agents: **8** (Python, TypeScript, Next.js, Go, Java, Rust, PHP, Ruby)

## Recent Updates (v4.9.0)

- **NEW**: Golang Engineer v1.0.0 - Go 1.24+ concurrency specialist
- **NEW**: Rust Engineer v1.0.0 - Rust 2024 edition expert
- **UPGRADED**: Python Engineer to v2.0.0 (Python 3.13, JIT)
- **UPGRADED**: TypeScript Engineer to v2.0.0 (TS 5.6+, branded types)
- **UPGRADED**: Next.js Engineer to v2.0.0 (Next.js 15, App Router)
- **UPGRADED**: PHP Engineer to v2.0.0 (PHP 8.4-8.5, Laravel 12)
- **UPGRADED**: Ruby Engineer to v2.0.0 (Ruby 3.4 YJIT, Rails 8)

## Quick Reference

| Agent | Version | Language/Framework | Status | Use When |
|-------|---------|-------------------|--------|----------|
| [Python Engineer](#python-engineer) | v2.0.0 | Python 3.13+ | ✅ Production | Service-oriented Python, async/await, FastAPI |
| [TypeScript Engineer](#typescript-engineer) | v2.0.0 | TypeScript 5.6+ | ✅ Production | Type-safe applications, branded types, modern tooling |
| [Next.js Engineer](#nextjs-engineer) | v2.0.0 | Next.js 15 | ✅ Production | Modern React apps, App Router, Server Components |
| [Go Engineer](#go-engineer) | v1.0.0 | Go 1.24+ | ✅ Production | Concurrent systems, microservices, performance |
| [Java Engineer](#java-engineer) | v1.0.0 | Java 21 LTS | ✅ Production | Spring Boot 3.x, virtual threads, enterprise patterns |
| [Rust Engineer](#rust-engineer) | v1.0.0 | Rust 2024 | ✅ Production | Systems programming, WebAssembly, performance |
| [PHP Engineer](#php-engineer) | v2.0.0 | PHP 8.4-8.5 | ✅ Production | Modern PHP, Laravel 12, DDD/CQRS patterns |
| [Ruby Engineer](#ruby-engineer) | v2.0.0 | Ruby 3.4 | ✅ Production | Rails 8, YJIT performance, service objects |

## Available Agents

### Python Engineer v2.0.0

**Agent ID**: `python-engineer`
**Language**: Python 3.13+
**Model**: Sonnet
**Status**: ✅ Production

**Specialization**:
Modern Python development specialist focused on service-oriented architecture, async/await patterns, dependency injection, and type safety with comprehensive testing.

**Key Capabilities**:
- **Modern Python**: Python 3.13+ with JIT compiler optimization
- **Architecture**: ABC interfaces, dependency injection containers, SOLID principles
- **Async/Await**: AsyncIO patterns for I/O-bound operations
- **Type Safety**: mypy, type hints, Pydantic for data validation
- **Testing**: pytest, unittest, comprehensive test coverage
- **Performance**: Profiling, optimization, caching strategies
- **Frameworks**: FastAPI, Django, Flask with best practices

**Best For**:
- Service-oriented Python applications
- API development with FastAPI
- Async web servers and microservices
- Data processing pipelines
- CLI tools and automation scripts

**Quality Standards**:
- PEP 8 compliance with Black formatting
- Type hints on all public interfaces
- 85%+ test coverage
- Async patterns for I/O operations
- Comprehensive error handling

**Example Use Cases**:
```python
# Service-oriented architecture with DI
from abc import ABC, abstractmethod

class IUserService(ABC):
    @abstractmethod
    async def create_user(self, data: dict) -> User:
        pass

class UserService(IUserService):
    def __init__(self, repo: IUserRepository):
        self.repo = repo

    async def create_user(self, data: dict) -> User:
        # Implementation with async patterns
        return await self.repo.save(User(**data))
```

**When to Delegate**:
- User mentions: "Python", "FastAPI", "async/await", "service-oriented"
- File paths: `*.py`, `/api/`, `/services/`
- Requirements: Type-safe Python APIs, async processing, DI patterns

---

### TypeScript Engineer v2.0.0

**Agent ID**: `typescript-engineer`
**Language**: TypeScript 5.6+
**Model**: Sonnet
**Status**: ✅ Production

**Specialization**:
TypeScript specialist focused on advanced type safety with branded types, discriminated unions, conditional types, and modern build tooling for high-performance applications.

**Key Capabilities**:
- **Advanced Types**: Branded types, discriminated unions, conditional types
- **Type Safety**: Strict mode, no implicit any, comprehensive type coverage
- **Modern Build**: Vite, Bun, esbuild, SWC for fast builds
- **Testing**: Vitest, Playwright for comprehensive testing
- **Frameworks**: React, Vue, Next.js with TypeScript best practices
- **Performance**: Web Workers, optimization patterns
- **Functional**: Functional programming patterns with TypeScript

**Best For**:
- Type-safe API clients with branded types
- Complex state management with discriminated unions
- High-performance web applications
- TypeScript library development
- Modern React/Vue applications with strict typing

**Quality Standards**:
- Strict TypeScript mode enabled
- Branded types for domain identifiers
- Result types for error handling
- Comprehensive type coverage
- Modern build tooling (Vite/Bun)

**Example Use Cases**:
```typescript
// Branded types for type safety
type UserId = string & { readonly brand: unique symbol };
type EmailAddress = string & { readonly brand: unique symbol };

// Discriminated unions for responses
type ApiResponse<T> =
  | { status: 'success'; data: T }
  | { status: 'error'; error: string };

// Type-safe fetch wrapper
async function fetchUser(id: UserId): Promise<ApiResponse<User>> {
  // Implementation with result types
}
```

**When to Delegate**:
- User mentions: "TypeScript", "branded types", "type safety", "strict mode"
- File paths: `*.ts`, `*.tsx`, `/types/`, `/lib/`
- Requirements: Advanced TypeScript patterns, type-safe APIs

---

### Next.js Engineer v2.0.0

**Agent ID**: `nextjs-engineer`
**Language**: Next.js 15 + TypeScript
**Model**: Sonnet
**Status**: ✅ Production

**Specialization**:
Next.js 15 expert specializing in App Router, Server Components, Server Actions, and modern React patterns for production-grade applications.

**Key Capabilities**:
- **Next.js 15**: App Router, Server Components, Server Actions
- **Architecture**: Clean separation of server/client components
- **Data Fetching**: Server-side rendering, static generation, ISR
- **Performance**: Image optimization, font optimization, route prefetching
- **TypeScript**: Full TypeScript integration with strict mode
- **Deployment**: Vercel, self-hosted, Docker deployments
- **Testing**: Jest, Playwright for E2E testing

**Best For**:
- Modern e-commerce applications
- Content-heavy websites with SSR/SSG
- Dashboard applications with real-time data
- Marketing sites with optimal SEO
- Full-stack TypeScript applications

**Quality Standards**:
- App Router architecture (not Pages Router)
- Server Components by default, Client Components when needed
- Server Actions for mutations
- TypeScript throughout
- Optimized images and fonts

**Example Use Cases**:
```typescript
// Server Component (default)
async function ProductList() {
  const products = await fetchProducts(); // Server-side fetch
  return (
    <div>
      {products.map(p => <ProductCard key={p.id} product={p} />)}
    </div>
  );
}

// Client Component (when needed)
'use client';
function ShoppingCart() {
  const [items, setItems] = useState([]);
  // Client-side interactivity
}

// Server Action (mutations)
'use server';
async function addToCart(productId: string) {
  // Server-side mutation
}
```

**When to Delegate**:
- User mentions: "Next.js", "App Router", "Server Components", "React SSR"
- File paths: `/app/`, `/components/`, `next.config.*`
- Requirements: Modern React apps with Next.js 15

---

### Go Engineer v1.0.0 🆕

**Agent ID**: `go-engineer`
**Language**: Go 1.24+
**Model**: Sonnet
**Status**: ✅ Production

**Specialization**:
Go 1.24+ specialist focused on concurrency patterns, microservices architecture, high-performance systems, and idiomatic Go code.

**Key Capabilities**:
- **Modern Go**: Go 1.24+ with latest language features
- **Concurrency**: Goroutines, channels, sync primitives, context management
- **Architecture**: Clean architecture, hexagonal patterns, DDD
- **Performance**: Profiling, benchmarking, optimization
- **Testing**: Table-driven tests, benchmarks, race detection
- **APIs**: HTTP servers, gRPC, WebSocket
- **Deployment**: Docker, Kubernetes, cloud-native patterns

**Best For**:
- Microservices and distributed systems
- High-performance backend services
- Concurrent data processing
- CLI tools and system utilities
- Real-time systems and WebSocket servers

**Quality Standards**:
- Idiomatic Go code following effective Go principles
- Comprehensive error handling with context
- Table-driven tests with race detection
- Context management for cancellation
- Performance benchmarks for critical paths

**Example Use Cases**:
```go
// Concurrent processing with channels
func ProcessItems(items []Item) []Result {
    results := make(chan Result, len(items))
    var wg sync.WaitGroup

    for _, item := range items {
        wg.Add(1)
        go func(i Item) {
            defer wg.Done()
            results <- processItem(i)
        }(item)
    }

    go func() {
        wg.Wait()
        close(results)
    }()

    return collectResults(results)
}

// Context-aware HTTP handler
func (s *Server) HandleRequest(ctx context.Context, req Request) error {
    select {
    case <-ctx.Done():
        return ctx.Err()
    case result := <-s.process(req):
        return s.respond(result)
    }
}
```

**When to Delegate**:
- User mentions: "Go", "Golang", "concurrency", "goroutines", "microservices"
- File paths: `*.go`, `/cmd/`, `/internal/`, `/pkg/`
- Requirements: Concurrent systems, high performance, microservices

---

### Java Engineer v1.0.0 🆕

**Agent ID**: `java-engineer`
**Language**: Java 21 LTS
**Model**: Sonnet
**Status**: ✅ Production

**Specialization**:
Java 21 LTS specialist focused on Spring Boot 3.x applications, virtual threads for high concurrency, modern performance optimizations, and enterprise architecture patterns with comprehensive JUnit 5 testing.

**Key Capabilities**:
- **Java 21 LTS**: Virtual threads (JEP 444), pattern matching, sealed classes, record patterns
- **Spring Boot 3.x**: Auto-configuration, dependency injection, reactive support with Project Reactor
- **Architecture**: Hexagonal architecture, clean architecture, domain-driven design (DDD), CQRS
- **Concurrency**: Virtual threads for lightweight concurrency, CompletableFuture patterns, reactive streams
- **Testing**: JUnit 5, Mockito, AssertJ, TestContainers for integration testing
- **Build Tools**: Maven 4.x, Gradle 8.x with dependency management
- **Performance**: JVM tuning (G1GC, ZGC), Java Flight Recorder (JFR), JMH benchmarking

**Best For**:
- Spring Boot 3.x microservices and applications
- Enterprise application architecture (hexagonal, clean, DDD)
- High-performance concurrent systems with virtual threads
- Production-ready code with 90%+ test coverage
- Maven/Gradle build optimization
- JVM performance tuning and profiling

**Quality Standards**:
- Java 21 LTS with modern features (virtual threads, pattern matching)
- Constructor injection over field injection in Spring
- Try-with-resources for all AutoCloseable resources
- 90%+ test coverage with JUnit 5 and Mockito
- Static analysis with SonarQube, SpotBugs, Checkstyle
- Explicit @Transactional boundaries for consistency

**Example Use Cases**:
```java
// Virtual threads for high concurrency
public class VirtualThreadPatterns {
    public static <T> List<T> processConcurrentTasks(
            List<Callable<T>> tasks,
            Duration timeout
    ) throws InterruptedException, ExecutionException, TimeoutException {
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            List<Future<T>> futures = executor.invokeAll(
                tasks,
                timeout.toMillis(),
                TimeUnit.MILLISECONDS
            );
            return futures.stream()
                .filter(f -> !f.isCancelled())
                .map(f -> {
                    try { return f.get(); }
                    catch (Exception e) { throw new RuntimeException(e); }
                })
                .collect(Collectors.toList());
        }
    }
}

// Spring Boot with constructor injection
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository repository;

    @Transactional
    public User createUser(CreateUserRequest request) {
        // Implementation with explicit transaction boundary
        return repository.save(new User(request));
    }
}

// Stream API for functional processing
public static int lengthOfLongestSubstring(String s) {
    Map<Character, Integer> charIndex = new HashMap<>();
    int maxLength = 0, left = 0;

    for (int right = 0; right < s.length(); right++) {
        char c = s.charAt(right);
        if (charIndex.containsKey(c) && charIndex.get(c) >= left) {
            left = charIndex.get(c) + 1;
        }
        charIndex.put(c, right);
        maxLength = Math.max(maxLength, right - left + 1);
    }
    return maxLength;
}
```

**When to Delegate**:
- User mentions: "Java", "Spring Boot", "JVM", "Maven", "Gradle", "JUnit", "enterprise", "microservices"
- File paths: `*.java`, `/src/main/java/`, `/src/test/java/`, `pom.xml`, `build.gradle`
- Requirements: Enterprise Java applications, Spring Boot projects, high-concurrency systems, JVM performance tuning

---

### Rust Engineer v1.0.0 🆕

**Agent ID**: `rust-engineer`
**Language**: Rust 2024 edition
**Model**: Sonnet
**Status**: ✅ Production

**Specialization**:
Rust 2024 edition expert specializing in systems programming, memory safety, zero-cost abstractions, WebAssembly, and high-performance applications.

**Key Capabilities**:
- **Modern Rust**: Rust 2024 edition with latest features
- **Memory Safety**: Ownership, borrowing, lifetimes
- **Performance**: Zero-cost abstractions, inline assembly
- **Concurrency**: Fearless concurrency with Send/Sync traits
- **WebAssembly**: WASM compilation and optimization
- **Testing**: Cargo test, property-based testing, fuzzing
- **Ecosystem**: Tokio, Actix, Rocket for web services

**Best For**:
- Systems programming and OS-level tools
- High-performance computing applications
- WebAssembly modules for web browsers
- Embedded systems and IoT
- CLI tools requiring maximum performance
- Security-critical applications

**Quality Standards**:
- Idiomatic Rust following Rust book principles
- Comprehensive error handling with Result types
- Documentation comments on public APIs
- Clippy-clean code with no warnings
- Property-based tests for critical logic

**Example Use Cases**:
```rust
// Zero-cost abstraction with generics
fn process_data<T: Processor>(processor: &T, data: Vec<u8>) -> Result<Output, Error> {
    processor.process(data)
        .map_err(|e| Error::ProcessingFailed(e))
}

// Fearless concurrency with async/await
async fn fetch_multiple(urls: Vec<String>) -> Vec<Result<Response, Error>> {
    let futures = urls.into_iter().map(|url| fetch(url));
    futures::future::join_all(futures).await
}

// WebAssembly-compatible code
#[wasm_bindgen]
pub fn compute_fibonacci(n: u32) -> u64 {
    // WASM-optimized implementation
}
```

**When to Delegate**:
- User mentions: "Rust", "WebAssembly", "systems programming", "performance"
- File paths: `*.rs`, `Cargo.toml`, `/src/`
- Requirements: Memory safety, high performance, WASM

---

### PHP Engineer v2.0.0

**Agent ID**: `php-engineer`
**Language**: PHP 8.4-8.5
**Model**: Sonnet
**Status**: ✅ Production

**Specialization**:
Modern PHP development specialist focused on PHP 8.4+ features, Laravel 12, DDD/CQRS patterns, type safety, and comprehensive deployment expertise.

**Key Capabilities**:
- **Modern PHP**: PHP 8.4-8.5 with latest features (property hooks, asymmetric visibility)
- **Frameworks**: Laravel 12+, Symfony 7+
- **Architecture**: DDD, CQRS, hexagonal architecture
- **Type Safety**: Strict types, PHPStan/Psalm static analysis
- **Testing**: PHPUnit, Pest, feature tests
- **Deployment**: DigitalOcean App Platform, Docker, Kubernetes
- **Performance**: OPcache optimization, query optimization

**Best For**:
- Enterprise Laravel applications
- RESTful APIs with modern PHP
- E-commerce platforms
- Content management systems
- Microservices with PHP
- Legacy PHP modernization

**Quality Standards**:
- PHP 8.4+ with strict types enabled
- PSR-12 coding standard
- Static analysis with PHPStan level 8+
- Comprehensive test coverage
- Laravel best practices

**Example Use Cases**:
```php
<?php declare(strict_types=1);

// Modern PHP 8.4+ with property hooks
class User {
    public function __construct(
        private string $email {
            set => strtolower($value);
        },
        private ?string $name = null,
    ) {}
}

// Laravel 12 with CQRS pattern
class CreateUserCommand {
    public function __construct(
        public readonly string $email,
        public readonly string $name,
    ) {}
}

class CreateUserHandler {
    public function handle(CreateUserCommand $command): User {
        // CQRS command handling
    }
}
```

**When to Delegate**:
- User mentions: "PHP", "Laravel", "Symfony", "DDD", "CQRS"
- File paths: `*.php`, `/app/`, `/src/`, `composer.json`
- Requirements: Modern PHP applications, Laravel projects

---

### Ruby Engineer v2.0.0

**Agent ID**: `ruby-engineer`
**Language**: Ruby 3.4
**Model**: Sonnet
**Status**: ✅ Production

**Specialization**:
Ruby 3.4 and Rails 8 specialist focused on YJIT performance, service objects, clean architecture, and comprehensive RSpec testing.

**Key Capabilities**:
- **Modern Ruby**: Ruby 3.4 with YJIT performance
- **Rails 8**: Latest Rails features and best practices
- **Architecture**: Service objects, PORO patterns, DI
- **Testing**: RSpec with comprehensive coverage
- **Performance**: YJIT optimization, query optimization
- **Background Jobs**: Sidekiq, Good Job patterns
- **Deployment**: Heroku, Fly.io, Docker

**Best For**:
- Rails 8 web applications
- RESTful APIs with Ruby
- Background job processing
- Service-oriented Ruby applications
- Rails upgrades and modernization
- Ruby gems development

**Quality Standards**:
- Ruby 3.4+ with YJIT enabled
- RuboCop compliance
- Service objects for business logic
- Comprehensive RSpec tests
- Rails 8 conventions

**Example Use Cases**:
```ruby
# Service object with dependency injection
class UserRegistrationService
  def initialize(user_repo: UserRepository.new, mailer: UserMailer)
    @user_repo = user_repo
    @mailer = mailer
  end

  def call(params)
    ActiveRecord::Base.transaction do
      user = @user_repo.create!(params)
      @mailer.welcome_email(user).deliver_later
      Result.success(user)
    rescue => e
      Result.failure(e.message)
    end
  end
end

# RSpec with comprehensive testing
RSpec.describe UserRegistrationService do
  describe '#call' do
    it 'creates user and sends welcome email' do
      # Comprehensive test with mocks
    end
  end
end
```

**When to Delegate**:
- User mentions: "Ruby", "Rails", "RSpec", "service objects"
- File paths: `*.rb`, `/app/`, `/spec/`, `Gemfile`
- Requirements: Rails applications, Ruby services

---

## Agent Performance Benchmarks

Claude MPM coding agents are continuously evaluated using a lightweight SWE benchmark suite (96 tests covering algorithms, real-world scenarios, framework expertise, and edge cases).

### Current Scores (Lightweight Benchmark v1.0)

| Rank | Agent | Score | Grade | Easy | Medium | Hard | Status |
|------|-------|-------|-------|------|--------|------|--------|
| 1 | Ruby Engineer | 68.1% | C+ | 3/4 | 4/5 | 2/3 | ✅ Functional |
| 2 | Rust Engineer | 67.3% | C+ | 3/4 | 4/5 | 2/3 | ✅ Functional |
| 3 | TypeScript Engineer | 66.8% | C+ | 4/4 | 2/5 | 2/3 | ✅ Functional |
| 4 | Java Engineer | 65.0% | C+ | TBD | TBD | TBD | ✅ Functional |
| 5 | Next.js Engineer | 65.8% | C+ | 4/4 | 4/5 | 1/3 | ✅ Functional |
| 6 | Golang Engineer | 62.6% | C | 3/4 | 3/5 | 1/3 | ✅ Functional |
| 7 | Python Engineer | 62.3% | C | 4/4 | 2/5 | 1/3 | ✅ Functional |
| 8 | PHP Engineer | 60.8% | C | 4/4 | 3/5 | 0/3 | ⚠️ Needs improvement |

**Methodology**: Multi-dimensional evaluation (Correctness 40%, Idiomaticity 25%, Performance 20%, Best Practices 15%) with difficulty weighting (Easy 1.0x, Medium 1.2x, Hard 1.5x).

**Average Score**: 64.7% across all agents
**Last Updated**: 2025-10-20

### Interpreting Scores

- **70%+ (B-)**: Production-ready with minor improvements needed
- **65-69% (C+)**: Functional with targeted improvements recommended
- **60-64% (C)**: Functional but requires enhancement
- **<60%**: Significant improvements needed

### Benchmark Details

For complete benchmark methodology, test suites, and detailed results, see:
- [Benchmark Documentation](../benchmarks/README.md) - Complete system documentation
- [Quick Start Guide](../benchmarks/QUICKSTART.md) - 30-second start guide
- [Benchmark Quick Reference](BENCHMARK_QUICKREF.md) - Quick reference card
- Latest Results: `docs/benchmarks/results/baseline-2025-10-18/dashboard.html`

---

## Agent Selection Guide

### By Language

| Need | Use Agent |
|------|-----------|
| Python | Python Engineer v2.0.0 |
| TypeScript | TypeScript Engineer v2.0.0 |
| JavaScript + React | Next.js Engineer v2.0.0 or TypeScript Engineer v2.0.0 |
| Go/Golang | Go Engineer v1.0.0 🆕 |
| Java | Java Engineer v1.0.0 🆕 |
| Rust | Rust Engineer v1.0.0 🆕 |
| PHP | PHP Engineer v2.0.0 |
| Ruby | Ruby Engineer v2.0.0 |

### By Use Case

| Use Case | Recommended Agent |
|----------|-------------------|
| Microservices | Go Engineer, Java Engineer, Rust Engineer, Python Engineer |
| Web Applications | Next.js Engineer, TypeScript Engineer, Ruby Engineer |
| APIs | Python Engineer (FastAPI), Java Engineer (Spring Boot), PHP Engineer (Laravel), Ruby Engineer (Rails) |
| Performance-Critical | Rust Engineer, Go Engineer, Java Engineer |
| Systems Programming | Rust Engineer, Go Engineer |
| WebAssembly | Rust Engineer, Go Engineer |
| E-commerce | Next.js Engineer, PHP Engineer, Ruby Engineer |
| CLI Tools | Go Engineer, Rust Engineer, Python Engineer |
| Enterprise Applications | Java Engineer, PHP Engineer, Go Engineer |

### By Architecture Pattern

| Pattern | Best Agent |
|---------|------------|
| Service-Oriented | Python Engineer, Java Engineer, PHP Engineer |
| DDD/CQRS | Java Engineer, PHP Engineer, Go Engineer |
| Clean Architecture | Go Engineer, Java Engineer, Rust Engineer, Python Engineer |
| Hexagonal Architecture | Java Engineer, Go Engineer, PHP Engineer |
| Server Components | Next.js Engineer |
| Concurrency | Go Engineer, Rust Engineer, Java Engineer |

## Quality Standards (All Agents)

### Common Requirements

All coding agents adhere to these quality standards:

1. **Search-First Methodology**: Use semantic search before implementing
2. **Code Conciseness**: Minimize net new lines of code
3. **Test Coverage**: 85%+ coverage target
4. **Documentation**: Comprehensive inline and external docs
5. **Error Handling**: Comprehensive error handling patterns
6. **Performance**: Profiling and optimization where appropriate

### Statistical Confidence

All agents target **95% confidence** in their implementations through:

- 25 comprehensive tests per agent (175 total)
- Multi-dimensional evaluation (correctness, idiomaticity, performance)
- Paradigm-aware testing (respecting language philosophies)
- Difficulty-based scoring (easy/medium/hard)

## Version History

### v2.0.0 (Current)
- **Upgraded**: Python Engineer (Python 3.13, JIT)
- **Upgraded**: TypeScript Engineer (TS 5.6+, branded types)
- **Upgraded**: Next.js Engineer (Next.js 15, App Router)
- **Upgraded**: PHP Engineer (PHP 8.4-8.5, Laravel 12)
- **Upgraded**: Ruby Engineer (Ruby 3.4 YJIT, Rails 8)

### v1.0.0 (New)
- **Added**: Go Engineer (Go 1.24+)
- **Added**: Rust Engineer (Rust 2024 edition)

## Testing Infrastructure

Each coding agent is validated through:

- **12 comprehensive tests** per agent covering easy/medium/hard scenarios
- **Multi-dimensional scoring**: correctness, idiomaticity, performance, best practices
- **Paradigm-aware evaluation**: respecting language-specific philosophies
- **Statistical confidence**: 95% confidence target
- **Total test suite**: 96 tests across 8 coding agents

### Test Distribution by Agent
- Python Engineer: 12 tests (4 easy, 5 medium, 3 hard)
- TypeScript Engineer: 12 tests (4 easy, 5 medium, 3 hard)
- Next.js Engineer: 12 tests (4 easy, 5 medium, 3 hard)
- Go Engineer: 12 tests (4 easy, 5 medium, 3 hard)
- Java Engineer: 12 tests (4 easy, 5 medium, 3 hard) 🆕
- Rust Engineer: 12 tests (4 easy, 5 medium, 3 hard)
- PHP Engineer: 12 tests (4 easy, 5 medium, 3 hard)
- Ruby Engineer: 12 tests (4 easy, 5 medium, 3 hard)

See [Agent Testing Guide](../developer/AGENT_TESTING.md) for detailed testing procedures.

## Deployment Information

All coding agents are deployed to:
- **Location**: `.claude/agents/` (project-level)
- **Status**: Production-ready
- **Backup**: Maintained in version control

For deployment procedures, see [Agent Deployment Log](AGENT_DEPLOYMENT_LOG.md).

## Getting Help

### Using Coding Agents

To use a coding agent with Claude MPM:

```bash
# Interactive mode - agents are automatically selected
claude-mpm run

# Specify agent in prompt
"I need help with Python service-oriented architecture"
# PM will delegate to python-engineer

# Direct agent invocation (advanced)
"@python-engineer: Implement FastAPI endpoint"
```

### Troubleshooting

- **Agent not found**: Ensure agents are deployed with `claude-mpm agents deploy`
- **Version mismatch**: Check `claude-mpm agents list` for current versions
- **Performance issues**: Agents use semantic search - ensure project is indexed

### Further Reading

- [Agent Development Guide](../developer/07-agent-system/creation-guide.md)
- [Agent Testing Guide](../developer/AGENT_TESTING.md)
- [Agent Capabilities Reference](AGENT_CAPABILITIES.md)
- [Architecture Documentation](../developer/ARCHITECTURE.md)

---

**Last Updated**: 2025-10-17
**Document Version**: 1.0.0
**Maintained By**: Claude MPM Team
