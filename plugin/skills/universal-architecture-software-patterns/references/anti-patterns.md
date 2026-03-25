# Anti-Patterns

Common misapplications of architectural patterns and how to recognize them.

## Dependency Injection Anti-Patterns

### Service Locator Masquerading as DI

**The problem:**
Using a global registry to look up dependencies at runtime instead of injecting them.

```
// ANTI-PATTERN: Service Locator
class UserService {
  createUser(data) {
    notifier = ServiceLocator.get("Notifier")  // Hidden dependency
    repo = ServiceLocator.get("UserRepository")
    // ...
  }
}

// CORRECT: Dependency Injection
class UserService {
  constructor(notifier, repo) {  // Explicit dependencies
    this.notifier = notifier
    this.repo = repo
  }
}
```

**Why it's harmful:**
- Dependencies hidden - can't tell what UserService needs without reading implementation
- Testing requires global state manipulation
- Order-dependent initialization
- Harder to reason about

**Signs you're doing this:**
- Calling `Container.resolve()` or `ServiceLocator.get()` inside methods
- Tests need to configure global registries
- "Which services does X depend on?" requires code inspection

---

### Constructor Over-Injection

**The problem:**
A class requires so many dependencies it signals design issues.

```
// ANTI-PATTERN: Too many dependencies
class OrderService {
  constructor(
    userRepo, orderRepo, productRepo, inventoryRepo,
    paymentService, shippingService, notificationService,
    taxCalculator, discountEngine, fraudDetector,
    logger, metrics, cache
  ) { ... }
}
```

**Why it's harmful:**
- Class doing too much (violates Single Responsibility)
- Difficult to understand
- Testing requires many mocks
- Probably has feature envy

**How to fix:**
- Extract cohesive groups into new services
- Consider if some are cross-cutting concerns (logging, metrics) that don't need injection
- Question if class should exist at all

```
// BETTER: Smaller, focused services
class OrderProcessor {
  constructor(orderRepo, inventoryService, paymentGateway) { ... }
}

class OrderNotifier {
  constructor(notificationService, templateEngine) { ... }
}
```

---

### Injecting the Container

**The problem:**
Passing the DI container itself as a dependency.

```
// ANTI-PATTERN: Container as dependency
class UserService {
  constructor(container) {
    this.container = container
  }
  
  createUser(data) {
    notifier = this.container.resolve("Notifier")  // Still Service Locator!
  }
}
```

**Why it's harmful:**
- Hides actual dependencies
- Makes class depend on container implementation
- Same problems as Service Locator

**Correct approach:**
Resolve at composition root, inject concrete dependencies.

---

## Service-Oriented Architecture Anti-Patterns

### Anemic Services

**The problem:**
Services that are just data containers with no behavior.

```
// ANTI-PATTERN: Anemic service
class UserService {
  getUser(id) { return repo.findById(id) }
  saveUser(user) { return repo.save(user) }
  deleteUser(id) { return repo.delete(id) }
}

// Business logic elsewhere
class UserController {
  register(data) {
    if (!isValidEmail(data.email)) throw Error()  // Logic leaked out
    if (data.password.length < 8) throw Error()
    user = new User(data)
    userService.saveUser(user)
    sendWelcomeEmail(user)  // More leaked logic
  }
}
```

**Why it's harmful:**
- Business logic scattered
- Service provides no value over repository
- Controller/caller becomes bloated

**Correct approach:**
Services encapsulate business logic.

```
// BETTER: Rich service
class UserService {
  register(data) {
    this.validateRegistration(data)  // Validation here
    user = User.create(data)
    this.repo.save(user)
    this.eventBus.publish(new UserRegistered(user))  // Side effects here
    return user
  }
}
```

---

### Chatty Services

**The problem:**
Services making many fine-grained calls to each other.

```
// ANTI-PATTERN: Chatty communication
class OrderService {
  createOrder(customerId, items) {
    customer = this.customerService.getCustomer(customerId)
    this.customerService.validateCustomer(customer)
    address = this.customerService.getDefaultAddress(customerId)
    this.customerService.validateAddress(address)
    credit = this.customerService.getCreditLimit(customerId)
    // ...5 more calls...
  }
}
```

**Why it's harmful:**
- Network overhead (if distributed)
- Tight coupling through multiple calls
- Harder to maintain consistency
- Sign of wrong service boundaries

**How to fix:**
- Consider merging services
- Create coarse-grained operations
- Use data transfer objects

```
// BETTER: Coarse-grained call
class OrderService {
  createOrder(customerId, items) {
    customerContext = this.customerService.getOrderContext(customerId)
    // Single call returns everything needed
  }
}
```

---

### Distributed Monolith

**The problem:**
Services that must be deployed and changed together.

**Signs:**
- Changing Service A requires changing Service B
- Services share database tables
- Circular dependencies between services
- Deployment order matters

**Why it's harmful:**
- Worst of both worlds: distribution complexity without independence
- Can't scale or deploy independently
- Adds network failures without adding flexibility

**How to fix:**
- Draw actual dependency graph
- Services should be independently deployable
- If they always change together, merge them

---

## Repository Anti-Patterns

### Generic Repository

**The problem:**
One-size-fits-all repository interface that handles any entity.

```
// ANTI-PATTERN: Generic repository
interface Repository<T> {
  findById(id) → T
  findAll() → T[]
  save(entity: T)
  delete(id)
  query(specification) → T[]
}

class UserService {
  constructor(repo: Repository<User>) { ... }
}
```

**Why it's harmful:**
- Doesn't expose domain-meaningful operations
- Leaks query logic to callers
- False abstraction - entities have different access patterns
- `findAll()` on a table with millions of rows?

**Correct approach:**
Entity-specific repositories with meaningful methods.

```
// BETTER: Domain-specific repository
interface UserRepository {
  findById(id) → User | null
  findByEmail(email) → User | null
  findActiveUsers(since: Date) → User[]
  // No generic query() method
}
```

---

### Repository Returning Primitives

**The problem:**
Repository methods returning raw data instead of domain objects.

```
// ANTI-PATTERN: Returns primitives
interface UserRepository {
  findById(id) → { id: string, email: string, created: string }
}

// Caller must construct domain object
class UserService {
  getUser(id) {
    data = this.repo.findById(id)
    return new User(data.id, data.email, new Date(data.created))  // Mapping here
  }
}
```

**Why it's harmful:**
- Mapping logic scattered
- Repository knows about database, caller knows about mapping
- Inconsistent domain objects possible

**Correct approach:**
Repository owns the mapping.

```
// BETTER: Returns domain objects
interface UserRepository {
  findById(id) → User | null  // Already mapped
}
```

---

## Domain Events Anti-Patterns

### Events as Remote Procedure Calls

**The problem:**
Using events to trigger actions and waiting for response.

```
// ANTI-PATTERN: Event as RPC
class OrderService {
  createOrder(data) {
    order = new Order(data)
    event = new ValidateOrderRequested(order)
    this.eventBus.publish(event)
    
    // Waiting for response event - this is RPC!
    validationResult = await this.eventBus.waitFor(
      OrderValidated,
      (e) => e.orderId == order.id
    )
    
    if (!validationResult.isValid) throw Error()
  }
}
```

**Why it's harmful:**
- Adds complexity without decoupling benefit
- Still synchronous, just obfuscated
- Harder to debug than direct call
- Timeout handling complexity

**Correct approach:**
Use direct call for synchronous needs, events for async reactions.

```
// BETTER: Direct call for synchronous validation
class OrderService {
  createOrder(data) {
    this.validator.validate(data)  // Direct, synchronous
    order = new Order(data)
    this.repo.save(order)
    this.eventBus.publish(new OrderCreated(order))  // Async reactions
  }
}
```

---

### Bidirectional Events

**The problem:**
Services publishing events that trigger events back to themselves.

```
// ANTI-PATTERN: Event ping-pong
OrderService publishes OrderCreated
  → InventoryService subscribes, publishes InventoryReserved
    → OrderService subscribes, publishes OrderConfirmed
      → ShippingService subscribes, publishes ShipmentScheduled
        → OrderService subscribes, updates order...
```

**Why it's harmful:**
- Hard to trace flow
- Easy to create infinite loops
- Debugging nightmare
- Often hides that services are too coupled

**How to fix:**
- Events flow one direction (downstream)
- If bidirectional communication needed, reconsider boundaries
- Use choreography for simple flows, orchestration for complex

---

## Circuit Breaker Anti-Patterns

### Circuit Breaker Everywhere

**The problem:**
Adding circuit breakers to every call, including local operations.

```
// ANTI-PATTERN: Circuit breaker on local call
userCircuit = new CircuitBreaker(() => this.repo.findById(id))

// Even worse
validationCircuit = new CircuitBreaker(() => validateEmail(email))
```

**Why it's harmful:**
- Overhead without benefit for local calls
- Masks actual problems (why would local repo fail repeatedly?)
- False confidence in resilience

**Correct approach:**
Circuit breakers for network calls to external services.

---

### Ignoring Circuit State

**The problem:**
Catching circuit open errors and retrying anyway.

```
// ANTI-PATTERN: Defeating the circuit
try {
  result = paymentCircuit.execute(amount)
} catch (CircuitOpenError) {
  // Circuit open, let me just try anyway...
  result = paymentService.charge(amount)  // Defeats the purpose!
}
```

**Why it's harmful:**
- Circuit breaker exists to prevent overload
- Bypassing it continues hammering failing service
- Wasted resources

**Correct approach:**
Handle circuit open gracefully.

```
// BETTER: Graceful degradation
try {
  result = paymentCircuit.execute(amount)
} catch (CircuitOpenError) {
  // Queue for later, show user-friendly message
  this.retryQueue.enqueue(new DeferredPayment(amount, order))
  return PaymentResult.deferred("We'll process your payment shortly")
}
```

---

## General Anti-Patterns

### Pattern Cargo Culting

**The problem:**
Applying patterns because "best practice" without understanding the problem they solve.

**Signs:**
- "We always use Repository pattern"
- "DDD says we need aggregates"
- Patterns applied to trivial problems
- Architecture diagram looks impressive but code is simple CRUD

**How to fix:**
Start with the problem. What specific issue does this pattern solve here?

---

### Premature Abstraction

**The problem:**
Creating abstractions before understanding the concrete cases.

```
// ANTI-PATTERN: Abstraction with one implementation
interface MessageSender { send(message) }
class EmailMessageSender implements MessageSender { ... }
// No other senders exist or are planned
```

**Why it's harmful:**
- Abstractions are guesses about future variation
- Wrong abstraction harder to fix than no abstraction
- Adds indirection without flexibility

**Rule of thumb:**
Wait for the third concrete case before abstracting, or until you have clear evidence of needed variation.

---

### Leaky Abstractions

**The problem:**
Abstractions that don't fully hide what they abstract.

```
// ANTI-PATTERN: Leaky repository
interface UserRepository {
  findById(id) → User
  executeSql(query: string) → any[]  // Leaks SQL!
  getConnection() → DatabaseConnection  // Leaks database!
}
```

**Why it's harmful:**
- Callers can bypass abstraction
- Implementation details leak out
- Abstraction provides false security

**Correct approach:**
If abstraction is needed, make it complete.
