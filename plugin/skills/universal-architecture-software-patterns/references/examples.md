# Pattern Examples

Language-agnostic pseudocode demonstrating pattern implementations and combinations.

## Example 1: E-Commerce Order System

Demonstrates: DI, SOA, Repository, Domain Events, Circuit Breaker

### Problem Context
- Orders require inventory check, payment processing, notification
- Payment provider occasionally has outages
- Multiple teams own different capabilities

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Composition Root                         │
│  (Wires all dependencies at startup)                        │
└─────────────────────────────────────────────────────────────┘
         │              │               │              │
         ▼              ▼               ▼              ▼
   ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌───────────┐
   │ Order    │  │ Inventory │  │  Payment   │  │Notification│
   │ Service  │  │  Service  │  │  Service   │  │  Service  │
   └────┬─────┘  └─────┬─────┘  └──────┬─────┘  └─────┬─────┘
        │              │               │              │
        ▼              ▼               ▼              ▼
   ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌───────────┐
   │  Order   │  │ Inventory │  │  Payment   │  │   Email   │
   │Repository│  │ Repository│  │  Gateway   │  │  Gateway  │
   └──────────┘  └───────────┘  │ (with ACL) │  └───────────┘
                               └────────────┘
                                     │
                               ┌─────┴─────┐
                               │  Circuit  │
                               │  Breaker  │
                               └───────────┘
```

### Implementation

```
// ═══════════════════════════════════════════════════════════
// REPOSITORIES (Data Access Abstraction)
// ═══════════════════════════════════════════════════════════

interface OrderRepository {
  save(order: Order) → Order
  findById(id: OrderId) → Order | null
  findByCustomer(customerId: CustomerId) → Order[]
}

interface InventoryRepository {
  findByProduct(productId: ProductId) → InventoryItem | null
  reserve(productId: ProductId, quantity: int) → ReservationId
  release(reservationId: ReservationId)
}

// ═══════════════════════════════════════════════════════════
// ANTI-CORRUPTION LAYER (External Payment Provider)
// ═══════════════════════════════════════════════════════════

// Your interface (your language)
interface PaymentGateway {
  charge(amount: Money, method: PaymentMethod) → PaymentResult
  refund(paymentId: PaymentId, amount: Money) → RefundResult
}

// ACL Implementation
class StripePaymentGateway implements PaymentGateway {
  constructor(stripeClient, circuitBreaker) {
    this.stripe = stripeClient
    this.circuit = circuitBreaker
  }
  
  charge(amount, method) {
    // Circuit breaker wraps external call
    return this.circuit.execute(() => {
      // Translate your types to Stripe types
      stripeResult = this.stripe.createCharge({
        amount: amount.toCents(),
        currency: amount.currency.code,
        source: this.mapPaymentMethod(method)
      })
      // Translate Stripe response to your types
      return new PaymentResult(
        PaymentId(stripeResult.id),
        this.mapStatus(stripeResult.status)
      )
    })
  }
  
  private mapStatus(stripeStatus) {
    return match(stripeStatus) {
      "succeeded" => PaymentStatus.Completed
      "pending" => PaymentStatus.Processing
      "failed" => PaymentStatus.Failed
    }
  }
}

// ═══════════════════════════════════════════════════════════
// DOMAIN EVENTS
// ═══════════════════════════════════════════════════════════

class OrderCreated {
  orderId: OrderId
  customerId: CustomerId
  items: OrderItem[]
  timestamp: DateTime
}

class PaymentCompleted {
  orderId: OrderId
  paymentId: PaymentId
  amount: Money
  timestamp: DateTime
}

class OrderShipped {
  orderId: OrderId
  trackingNumber: string
  timestamp: DateTime
}

// ═══════════════════════════════════════════════════════════
// SERVICES (Business Logic)
// ═══════════════════════════════════════════════════════════

class OrderService {
  constructor(
    orderRepo: OrderRepository,
    inventoryService: InventoryService,
    paymentGateway: PaymentGateway,
    eventBus: EventBus
  ) {
    this.orderRepo = orderRepo
    this.inventory = inventoryService
    this.payment = paymentGateway
    this.events = eventBus
  }
  
  createOrder(customerId, items, paymentMethod) {
    // Reserve inventory
    reservations = []
    for (item of items) {
      reservation = this.inventory.reserve(item.productId, item.quantity)
      reservations.push(reservation)
    }
    
    // Calculate total
    total = this.calculateTotal(items)
    
    // Process payment
    paymentResult = this.payment.charge(total, paymentMethod)
    
    if (paymentResult.status != PaymentStatus.Completed) {
      // Release reservations on payment failure
      for (reservation of reservations) {
        this.inventory.release(reservation)
      }
      throw new PaymentFailedError(paymentResult)
    }
    
    // Create order
    order = Order.create(customerId, items, paymentResult.paymentId)
    this.orderRepo.save(order)
    
    // Publish event - don't know or care who listens
    this.events.publish(new OrderCreated(
      order.id,
      customerId,
      items,
      DateTime.now()
    ))
    
    return order
  }
}

// Notification service subscribes to events
class NotificationService {
  constructor(emailGateway, templateEngine) {
    this.email = emailGateway
    this.templates = templateEngine
  }
  
  // Called by event bus, not by OrderService
  onOrderCreated(event: OrderCreated) {
    customer = this.customerRepo.findById(event.customerId)
    body = this.templates.render("order-confirmation", {
      orderId: event.orderId,
      items: event.items
    })
    this.email.send(customer.email, "Order Confirmed", body)
  }
  
  onOrderShipped(event: OrderShipped) {
    // Different reaction to different event
    // ...
  }
}

// ═══════════════════════════════════════════════════════════
// COMPOSITION ROOT (Wiring)
// ═══════════════════════════════════════════════════════════

function createApplication(config) {
  // Infrastructure
  database = createDatabaseConnection(config.database)
  stripeClient = new StripeClient(config.stripe.apiKey)
  smtpClient = new SmtpClient(config.smtp)
  eventBus = new InProcessEventBus()
  
  // Circuit breaker for unreliable external service
  paymentCircuit = new CircuitBreaker({
    failureThreshold: 5,
    resetTimeout: 30000
  })
  
  // Repositories
  orderRepo = new PostgresOrderRepository(database)
  inventoryRepo = new PostgresInventoryRepository(database)
  customerRepo = new PostgresCustomerRepository(database)
  
  // Gateways (with ACL)
  paymentGateway = new StripePaymentGateway(stripeClient, paymentCircuit)
  emailGateway = new SmtpEmailGateway(smtpClient)
  
  // Services
  inventoryService = new InventoryService(inventoryRepo)
  notificationService = new NotificationService(emailGateway, templateEngine)
  orderService = new OrderService(
    orderRepo,
    inventoryService,
    paymentGateway,
    eventBus
  )
  
  // Subscribe event handlers
  eventBus.subscribe(OrderCreated, notificationService.onOrderCreated)
  eventBus.subscribe(OrderShipped, notificationService.onOrderShipped)
  
  return { orderService, inventoryService }
}
```

---

## Example 2: User Authentication System

Demonstrates: DI, Repository, Specification Pattern

### Problem Context
- Complex eligibility rules for premium features
- Multiple storage backends (some users in legacy system)
- Rules change frequently

### Implementation

```
// ═══════════════════════════════════════════════════════════
// SPECIFICATION PATTERN (Complex Business Rules)
// ═══════════════════════════════════════════════════════════

interface Specification<T> {
  isSatisfiedBy(candidate: T) → boolean
}

class And<T> implements Specification<T> {
  constructor(left: Specification<T>, right: Specification<T>) {
    this.left = left
    this.right = right
  }
  isSatisfiedBy(candidate) {
    return this.left.isSatisfiedBy(candidate) 
        && this.right.isSatisfiedBy(candidate)
  }
}

class Or<T> implements Specification<T> {
  constructor(left: Specification<T>, right: Specification<T>) {
    this.left = left
    this.right = right
  }
  isSatisfiedBy(candidate) {
    return this.left.isSatisfiedBy(candidate) 
        || this.right.isSatisfiedBy(candidate)
  }
}

class Not<T> implements Specification<T> {
  constructor(spec: Specification<T>) {
    this.spec = spec
  }
  isSatisfiedBy(candidate) {
    return !this.spec.isSatisfiedBy(candidate)
  }
}

// Concrete user specifications
class HasActiveSubscription implements Specification<User> {
  isSatisfiedBy(user) {
    return user.subscription?.status == "active"
  }
}

class AccountAgeGreaterThan implements Specification<User> {
  constructor(days: int) {
    this.days = days
  }
  isSatisfiedBy(user) {
    return daysBetween(user.createdAt, now()) > this.days
  }
}

class HasVerifiedEmail implements Specification<User> {
  isSatisfiedBy(user) {
    return user.emailVerifiedAt != null
  }
}

class IsInBetaProgram implements Specification<User> {
  isSatisfiedBy(user) {
    return user.betaProgramEnrolledAt != null
  }
}

class HasCompletedOnboarding implements Specification<User> {
  isSatisfiedBy(user) {
    return user.onboardingCompletedAt != null
  }
}

// ═══════════════════════════════════════════════════════════
// COMPOSED ELIGIBILITY RULES
// ═══════════════════════════════════════════════════════════

class EligibilityRules {
  // Premium features: active subscription + verified email + 30 days old
  premiumFeatures = and(
    new HasActiveSubscription(),
    and(
      new HasVerifiedEmail(),
      new AccountAgeGreaterThan(30)
    )
  )
  
  // Beta features: in beta program OR (premium + completed onboarding)
  betaFeatures = or(
    new IsInBetaProgram(),
    and(
      this.premiumFeatures,
      new HasCompletedOnboarding()
    )
  )
  
  // API access: verified email + 7 days old
  apiAccess = and(
    new HasVerifiedEmail(),
    new AccountAgeGreaterThan(7)
  )
}

// ═══════════════════════════════════════════════════════════
// SERVICE USING SPECIFICATIONS
// ═══════════════════════════════════════════════════════════

class FeatureAccessService {
  constructor(userRepo: UserRepository, rules: EligibilityRules) {
    this.userRepo = userRepo
    this.rules = rules
  }
  
  canAccessPremiumFeatures(userId: UserId) → boolean {
    user = this.userRepo.findById(userId)
    if (!user) return false
    return this.rules.premiumFeatures.isSatisfiedBy(user)
  }
  
  canAccessBetaFeatures(userId: UserId) → boolean {
    user = this.userRepo.findById(userId)
    if (!user) return false
    return this.rules.betaFeatures.isSatisfiedBy(user)
  }
  
  getAccessibleFeatures(userId: UserId) → FeatureSet {
    user = this.userRepo.findById(userId)
    if (!user) return FeatureSet.empty()
    
    features = FeatureSet.basic()
    
    if (this.rules.premiumFeatures.isSatisfiedBy(user)) {
      features = features.add(FeatureSet.premium())
    }
    
    if (this.rules.betaFeatures.isSatisfiedBy(user)) {
      features = features.add(FeatureSet.beta())
    }
    
    if (this.rules.apiAccess.isSatisfiedBy(user)) {
      features = features.add(FeatureSet.api())
    }
    
    return features
  }
}
```

**Benefits demonstrated:**
- Rules are testable in isolation
- New rules added without changing service
- Rules compose naturally
- Easy to understand eligibility criteria

---

## Example 3: Data Import Pipeline

Demonstrates: Unit of Work, Repository, Domain Events

### Problem Context
- Importing data from CSV requires atomic operations
- Import creates users, assigns to teams, triggers notifications
- Partial imports cause data inconsistency

### Implementation

```
// ═══════════════════════════════════════════════════════════
// UNIT OF WORK
// ═══════════════════════════════════════════════════════════

class UnitOfWork {
  constructor(connection) {
    this.connection = connection
    this.newEntities = []
    this.dirtyEntities = []
    this.deletedEntities = []
    this.transaction = null
  }
  
  registerNew(entity) {
    this.newEntities.push(entity)
  }
  
  registerDirty(entity) {
    if (!this.dirtyEntities.includes(entity)) {
      this.dirtyEntities.push(entity)
    }
  }
  
  registerDeleted(entity) {
    this.deletedEntities.push(entity)
  }
  
  async commit() {
    this.transaction = await this.connection.beginTransaction()
    try {
      for (entity of this.newEntities) {
        await this.insert(entity)
      }
      for (entity of this.dirtyEntities) {
        await this.update(entity)
      }
      for (entity of this.deletedEntities) {
        await this.delete(entity)
      }
      await this.transaction.commit()
      this.clear()
    } catch (error) {
      await this.transaction.rollback()
      throw error
    }
  }
  
  clear() {
    this.newEntities = []
    this.dirtyEntities = []
    this.deletedEntities = []
  }
  
  private async insert(entity) {
    mapper = this.getMapper(entity)
    await mapper.insert(entity, this.transaction)
  }
  
  // ... update, delete similar
}

// ═══════════════════════════════════════════════════════════
// IMPORT SERVICE
// ═══════════════════════════════════════════════════════════

class UserImportService {
  constructor(
    userRepo: UserRepository,
    teamRepo: TeamRepository,
    unitOfWorkFactory: () => UnitOfWork,
    eventBus: EventBus
  ) {
    this.userRepo = userRepo
    this.teamRepo = teamRepo
    this.createUnitOfWork = unitOfWorkFactory
    this.events = eventBus
  }
  
  async importUsers(csvData: ParsedCSV) → ImportResult {
    uow = this.createUnitOfWork()
    importedUsers = []
    errors = []
    
    for (row of csvData.rows) {
      try {
        user = this.createUserFromRow(row)
        uow.registerNew(user)
        
        if (row.teamName) {
          team = await this.teamRepo.findByName(row.teamName)
          if (team) {
            team.addMember(user)
            uow.registerDirty(team)
          }
        }
        
        importedUsers.push(user)
      } catch (validationError) {
        errors.push({ row: row.rowNumber, error: validationError })
      }
    }
    
    if (errors.length > 0 && !csvData.options.allowPartial) {
      // All or nothing
      return ImportResult.failed(errors)
    }
    
    // Atomic commit
    await uow.commit()
    
    // Events published after successful commit
    for (user of importedUsers) {
      this.events.publish(new UserImported(user))
    }
    
    return ImportResult.success(importedUsers, errors)
  }
}
```

---

## Testing Patterns

### Testing with DI

```
// Unit test - all dependencies mocked
test("createOrder reserves inventory before payment") {
  // Arrange
  mockInventory = new MockInventoryService()
  mockPayment = new MockPaymentGateway()
  mockPayment.willReturn(PaymentResult.success())
  
  service = new OrderService(
    new InMemoryOrderRepository(),
    mockInventory,
    mockPayment,
    new NullEventBus()
  )
  
  // Act
  service.createOrder(customerId, items, paymentMethod)
  
  // Assert
  assert mockInventory.reserveCalledBefore(mockPayment.chargeCall)
}

// Integration test - real implementations
test("createOrder persists order with payment reference") {
  // Real database, mock external payment
  orderRepo = new PostgresOrderRepository(testDatabase)
  mockPayment = new MockPaymentGateway()
  mockPayment.willReturn(PaymentResult.success(paymentId))
  
  service = new OrderService(
    orderRepo,
    new InventoryService(testDatabase),
    mockPayment,
    new InMemoryEventBus()
  )
  
  order = service.createOrder(customerId, items, paymentMethod)
  
  persisted = orderRepo.findById(order.id)
  assert persisted != null
  assert persisted.paymentId == paymentId
}
```

### Testing Specifications

```
test("premium eligibility requires active subscription") {
  spec = new HasActiveSubscription()
  
  activeUser = User.create({ subscription: { status: "active" } })
  inactiveUser = User.create({ subscription: { status: "cancelled" } })
  noSubUser = User.create({ subscription: null })
  
  assert spec.isSatisfiedBy(activeUser) == true
  assert spec.isSatisfiedBy(inactiveUser) == false
  assert spec.isSatisfiedBy(noSubUser) == false
}

test("composed specifications combine correctly") {
  premiumEligible = and(
    new HasActiveSubscription(),
    new AccountAgeGreaterThan(30)
  )
  
  // Active subscription, account is 60 days old
  eligible = User.create({
    subscription: { status: "active" },
    createdAt: daysAgo(60)
  })
  
  // Active subscription, account is 10 days old
  tooNew = User.create({
    subscription: { status: "active" },
    createdAt: daysAgo(10)
  })
  
  assert premiumEligible.isSatisfiedBy(eligible) == true
  assert premiumEligible.isSatisfiedBy(tooNew) == false
}
```

### Testing Circuit Breaker Behavior

```
test("circuit opens after failure threshold") {
  failingOperation = () => { throw new Error("service down") }
  
  circuit = new CircuitBreaker(failingOperation, {
    failureThreshold: 3,
    resetTimeout: 1000
  })
  
  // First 3 calls fail but attempt operation
  for (i in 1..3) {
    assertThrows(() => circuit.execute())
  }
  
  // 4th call fails immediately without attempting
  assertThrows(CircuitOpenError, () => circuit.execute())
}
```
