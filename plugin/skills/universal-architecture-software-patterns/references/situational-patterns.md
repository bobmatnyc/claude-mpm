# Situational Patterns

Apply these patterns when specific problems emerge. Don't apply preemptively.

## Repository Pattern

### What Problem It Solves

When services contain data access logic:
- **Testing requires database**: Can't unit test without real database
- **Database changes ripple**: Changing schema affects business logic
- **Query duplication**: Same queries written in multiple places
- **Vendor lock-in**: Database-specific code everywhere

### The Pattern

Abstract data access behind a domain-focused interface.

```
// Interface speaks domain language
interface UserRepository {
  findById(id) → User | null
  findByEmail(email) → User | null
  save(user) → User
  delete(id) → void
  findActiveUsers() → User[]
}

// Implementation hides database details
class PostgresUserRepository implements UserRepository {
  constructor(connection) {
    this.connection = connection
  }
  
  findById(id) {
    row = this.connection.query("SELECT * FROM users WHERE id = $1", [id])
    return row ? this.mapToUser(row) : null
  }
  
  findActiveUsers() {
    rows = this.connection.query(
      "SELECT * FROM users WHERE status = 'active' AND last_login > $1",
      [thirtyDaysAgo]
    )
    return rows.map(this.mapToUser)
  }
  
  private mapToUser(row) {
    return new User(row.id, row.email, row.name, ...)
  }
}
```

### When to Apply

**Apply when:**
- Multiple services access same data
- Business logic mixes with SQL/queries
- Changing database would require touching business code
- Same queries appear in multiple places

**Skip when:**
- Simple CRUD with minimal logic
- Single service, simple data needs
- Framework provides adequate abstraction

### Implementation Guidelines

**Domain language in interface**
Methods named for business concepts, not database operations.

```
// GOOD: Domain language
interface OrderRepository {
  findPendingOrders() → Order[]
  findByCustomer(customerId) → Order[]
}

// AVOID: Database language
interface OrderRepository {
  executeQuery(sql) → Row[]
  findByColumn(column, value) → Row[]
}
```

**Return domain objects, not database rows**

```
// GOOD: Returns domain entity
findById(id) → User

// AVOID: Returns raw data
findById(id) → { id: string, email: string, ... }
```

**Encapsulate complex queries**

```
// Complex query logic hidden in repository
findEligibleForPromotion() {
  // 20-line query with joins and conditions
  // Business code just calls this method
}
```

---

## Domain Events

### What Problem It Solves

When services call each other directly:
- **Circular dependencies**: Service A calls B calls C calls A
- **Temporal coupling**: All services must be available simultaneously
- **Knowledge spread**: Service A knows too much about B, C, D
- **Difficult scaling**: Adding new reactions requires modifying source

### The Pattern

Services emit events; interested parties subscribe.

```
// BEFORE: Direct coupling
class UserService {
  createUser(data) {
    user = this.repository.save(data)
    this.billingService.createAccount(user)      // Knows about billing
    this.notificationService.sendWelcome(user)   // Knows about notifications
    this.analyticsService.trackSignup(user)      // Knows about analytics
    return user
  }
}

// AFTER: Event-driven
class UserService {
  createUser(data) {
    user = this.repository.save(data)
    this.eventBus.publish(new UserCreated(user))  // Doesn't know who listens
    return user
  }
}

// Subscribers handle their own concerns
class BillingService {
  onUserCreated(event) {
    this.createAccount(event.user)
  }
}

class NotificationService {
  onUserCreated(event) {
    this.sendWelcome(event.user)
  }
}
```

### When to Apply

**Apply when:**
- Services call each other in cycles
- Adding new reactions requires modifying existing services
- Services need to react without blocking the source
- Multiple services need to know when something happens

**Skip when:**
- Immediate response required (use direct call)
- Only one consumer exists
- Debugging/tracing complexity outweighs benefits
- Simple linear flow without branching reactions

### Event Design

**Events are facts about the past**

```
// GOOD: Past tense, fact
UserCreated { userId, timestamp }
OrderShipped { orderId, trackingNumber, timestamp }

// AVOID: Commands or requests
CreateUserAccount { ... }
PleaseShipOrder { ... }
```

**Include enough context**

```
// GOOD: Self-contained
OrderCreated {
  orderId
  customerId
  items: [{ productId, quantity, price }]
  totalAmount
  timestamp
}

// AVOID: Requires lookup
OrderCreated {
  orderId  // Consumer must call back to get details
}
```

**Events are immutable**
Once published, never modify. Version if schema changes.

### Implementation Patterns

**In-process event bus**
Simple, synchronous, same transaction.

```
class EventBus {
  handlers = {}
  
  subscribe(eventType, handler) {
    this.handlers[eventType].push(handler)
  }
  
  publish(event) {
    for (handler of this.handlers[event.type]) {
      handler(event)
    }
  }
}
```

**Message queue (async)**
Durable, distributed, eventual consistency.

```
// Publisher
messageQueue.publish("user.created", event)

// Consumer (separate process)
messageQueue.subscribe("user.created", (event) => {
  billingService.createAccount(event.user)
})
```

---

## Anti-Corruption Layer (ACL)

### What Problem It Solves

When integrating external systems:
- **API changes break your code**: External update causes cascading failures
- **Foreign concepts leak in**: External terminology in your domain
- **Testing difficulty**: Can't test without external system
- **Coupling to volatility**: Your stability depends on their stability

### The Pattern

Wrap external systems in your own interface that speaks your domain language.

```
// External API (you don't control)
StripeAPI {
  createCustomer(email, source) → { customer_id, default_source }
  chargeCustomer(customer_id, amount_cents, currency) → { charge_id, status }
}

// Your domain interface
interface PaymentProvider {
  createCustomerAccount(customer: Customer) → AccountId
  charge(accountId: AccountId, amount: Money) → ChargeResult
}

// ACL translates between them
class StripePaymentProvider implements PaymentProvider {
  constructor(stripeApi) {
    this.stripe = stripeApi
  }
  
  createCustomerAccount(customer) {
    result = this.stripe.createCustomer(customer.email, customer.paymentSource)
    return new AccountId(result.customer_id)
  }
  
  charge(accountId, amount) {
    result = this.stripe.chargeCustomer(
      accountId.value,
      amount.toCents(),
      amount.currency
    )
    return new ChargeResult(
      result.charge_id,
      this.mapStatus(result.status)
    )
  }
  
  private mapStatus(stripeStatus) {
    switch(stripeStatus) {
      case "succeeded": return ChargeStatus.Completed
      case "pending": return ChargeStatus.Processing
      case "failed": return ChargeStatus.Failed
    }
  }
}
```

### When to Apply

**Apply when:**
- Integrating third-party APIs
- Wrapping legacy systems
- External system uses different terminology
- External system may be replaced
- External changes have caused production issues

**Skip when:**
- Internal service you control
- Simple, stable integration (logging, metrics)
- Translation overhead outweighs isolation benefit

### Implementation Guidelines

**Your interface, your language**

```
// External uses "customer_id", you use "AccountId"
// External uses cents, you use Money value object
// External uses string status, you use enum
```

**Handle external failures**

```
charge(accountId, amount) {
  try {
    result = this.stripe.chargeCustomer(...)
    return success(this.mapResult(result))
  } catch (StripeError e) {
    return failure(this.mapError(e))  // Translate their errors too
  }
}
```

**Version your interface, not theirs**

```
// Your interface stays stable
interface PaymentProvider {
  charge(accountId, amount) → ChargeResult
}

// ACL adapts to API changes internally
class StripePaymentProvider_v3 implements PaymentProvider {
  // New Stripe API version, same interface
}
```

---

## Circuit Breaker

### What Problem It Solves

When external services fail:
- **Cascading failures**: One slow service blocks everything
- **Resource exhaustion**: Threads/connections waiting on timeouts
- **Poor user experience**: Long waits before errors
- **Recovery delay**: Even after external recovers, backlog causes issues

### The Pattern

Monitor failure rate; when threshold exceeded, fail fast without calling.

```
class CircuitBreaker {
  state = CLOSED  // CLOSED = normal, OPEN = failing fast, HALF_OPEN = testing
  failureCount = 0
  lastFailureTime = null
  
  constructor(operation, options) {
    this.operation = operation
    this.failureThreshold = options.failureThreshold  // e.g., 5
    this.resetTimeout = options.resetTimeout          // e.g., 30000ms
  }
  
  execute(...args) {
    if (this.state == OPEN) {
      if (timeSince(this.lastFailureTime) > this.resetTimeout) {
        this.state = HALF_OPEN  // Try one request
      } else {
        throw new CircuitOpenError()  // Fail fast
      }
    }
    
    try {
      result = this.operation(...args)
      this.onSuccess()
      return result
    } catch (error) {
      this.onFailure()
      throw error
    }
  }
  
  onSuccess() {
    this.failureCount = 0
    this.state = CLOSED
  }
  
  onFailure() {
    this.failureCount++
    this.lastFailureTime = now()
    if (this.failureCount >= this.failureThreshold) {
      this.state = OPEN
    }
  }
}
```

### Usage

```
// Wrap external call
paymentCircuit = new CircuitBreaker(
  (amount, customer) => stripeApi.charge(amount, customer),
  { failureThreshold: 5, resetTimeout: 30000 }
)

// Use wrapped operation
try {
  result = paymentCircuit.execute(amount, customer)
} catch (CircuitOpenError) {
  // Handle gracefully - maybe queue for retry, show message
  return "Payment processing delayed, we'll charge you shortly"
}
```

### When to Apply

**Apply when:**
- Calling external services over network
- Downstream service has reliability issues
- Cascading failures have occurred
- System needs to degrade gracefully

**Skip when:**
- Local operations (no network)
- Failure is acceptable/expected (optional features)
- Already have retry/timeout at infrastructure level

### Configuration Guidelines

**Failure threshold**
Depends on normal error rate. If 1% errors normal, threshold of 5 in 100 requests.

**Reset timeout**
Depends on typical recovery time. Start with 30 seconds, adjust based on observation.

**Timeout per call**
Circuit breaker doesn't replace timeouts. Still timeout individual calls.

```
// Both timeout AND circuit breaker
paymentCircuit = new CircuitBreaker(
  (amount, customer) => withTimeout(
    stripeApi.charge(amount, customer),
    5000  // 5 second timeout
  ),
  { failureThreshold: 5, resetTimeout: 30000 }
)
```

---

## Unit of Work

### What Problem It Solves

When multiple repositories need atomic updates:
- **Partial updates**: First save succeeds, second fails, data inconsistent
- **Transaction management**: Business logic mixed with transaction code
- **Scattered commits**: Multiple commit points, hard to reason about

### The Pattern

Coordinate multiple repository operations as single transaction.

```
class UnitOfWork {
  private dirtyEntities = []
  private newEntities = []
  private deletedEntities = []
  
  registerNew(entity) {
    this.newEntities.push(entity)
  }
  
  registerDirty(entity) {
    this.dirtyEntities.push(entity)
  }
  
  registerDeleted(entity) {
    this.deletedEntities.push(entity)
  }
  
  commit() {
    transaction = this.connection.beginTransaction()
    try {
      for (entity of this.newEntities) {
        this.insert(entity)
      }
      for (entity of this.dirtyEntities) {
        this.update(entity)
      }
      for (entity of this.deletedEntities) {
        this.delete(entity)
      }
      transaction.commit()
    } catch (error) {
      transaction.rollback()
      throw error
    }
  }
}
```

### Usage

```
function transferFunds(fromAccount, toAccount, amount, unitOfWork) {
  fromAccount.debit(amount)
  toAccount.credit(amount)
  
  unitOfWork.registerDirty(fromAccount)
  unitOfWork.registerDirty(toAccount)
  unitOfWork.commit()  // Both or neither
}
```

### When to Apply

**Apply when:**
- Multiple entities must update atomically
- Business operations span multiple repositories
- Need to defer persistence until operation complete

**Skip when:**
- Single entity operations
- Eventual consistency acceptable
- Framework provides transaction management

---

## Specification Pattern

### What Problem It Solves

When business rules become complex:
- **Conditional spaghetti**: Nested if statements for eligibility checks
- **Duplication**: Same rules in multiple places
- **Untestable**: Can't test rules in isolation
- **Rigid**: Adding new criteria requires modifying existing code

### The Pattern

Encapsulate business rules as composable objects.

```
// Base specification
interface Specification<T> {
  isSatisfiedBy(candidate: T) → boolean
}

// Concrete specifications
class HasActiveSubscription implements Specification<Customer> {
  isSatisfiedBy(customer) {
    return customer.subscription?.status == "active"
  }
}

class AccountOlderThan implements Specification<Customer> {
  constructor(days) {
    this.days = days
  }
  
  isSatisfiedBy(customer) {
    return daysSince(customer.createdAt) > this.days
  }
}

// Composition
class AndSpecification implements Specification<T> {
  constructor(left, right) {
    this.left = left
    this.right = right
  }
  
  isSatisfiedBy(candidate) {
    return this.left.isSatisfiedBy(candidate) 
        && this.right.isSatisfiedBy(candidate)
  }
}

// Usage
eligibleForDiscount = and(
  new HasActiveSubscription(),
  new AccountOlderThan(30)
)

if (eligibleForDiscount.isSatisfiedBy(customer)) {
  applyDiscount(order)
}
```

### When to Apply

**Apply when:**
- Complex eligibility or validation rules
- Rules reused in multiple contexts
- Rules need to be tested independently
- Rules change frequently
- Rules combine in different ways

**Skip when:**
- Simple boolean checks
- Rules never reused
- Overhead exceeds benefit
