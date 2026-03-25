# Real-World TDD Examples

> **Part of**: [Test-Driven Development](../SKILL.md)
> **Category**: testing
> **Reading Level**: Intermediate

## Purpose

Real-world scenarios demonstrating test-driven development in action, with complete RED/GREEN/REFACTOR cycles and step-by-step walkthroughs.

## Example 1: Form Validation

### Scenario
Build email validation for user registration form.

### Iteration 1: Basic Email Validation

**RED - Write Failing Test:**
```typescript
describe('Email Validation', () => {
  test('accepts valid email format', () => {
    const result = validateEmail('user@example.com');
    expect(result.valid).toBe(true);
  });
});
```

**VERIFY RED - Run Test:**
```bash
$ npm test
FAIL: accepts valid email format
ReferenceError: validateEmail is not defined
```
✓ Fails correctly - function doesn't exist

**GREEN - Minimal Implementation:**
```typescript
interface ValidationResult {
  valid: boolean;
  error?: string;
}

function validateEmail(email: string): ValidationResult {
  return { valid: true };  // Simplest thing that passes
}
```

**VERIFY GREEN - Run Test:**
```bash
$ npm test
PASS: accepts valid email format
```
✓ Test passes

### Iteration 2: Reject Invalid Format

**RED:**
```typescript
test('rejects email without @ symbol', () => {
  const result = validateEmail('userexample.com');
  expect(result.valid).toBe(false);
  expect(result.error).toBe('Invalid email format');
});
```

**VERIFY RED:**
```bash
$ npm test
FAIL: rejects email without @ symbol
Expected valid: false, Received: true
```
✓ Fails correctly

**GREEN:**
```typescript
function validateEmail(email: string): ValidationResult {
  if (!email.includes('@')) {
    return { valid: false, error: 'Invalid email format' };
  }
  return { valid: true };
}
```

**VERIFY GREEN:**
```bash
$ npm test
PASS: accepts valid email format
PASS: rejects email without @ symbol
```
✓ Both tests pass

### Iteration 3: Reject Multiple @ Symbols

**RED:**
```typescript
test('rejects email with multiple @ symbols', () => {
  const result = validateEmail('user@@example.com');
  expect(result.valid).toBe(false);
});
```

**GREEN:**
```typescript
function validateEmail(email: string): ValidationResult {
  if (!email.includes('@')) {
    return { valid: false, error: 'Invalid email format' };
  }
  if (email.indexOf('@') !== email.lastIndexOf('@')) {
    return { valid: false, error: 'Invalid email format' };
  }
  return { valid: true };
}
```

**REFACTOR - Clean Up:**
```typescript
function validateEmail(email: string): ValidationResult {
  const hasAtSymbol = email.includes('@');
  const hasSingleAtSymbol = email.indexOf('@') === email.lastIndexOf('@');

  if (!hasAtSymbol || !hasSingleAtSymbol) {
    return { valid: false, error: 'Invalid email format' };
  }

  return { valid: true };
}
```

**Time:** 15 minutes, 3 tests, working validation

## Example 2: Bug Fix with TDD

### Scenario
Bug reported: Empty shopping cart shows "$0" instead of "Cart is empty" message.

### Step 1: Reproduce with Test

**RED - Failing Test:**
```typescript
describe('Shopping Cart Display', () => {
  test('shows empty message when cart has no items', () => {
    const cart = new ShoppingCart();
    const display = cart.getDisplayMessage();
    expect(display).toBe('Cart is empty');
  });
});
```

**VERIFY RED:**
```bash
$ npm test
FAIL: shows empty message when cart has no items
Expected: 'Cart is empty'
Received: 'Total: $0'
```
✓ Test reproduces the bug

### Step 2: Fix with Minimal Change

**GREEN:**
```typescript
class ShoppingCart {
  private items: Item[] = [];

  getDisplayMessage(): string {
    if (this.items.length === 0) {
      return 'Cart is empty';
    }
    return `Total: $${this.getTotal()}`;
  }

  getTotal(): number {
    return this.items.reduce((sum, item) => sum + item.price, 0);
  }
}
```

**VERIFY GREEN:**
```bash
$ npm test
PASS: shows empty message when cart has no items
PASS: calculates total correctly (existing test)
```
✓ Bug fixed, no regressions

### Step 3: Prevent Regression

Test stays in suite permanently - bug can never return without test failing.

**Time:** 10 minutes, bug fixed with regression protection

## Example 3: API Client Development

### Scenario
Build HTTP client with retry logic for failed requests.

### Iteration 1: Basic Request

**RED:**
```typescript
describe('HTTP Client', () => {
  test('makes GET request successfully', async () => {
    const client = new HttpClient('https://api.example.com');
    const response = await client.get('/users/1');
    expect(response.status).toBe(200);
    expect(response.data).toBeDefined();
  });
});
```

**GREEN:**
```typescript
class HttpClient {
  constructor(private baseUrl: string) {}

  async get(path: string): Promise<Response> {
    const res = await fetch(`${this.baseUrl}${path}`);
    return {
      status: res.status,
      data: await res.json()
    };
  }
}
```

### Iteration 2: Handle Network Errors

**RED:**
```typescript
test('retries on network error', async () => {
  const client = new HttpClient('https://api.example.com');

  // Mock fetch to fail once then succeed
  let attempts = 0;
  global.fetch = jest.fn().mockImplementation(() => {
    attempts++;
    if (attempts === 1) {
      throw new Error('Network error');
    }
    return Promise.resolve({
      status: 200,
      json: () => Promise.resolve({ id: 1 })
    });
  });

  const response = await client.get('/users/1');

  expect(response.status).toBe(200);
  expect(attempts).toBe(2);
});
```

**GREEN:**
```typescript
class HttpClient {
  constructor(private baseUrl: string) {}

  async get(path: string): Promise<Response> {
    try {
      return await this.makeRequest(path);
    } catch (error) {
      // Retry once
      return await this.makeRequest(path);
    }
  }

  private async makeRequest(path: string): Promise<Response> {
    const res = await fetch(`${this.baseUrl}${path}`);
    return {
      status: res.status,
      data: await res.json()
    };
  }
}
```

### Iteration 3: Configurable Retries

**RED:**
```typescript
test('retries up to max attempts', async () => {
  const client = new HttpClient('https://api.example.com', {
    maxRetries: 3
  });

  let attempts = 0;
  global.fetch = jest.fn().mockImplementation(() => {
    attempts++;
    if (attempts < 3) {
      throw new Error('Network error');
    }
    return Promise.resolve({
      status: 200,
      json: () => Promise.resolve({ id: 1 })
    });
  });

  const response = await client.get('/users/1');

  expect(response.status).toBe(200);
  expect(attempts).toBe(3);
});
```

**GREEN:**
```typescript
interface HttpClientOptions {
  maxRetries?: number;
}

class HttpClient {
  private maxRetries: number;

  constructor(
    private baseUrl: string,
    options: HttpClientOptions = {}
  ) {
    this.maxRetries = options.maxRetries ?? 1;
  }

  async get(path: string): Promise<Response> {
    let lastError: Error;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        return await this.makeRequest(path);
      } catch (error) {
        lastError = error as Error;
      }
    }

    throw lastError!;
  }

  private async makeRequest(path: string): Promise<Response> {
    const res = await fetch(`${this.baseUrl}${path}`);
    return {
      status: res.status,
      data: await res.json()
    };
  }
}
```

**REFACTOR:**
```typescript
// Extract retry logic to utility
async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries: number
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
    }
  }

  throw lastError!;
}

class HttpClient {
  constructor(
    private baseUrl: string,
    private options: HttpClientOptions = {}
  ) {}

  async get(path: string): Promise<Response> {
    return withRetry(
      () => this.makeRequest(path),
      this.options.maxRetries ?? 1
    );
  }

  private async makeRequest(path: string): Promise<Response> {
    const res = await fetch(`${this.baseUrl}${path}`);
    return {
      status: res.status,
      data: await res.json()
    };
  }
}
```

**Time:** 30 minutes, robust HTTP client with retry logic

## Example 4: Refactoring with Test Protection

### Scenario
Legacy code needs refactoring - extract business logic from controller.

### Step 1: Write Tests for Current Behavior

**RED (characterization tests):**
```typescript
describe('User Registration', () => {
  test('registers new user with valid data', async () => {
    const controller = new UserController();
    const result = await controller.register({
      email: 'user@example.com',
      password: 'SecurePass123',
      name: 'Test User'
    });

    expect(result.success).toBe(true);
    expect(result.userId).toBeDefined();
  });

  test('rejects duplicate email', async () => {
    const controller = new UserController();
    await controller.register({
      email: 'existing@example.com',
      password: 'Pass123',
      name: 'First User'
    });

    const result = await controller.register({
      email: 'existing@example.com',
      password: 'Pass456',
      name: 'Second User'
    });

    expect(result.success).toBe(false);
    expect(result.error).toBe('Email already exists');
  });
});
```

**GREEN - Tests pass on legacy code:**
```bash
$ npm test
PASS: registers new user with valid data
PASS: rejects duplicate email
```

### Step 2: Refactor with Test Protection

**Before (everything in controller):**
```typescript
class UserController {
  async register(data: UserData) {
    // Validation
    if (!data.email.includes('@')) {
      return { success: false, error: 'Invalid email' };
    }
    if (data.password.length < 8) {
      return { success: false, error: 'Password too short' };
    }

    // Check duplicate
    const existing = await db.users.findByEmail(data.email);
    if (existing) {
      return { success: false, error: 'Email already exists' };
    }

    // Create user
    const user = await db.users.create({
      email: data.email,
      password: hashPassword(data.password),
      name: data.name
    });

    return { success: true, userId: user.id };
  }
}
```

**After (extracted service):**
```typescript
// Extract service
class UserService {
  async registerUser(data: UserData): Promise<User> {
    this.validateUserData(data);
    await this.checkDuplicateEmail(data.email);
    return this.createUser(data);
  }

  private validateUserData(data: UserData): void {
    if (!data.email.includes('@')) {
      throw new Error('Invalid email');
    }
    if (data.password.length < 8) {
      throw new Error('Password too short');
    }
  }

  private async checkDuplicateEmail(email: string): Promise<void> {
    const existing = await db.users.findByEmail(email);
    if (existing) {
      throw new Error('Email already exists');
    }
  }

  private async createUser(data: UserData): Promise<User> {
    return db.users.create({
      email: data.email,
      password: hashPassword(data.password),
      name: data.name
    });
  }
}

// Simplified controller
class UserController {
  private userService = new UserService();

  async register(data: UserData) {
    try {
      const user = await this.userService.registerUser(data);
      return { success: true, userId: user.id };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
}
```

**Verify refactoring:**
```bash
$ npm test
PASS: registers new user with valid data
PASS: rejects duplicate email
```
✓ Behavior unchanged, structure improved

### Step 3: Add Tests for New Service

**Now test service directly:**
```typescript
describe('UserService', () => {
  test('validates email format', async () => {
    const service = new UserService();
    await expect(
      service.registerUser({
        email: 'invalid',
        password: 'Pass123456',
        name: 'Test'
      })
    ).rejects.toThrow('Invalid email');
  });

  test('validates password length', async () => {
    const service = new UserService();
    await expect(
      service.registerUser({
        email: 'test@example.com',
        password: 'short',
        name: 'Test'
      })
    ).rejects.toThrow('Password too short');
  });
});
```

**Time:** 45 minutes, safe refactoring with test protection

## Example 5: Building a Feature from Scratch

### Scenario
Implement shopping cart with add/remove/total functionality.

### Complete TDD Session

**Iteration 1 - Add Item:**
```typescript
// RED
test('adds item to cart', () => {
  const cart = new ShoppingCart();
  cart.addItem({ id: 1, name: 'Book', price: 10 });
  expect(cart.getItemCount()).toBe(1);
});

// GREEN
class ShoppingCart {
  private items: Item[] = [];

  addItem(item: Item) {
    this.items.push(item);
  }

  getItemCount(): number {
    return this.items.length;
  }
}
```

**Iteration 2 - Calculate Total:**
```typescript
// RED
test('calculates total price', () => {
  const cart = new ShoppingCart();
  cart.addItem({ id: 1, name: 'Book', price: 10 });
  cart.addItem({ id: 2, name: 'Pen', price: 5 });
  expect(cart.getTotal()).toBe(15);
});

// GREEN
class ShoppingCart {
  private items: Item[] = [];

  addItem(item: Item) {
    this.items.push(item);
  }

  getItemCount(): number {
    return this.items.length;
  }

  getTotal(): number {
    return this.items.reduce((sum, item) => sum + item.price, 0);
  }
}
```

**Iteration 3 - Remove Item:**
```typescript
// RED
test('removes item from cart', () => {
  const cart = new ShoppingCart();
  cart.addItem({ id: 1, name: 'Book', price: 10 });
  cart.addItem({ id: 2, name: 'Pen', price: 5 });
  cart.removeItem(1);
  expect(cart.getItemCount()).toBe(1);
  expect(cart.getTotal()).toBe(5);
});

// GREEN
class ShoppingCart {
  private items: Item[] = [];

  addItem(item: Item) {
    this.items.push(item);
  }

  removeItem(itemId: number) {
    this.items = this.items.filter(item => item.id !== itemId);
  }

  getItemCount(): number {
    return this.items.length;
  }

  getTotal(): number {
    return this.items.reduce((sum, item) => sum + item.price, 0);
  }
}
```

**Iteration 4 - Handle Empty Cart:**
```typescript
// RED
test('returns zero for empty cart', () => {
  const cart = new ShoppingCart();
  expect(cart.getTotal()).toBe(0);
});

// GREEN - Already passes!
```

**Iteration 5 - Quantity Support:**
```typescript
// RED
test('handles item quantity', () => {
  const cart = new ShoppingCart();
  cart.addItem({ id: 1, name: 'Book', price: 10 }, 3);
  expect(cart.getTotal()).toBe(30);
});

// GREEN
interface CartItem extends Item {
  quantity: number;
}

class ShoppingCart {
  private items: CartItem[] = [];

  addItem(item: Item, quantity: number = 1) {
    this.items.push({ ...item, quantity });
  }

  removeItem(itemId: number) {
    this.items = this.items.filter(item => item.id !== itemId);
  }

  getItemCount(): number {
    return this.items.reduce((sum, item) => sum + item.quantity, 0);
  }

  getTotal(): number {
    return this.items.reduce(
      (sum, item) => sum + (item.price * item.quantity),
      0
    );
  }
}
```

**Time:** 25 minutes, complete shopping cart with 5 tests

## Key Patterns Demonstrated

### Incremental Development
- Each test adds one small behavior
- Build complexity gradually
- Each step verified before next

### Test Protection
- Refactoring safe with tests
- Regressions caught immediately
- Behavior preserved across changes

### Test-First Benefits
- Clear requirements from tests
- No over-engineering
- 100% relevant test coverage

### Time Investment
- Small features: 10-25 minutes
- Medium features: 25-45 minutes
- Includes tests, implementation, refactoring
- Compare to: 15 min coding + 60-120 min debugging

## Summary

TDD in practice:
- Start with failing test
- Implement minimally
- Refactor safely
- Build incrementally
- Fast feedback loop
- High confidence

## Related References

- [Workflow](workflow.md): Complete RED/GREEN/REFACTOR process
- [Philosophy](philosophy.md): Why TDD works
- [Anti-patterns](anti-patterns.md): Common mistakes
- [Integration](integration.md): TDD with other skills
