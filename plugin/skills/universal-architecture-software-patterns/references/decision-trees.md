# Decision Trees

Detailed flowcharts for pattern selection based on observed problems.

## Master Decision Tree

```
START: What problem are you experiencing?
│
├─► "Code is hard to test"
│   └─► Go to: Testability Decision Tree
│
├─► "Business logic is scattered"
│   └─► Go to: Organization Decision Tree
│
├─► "External systems cause problems"
│   └─► Go to: External Integration Decision Tree
│
├─► "Services are too coupled"
│   └─► Go to: Coupling Decision Tree
│
├─► "Data operations are inconsistent"
│   └─► Go to: Data Management Decision Tree
│
└─► "No specific problem"
    └─► STOP. Don't add patterns without problems.
```

---

## Testability Decision Tree

```
Code is hard to test
│
├─► Are classes creating their own dependencies?
│   │
│   ├─► Yes
│   │   └─► Apply: DEPENDENCY INJECTION
│   │       - Pass dependencies via constructor
│   │       - Define interfaces for mockable boundaries
│   │       
│   └─► No
│       │
│       ├─► Are you testing through UI/API when unit test would work?
│       │   └─► Not a pattern problem - use correct test level
│       │
│       ├─► Are database calls mixed with business logic?
│       │   └─► Apply: REPOSITORY PATTERN
│       │       - Abstract data access
│       │       - Mock repository in tests
│       │
│       └─► Are external APIs called directly?
│           └─► Apply: ANTI-CORRUPTION LAYER
│               - Wrap external calls
│               - Mock wrapper in tests
```

### Testability Pattern Selection Summary

| Symptom | Pattern | Why |
|---------|---------|-----|
| `new Dependency()` in class | DI | Can't substitute test doubles |
| SQL in business logic | Repository | Can't test without database |
| Direct external API calls | ACL | Can't test without external service |
| Global state dependencies | DI + refactor | Hidden dependencies untestable |

---

## Organization Decision Tree

```
Business logic is scattered
│
├─► Is the same validation/rule in multiple places?
│   │
│   ├─► Yes, and rules are complex
│   │   └─► Apply: SPECIFICATION PATTERN
│   │       - Encapsulate rules as objects
│   │       - Compose and reuse
│   │
│   └─► Yes, but rules are simple
│       └─► Extract to shared function first
│           - Only add Specification if rules grow complex
│
├─► Is it unclear which team/component owns what logic?
│   │
│   └─► Apply: SERVICE-ORIENTED ARCHITECTURE
│       - Define service boundaries
│       - Each service owns its domain
│       - Clear interfaces between services
│
├─► Does business code know about database structure?
│   │
│   └─► Apply: REPOSITORY PATTERN
│       - Services speak domain language
│       - Repository handles persistence
│
└─► Is feature code spread across layers (controller → service → repo)?
    │
    └─► This is often correct! Layers serve different purposes.
        - Question if layers are needed
        - Don't merge without cause
```

### Organization Pattern Selection Summary

| Symptom | Pattern | Why |
|---------|---------|-----|
| Duplicated complex rules | Specification | Single source of truth, testable |
| "Who owns this code?" | SOA | Clear boundaries and ownership |
| SQL leaking to business layer | Repository | Abstraction isolates concerns |
| Identical code in controller and service | Review architecture | May indicate wrong boundaries |

---

## External Integration Decision Tree

```
External systems cause problems
│
├─► Do API changes from vendor break your code?
│   │
│   └─► Apply: ANTI-CORRUPTION LAYER
│       - Define your interface
│       - Translate at boundary
│       - Internal code uses your types
│
├─► Does external service unreliability affect your users?
│   │
│   ├─► Failures cascade (one service down = everything down)
│   │   └─► Apply: CIRCUIT BREAKER
│   │       - Fail fast when service unhealthy
│   │       - Degrade gracefully
│   │
│   ├─► Transient failures (occasional timeouts, retries help)
│   │   └─► Apply: RETRY WITH BACKOFF
│   │       - Exponential backoff
│   │       - Maximum retry count
│   │       - Combine with circuit breaker for persistent failures
│   │
│   └─► Slow responses hurt performance
│       └─► Apply: TIMEOUT + CIRCUIT BREAKER
│           - Timeout individual calls
│           - Circuit breaker for persistent slowness
│
└─► Is external terminology leaking into your domain?
    │
    └─► Apply: ANTI-CORRUPTION LAYER
        - Translate at boundary
        - Your code uses your language
```

### External Integration Pattern Combinations

| Scenario | Patterns | Notes |
|----------|----------|-------|
| Unreliable third-party API | ACL + Circuit Breaker + Retry | Full protection |
| Stable but foreign terminology | ACL only | Translation without resilience |
| Internal microservice | Circuit Breaker if unreliable | ACL usually overkill |
| Critical payment provider | ACL + Circuit Breaker + Fallback | Graceful degradation |

---

## Coupling Decision Tree

```
Services are too coupled
│
├─► Do services call each other in cycles?
│   │
│   (A → B → C → A or similar)
│   │
│   └─► Apply: DOMAIN EVENTS
│       - Break cycle with publish/subscribe
│       - Services react to events, don't call directly
│
├─► Must all services be available for any operation?
│   │
│   └─► Evaluate each dependency:
│       ├─► Required for correctness? → Keep synchronous
│       └─► Nice-to-have/eventual? → Apply: DOMAIN EVENTS
│
├─► Does adding new feature require changing multiple services?
│   │
│   ├─► Services share data inappropriately?
│   │   └─► Apply: SOA with clear data ownership
│   │
│   └─► Services have wrong boundaries?
│       └─► Refactor boundaries
│           - May need to merge services
│           - May need to split differently
│
└─► Do services share a database?
    │
    └─► Often root cause of coupling
        - Each service should own its data
        - If sharing required, explicit shared service
```

### Coupling Indicators and Solutions

| Indicator | Likely Problem | Solution |
|-----------|---------------|----------|
| Circular calls between services | Wrong boundaries or missing events | Domain Events or merge |
| Deploy A requires deploy B | Shared assumptions or contracts | Version interfaces, decouple |
| Shared database tables | Data ownership unclear | Service per bounded context |
| "Cannot test without X running" | Temporal coupling | Async events or better mocking |

---

## Data Management Decision Tree

```
Data operations are inconsistent
│
├─► Multiple entities must update atomically?
│   │
│   (Transfer between accounts, order with items, etc.)
│   │
│   └─► Apply: UNIT OF WORK
│       - Track changes
│       - Commit as single transaction
│
├─► Same query written in multiple places?
│   │
│   └─► Apply: REPOSITORY PATTERN
│       - Encapsulate queries
│       - Single source for data access
│
├─► Business logic mixed with persistence logic?
│   │
│   └─► Apply: REPOSITORY + SERVICE
│       - Repository handles data
│       - Service handles business rules
│
└─► Complex filtering/selection logic?
    │
    └─► Apply: SPECIFICATION PATTERN
        - Encapsulate criteria
        - Compose queries
        - Repository accepts specifications
```

---

## Quick Reference: Problem → Pattern

| Problem | First Pattern | Additional Patterns |
|---------|--------------|---------------------|
| Hard to test | DI | Repository, ACL |
| Scattered logic | SOA | Repository, Specification |
| API changes break code | ACL | Circuit Breaker |
| Cascading failures | Circuit Breaker | Retry, Timeout |
| Circular dependencies | Domain Events | SOA refactor |
| Data inconsistency | Unit of Work | Repository |
| Complex business rules | Specification | Domain Events |

---

## Decision Checklist

Before applying any pattern, answer:

1. **What specific problem am I solving?**
   - If you can't name it, don't apply pattern

2. **Will this pattern solve that problem?**
   - Understand the pattern's purpose
   - Match to your problem

3. **What is the cost of this pattern?**
   - Complexity added
   - Learning curve
   - Maintenance burden

4. **Is there a simpler solution?**
   - Sometimes refactoring beats patterns
   - Sometimes the "problem" is acceptable

5. **Can I validate the pattern helped?**
   - Before/after comparison
   - Measurable improvement
