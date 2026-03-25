# Foundational Patterns

These patterns form the structural foundation for maintainable systems. Apply by default unless specific constraints prevent it.

## Dependency Injection (DI)

### What Problem It Solves

Classes that instantiate their own dependencies become:
- **Untestable**: Can't substitute test doubles
- **Rigid**: Changing implementation requires changing consumers  
- **Coupled**: Component knows too much about its dependencies

### The Pattern

Dependencies are passed to a component rather than created by it.

```
// BEFORE: Component creates dependency
class UserService {
  notifier = new EmailNotifier()  // Hardcoded
  
  createUser(data) {
    user = save(data)
    this.notifier.send(user.email, "Welcome")
  }
}

// AFTER: Dependency injected
class UserService {
  constructor(notifier) {
    this.notifier = notifier  // Injected
  }
  
  createUser(data) {
    user = save(data)
    this.notifier.send(user.email, "Welcome")
  }
}

// Usage
service = new UserService(new EmailNotifier())      // Production
testService = new UserService(new MockNotifier())   // Testing
```

### Implementation Approaches

**Constructor Injection (Preferred)**
Dependencies passed via constructor. Makes dependencies explicit and immutable.

```
class OrderService {
  constructor(repository, paymentGateway, notifier) {
    this.repository = repository
    this.paymentGateway = paymentGateway
    this.notifier = notifier
  }
}
```

**Setter Injection**
Dependencies set via methods. Allows optional dependencies but makes object state mutable.

```
class OrderService {
  setRepository(repository) {
    this.repository = repository
  }
}
```

**Interface Injection**
Component declares interface for receiving dependencies. Less common.

**Factory Functions**
Functional approach achieving same decoupling.

```
function createUserService(notifier) {
  return {
    createUser(data) {
      user = save(data)
      notifier.send(user.email, "Welcome")
      return user
    }
  }
}
```

### DI Containers

Containers automate dependency wiring. Useful for large applications with many dependencies.

```
// Registration
container.register('Notifier', EmailNotifier)
container.register('UserRepository', PostgresUserRepository)
container.register('UserService', UserService, ['Notifier', 'UserRepository'])

// Resolution
service = container.resolve('UserService')  // Wired automatically
```

**When to use containers:**
- Many services with complex dependency graphs
- Multiple environments (dev/test/prod) with different implementations
- Need lifecycle management (singleton vs transient)

**When NOT to use containers:**
- Small applications (<10 services)
- Simple dependency graphs
- When explicit wiring provides clarity

### When to Deviate from DI

**Stable, stateless utilities**
Math functions, string utilities, pure functions with no state.

```
// OK to call directly - stable utility
hash = calculateSHA256(data)
```

**Framework-managed components**
When framework handles lifecycle (React components, HTTP handlers).

```
// Framework manages instantiation
function UserPage({ userId }) {
  // OK: framework-injected props
}
```

**Value objects**
Immutable data carriers without behavior dependencies.

```
// OK: no dependencies
point = new Point(x, y)
```

### Testing with DI

DI enables test doubles:

```
// Unit test with mock
test("createUser sends notification") {
  mockNotifier = new MockNotifier()
  service = new UserService(mockNotifier)
  
  service.createUser({ email: "test@example.com" })
  
  assert mockNotifier.wasCalled()
  assert mockNotifier.lastRecipient == "test@example.com"
}

// Integration test with real implementation
test("createUser stores in database") {
  realRepo = new TestDatabaseRepository()
  service = new UserService(new NullNotifier(), realRepo)
  
  user = service.createUser({ email: "test@example.com" })
  
  assert realRepo.findById(user.id) != null
}
```

---

## Service-Oriented Architecture (SOA)

### What Problem It Solves

Without clear boundaries:
- **Logic scatters**: Same business rule in multiple places
- **Changes ripple**: Modifying one thing breaks unrelated things
- **Ownership unclear**: No one knows who maintains what
- **Testing difficult**: Can't test in isolation

### The Pattern

Organize code into services with:
- Clear boundaries and responsibilities
- Well-defined interfaces
- Internal implementation hidden
- Explicit dependencies between services

```
// Service boundary
UserService
├── Interface (public contract)
│   ├── createUser(data) → User
│   ├── findById(id) → User | null
│   └── updateUser(id, data) → User
├── Implementation (hidden)
│   ├── validation logic
│   ├── persistence calls
│   └── event publishing
└── Dependencies (explicit)
    ├── UserRepository
    ├── Notifier
    └── EventBus
```

### Service Boundary Guidelines

**By Business Capability**
Group by what the business does, not technical layers.

```
// GOOD: Business capabilities
UserService       // User lifecycle
OrderService      // Order processing  
InventoryService  // Stock management

// AVOID: Technical layers
DatabaseService   // Too broad
ValidationService // Cross-cutting concern
```

**Single Responsibility**
Each service owns one cohesive concept.

```
// GOOD: Focused responsibility
PaymentService {
  processPayment(order, paymentMethod)
  refund(paymentId, amount)
  getPaymentStatus(paymentId)
}

// AVOID: Mixed responsibilities
PaymentAndShippingService {
  processPayment(...)
  calculateShipping(...)  // Different concern
  refund(...)
  trackPackage(...)       // Different concern
}
```

**Data Ownership**
Services own their data; others access via service interface.

```
// GOOD: UserService owns user data
OrderService {
  createOrder(userId, items) {
    user = this.userService.findById(userId)  // Via service
    // ...
  }
}

// AVOID: Direct data access
OrderService {
  createOrder(userId, items) {
    user = this.database.query("SELECT * FROM users...")  // Bypasses service
  }
}
```

### Interface Design

**Expose capabilities, not data structures**

```
// GOOD: Capability-focused
interface InventoryService {
  reserveStock(productId, quantity) → ReservationId
  releaseReservation(reservationId)
  checkAvailability(productId) → AvailabilityStatus
}

// AVOID: Data-focused
interface InventoryService {
  getInventoryRecord(productId) → InventoryRecord  // Exposes internal structure
  updateInventoryRecord(record)                     // Allows arbitrary mutation
}
```

**Version interfaces when changing**

```
// v1 still supported
interface UserService_v1 {
  getUser(id) → { name, email }
}

// v2 adds fields
interface UserService_v2 {
  getUser(id) → { name, email, preferences }
}
```

### Service Communication

**Synchronous (request/response)**
For immediate, required responses.

```
// Order needs user data NOW
user = userService.findById(userId)
if (!user) throw new Error("User not found")
```

**Asynchronous (events)**
For notifications, eventual consistency.

```
// Order doesn't wait for notification
orderService.createOrder(data)
eventBus.publish(OrderCreated(order))  // Listeners handle async
```

### When to Merge Services

**Chatty communication**
If services constantly call each other, they may be one service split wrong.

```
// Sign of wrong boundary
OrderService.createOrder() {
  this.pricingService.calculatePrice()
  this.pricingService.applyDiscounts()
  this.pricingService.calculateTax()
  this.pricingService.formatTotal()
}

// Consider: pricing is part of order creation
```

**Shared data mutation**
If two services need to modify same data atomically, they may belong together.

**Artificial separation**
If separation exists only for "clean architecture" but adds no value.

### Testing Services

**Unit tests**: Mock dependencies, test service logic

```
test("createOrder validates user exists") {
  mockUserService = new MockUserService()
  mockUserService.willReturn(null)  // User not found
  
  orderService = new OrderService(mockUserService, ...)
  
  assertThrows(() => orderService.createOrder(invalidUserId, items))
}
```

**Integration tests**: Real dependencies, test service interactions

```
test("createOrder persists and publishes event") {
  // Real implementations in test database
  orderService = new OrderService(realUserService, realRepo, realEventBus)
  
  order = orderService.createOrder(userId, items)
  
  assert realRepo.findById(order.id) != null
  assert realEventBus.lastEvent instanceof OrderCreated
}
```

---

## DI + SOA Together

The patterns complement each other:

- **SOA** defines service boundaries and interfaces
- **DI** manages dependencies between services

```
// SOA: Service boundaries
UserService ─────depends on────▶ UserRepository
     │                                │
     │                                ▼
     └────depends on────▶ Notifier ◀─── DI: Injected at construction

// Composition root wires everything
function createApplication() {
  repository = new PostgresUserRepository(dbConnection)
  notifier = new EmailNotifier(smtpConfig)
  userService = new UserService(repository, notifier)
  
  return { userService }
}
```

**DI enables SOA testing**
Because services receive dependencies, you can test each service in isolation.

**SOA guides DI boundaries**
Service interfaces define what gets injected where.
