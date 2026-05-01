---
skill_id: api-documentation
skill_version: 0.1.0
description: Best practices for documenting APIs and code interfaces, eliminating redundant documentation guidance per agent.
updated_at: 2025-10-30T17:00:00Z
tags: [api, documentation, best-practices, interfaces]
effort: high
---

# API Documentation

Best practices for documenting APIs and code interfaces. Eliminates ~100-150 lines of redundant documentation guidance per agent.

## Core Documentation Principles

1. **Document the why, not just the what** - Explain intent and rationale
2. **Keep docs close to code** - Inline documentation stays synchronized
3. **Document contracts, not implementation** - Focus on behavior
4. **Examples are essential** - Show real usage
5. **Update docs with code** - Outdated docs are worse than no docs

## Function/Method Documentation

### Python (Docstrings)

```python
def calculate_discount(price: float, discount_percent: float) -> float:
    """
    Calculate discounted price with percentage off.

    Args:
        price: Original price in dollars (must be positive)
        discount_percent: Discount percentage (0-100)

    Returns:
        Final price after discount, rounded to 2 decimals

    Raises:
        ValueError: If price is negative or discount > 100

    Examples:
        >>> calculate_discount(100.0, 20.0)
        80.0
        >>> calculate_discount(50.0, 50.0)
        25.0

    Note:
        Discount percent is capped at 100% (minimum price of 0)
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
    if discount_percent > 100:
        raise ValueError("Discount cannot exceed 100%")

    discount_amount = price * (discount_percent / 100)
    return round(price - discount_amount, 2)
```

### JavaScript (JSDoc)

```javascript
/**
 * Calculate discounted price with percentage off
 *
 * @param {number} price - Original price in dollars (must be positive)
 * @param {number} discountPercent - Discount percentage (0-100)
 * @returns {number} Final price after discount, rounded to 2 decimals
 * @throws {Error} If price is negative or discount > 100
 *
 * @example
 * calculateDiscount(100.0, 20.0)
 * // returns 80.0
 *
 * @example
 * calculateDiscount(50.0, 50.0)
 * // returns 25.0
 */
function calculateDiscount(price, discountPercent) {
  if (price < 0) {
    throw new Error('Price cannot be negative');
  }
  if (discountPercent > 100) {
    throw new Error('Discount cannot exceed 100%');
  }

  const discountAmount = price * (discountPercent / 100);
  return Math.round((price - discountAmount) * 100) / 100;
}
```

### Go (Godoc)

```go
// CalculateDiscount calculates discounted price with percentage off.
//
// The function applies the given discount percentage to the original price
// and returns the final price rounded to 2 decimal places.
//
// Parameters:
//   - price: Original price in dollars (must be positive)
//   - discountPercent: Discount percentage (0-100)
//
// Returns the final price after discount.
//
// Returns an error if price is negative or discount exceeds 100%.
//
// Example:
//
//	finalPrice, err := CalculateDiscount(100.0, 20.0)
//	// finalPrice = 80.0
func CalculateDiscount(price, discountPercent float64) (float64, error) {
    if price < 0 {
        return 0, errors.New("price cannot be negative")
    }
    if discountPercent > 100 {
        return 0, errors.New("discount cannot exceed 100%")
    }

    discountAmount := price * (discountPercent / 100)
    return math.Round((price-discountAmount)*100) / 100, nil
}
```

## API Endpoint Documentation

### REST API (OpenAPI/Swagger)

```yaml
openapi: 3.0.0
info:
  title: User Management API
  version: 1.0.0

paths:
  /users/{userId}:
    get:
      summary: Get user by ID
      description: Retrieves detailed information for a specific user
      parameters:
        - name: userId
          in: path
          required: true
          schema:
            type: integer
            minimum: 1
          description: Unique user identifier
      responses:
        '200':
          description: User found successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
              example:
                id: 123
                name: "John Doe"
                email: "john@example.com"
        '404':
          description: User not found
        '401':
          description: Unauthorized - authentication required
```

### GraphQL

```graphql
"""
Represents a user in the system
"""
type User {
  """Unique identifier for the user"""
  id: ID!

  """User's full name"""
  name: String!

  """User's email address (validated)"""
  email: String!

  """User's posts (paginated)"""
  posts(limit: Int = 10, offset: Int = 0): [Post!]!
}

"""
Query a specific user by ID
"""
type Query {
  """
  Get user by unique identifier

  Returns null if user not found
  """
  user(id: ID!): User
}
```

## Class/Module Documentation

```python
class UserManager:
    """
    Manages user accounts and authentication.

    This class provides a high-level interface for user management
    operations including creation, authentication, and profile updates.

    Attributes:
        db: Database connection instance
        cache: Redis cache for session management

    Example:
        >>> manager = UserManager(db=get_db(), cache=get_cache())
        >>> user = manager.create_user("john@example.com", "password")
        >>> authenticated = manager.authenticate("john@example.com", "password")
        >>> authenticated is not None
        True

    Thread Safety:
        This class is thread-safe. Multiple threads can safely call
        methods concurrently.

    Note:
        All passwords are automatically hashed using bcrypt before
        storage. Never pass pre-hashed passwords to methods.
    """

    def __init__(self, db: Database, cache: Cache):
        """
        Initialize UserManager with database and cache.

        Args:
            db: Database connection for persistent storage
            cache: Redis cache for session management

        Raises:
            ConnectionError: If unable to connect to database or cache
        """
        self.db = db
        self.cache = cache
```

## Ontology Tagging

Tagging code with well-known ontologies in inline documentation makes intent explicit, machine-readable, and interoperable across teams and tools. Beyond explaining WHY, ontology tags link code to shared vocabularies so semantic relationships (is-a, part-of, domain) become discoverable.

### Why Ontology Tagging Matters

- **Discoverability**: Search across services by concept, not just keyword
- **Interoperability**: Shared meaning across teams, services, and tools
- **Disambiguation**: A `User` in billing vs. auth vs. analytics is no longer ambiguous
- **Documentation generation**: Tools can extract structured metadata for API catalogs
- **i18n / knowledge graphs**: Tagged code feeds directly into semantic indexes

### Well-Known Ontologies

Use the most specific applicable ontology:

- **`schema:`** — [schema.org](https://schema.org/) types and properties (e.g., `schema:Person`, `schema:PayAction`, `schema:PostalAddress`)
- **`dc:` / `dcterms:`** — [Dublin Core](https://www.dublincore.org/) metadata (`dc:subject`, `dc:description`, `dc:creator`, `dcterms:created`)
- **`skos:`** — [SKOS](https://www.w3.org/2004/02/skos/) concept classification (`skos:Concept`, `skos:broader`, `skos:narrower`, `skos:related`)
- **`rdfs:` / `owl:`** — Class hierarchies and equivalences (`rdfs:subClassOf`, `owl:equivalentClass`)
- **`codemeta:`** — [CodeMeta](https://codemeta.github.io/) for software metadata (`codemeta:softwareRequirements`)
- **Domain-specific** — Use the most specific applicable vocabulary for the domain (financial, medical, legal, scientific)

### When to Tag

- Public classes, functions, and API endpoints
- Domain objects and value types
- Any code with cross-team or cross-service significance
- Persisted entities and external API contracts

### Format Guidance

Keep tags concise. One `@type`, one `dc:subject` line, and `skos:broader` are sufficient for most cases.

### Python Example

```python
def calculate_discount(price: float, rate: float) -> float:
    """
    Apply a percentage discount to a price.

    WHY: Business rule requires consistent discount application across
    checkout and invoice services; centralized to avoid drift.

    Ontology:
        @type: schema:PriceSpecification
        @concept: skos:Concept <FinancialCalculation>
        dc:subject: "pricing", "discount", "commerce"

    Args:
        price: Base price before discount. schema:price
        rate: Discount rate as decimal (0.0–1.0). schema:discount
    Returns:
        Discounted price. schema:price
    """
```

### TypeScript / JSDoc Example

```typescript
/**
 * Resolve a user's billing address.
 *
 * WHY: Shipping and billing may differ; always prefer billing for invoices.
 *
 * @ontology schema:PostalAddress
 * @concept skos:Concept BillingAddress
 * @dc:subject billing, address, user
 */
function resolveBillingAddress(userId: string): PostalAddress { ... }
```

### Go / Godoc Example

```go
// ProcessPayment validates and records a payment transaction.
//
// WHY: Centralizes payment validation to enforce audit trail across
// all checkout flows.
//
// Ontology:
//   @type: schema:PayAction
//   dc:subject: "payment", "transaction", "finance"
//   skos:broader: <FinancialTransaction>
func ProcessPayment(amount float64, currency string) (*Receipt, error) { ... }
```

### Tagging Checklist

```
□ Public APIs include an Ontology block in their docstring
□ @type uses the most specific schema.org (or domain) class
□ dc:subject lists 2-4 concise topic keywords
□ skos:broader links to a parent concept where applicable
□ Domain-specific ontologies preferred over generic where available
□ Tags kept concise — no more than ~3 lines for typical functions
```

## README Documentation Structure

```markdown
# Project Name

Brief description of what the project does (1-2 sentences).

## Features

- Key feature 1
- Key feature 2
- Key feature 3

## Installation

```bash
pip install project-name
```

## Quick Start

```python
from project import MainClass

# Simple usage example
client = MainClass(api_key="your-key")
result = client.do_something()
print(result)
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `api_key` | str | None | API authentication key |
| `timeout` | int | 30 | Request timeout in seconds |

## API Reference

See full [API Documentation](docs/api.md)

### Main Methods

#### `do_something(param1, param2)`

Description of what this does.

**Parameters:**
- `param1` (str): Description of param1
- `param2` (int): Description of param2

**Returns:** Description of return value

**Example:**
```python
result = client.do_something("value", 42)
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License - see [LICENSE](LICENSE)
```

## Documentation Anti-Patterns

### ❌ Redundant Comments

```python
# Bad: Obvious comment adds no value
i = i + 1  # Increment i

# Good: Comment explains WHY
i = i + 1  # Skip header row
```

### ❌ Outdated Documentation

```python
# Bad: Comment doesn't match code
def get_users(limit=10):  # Comment says: Returns all users
    """Returns all users in the system."""  # But limit is 10!
    return User.query.limit(limit).all()

# Good: Keep docs synchronized
def get_users(limit=10):
    """
    Returns up to 'limit' users from the system.

    Args:
        limit: Maximum number of users to return (default: 10)
    """
    return User.query.limit(limit).all()
```

### ❌ Implementation Documentation

```python
# Bad: Documents HOW (implementation)
def sort_users(users):
    """Uses bubble sort algorithm to sort users."""  # Don't care!
    ...

# Good: Documents WHAT (contract)
def sort_users(users):
    """Returns users sorted alphabetically by name."""
    ...
```

## Documentation Tools

### Python
- **Sphinx**: Generate HTML docs from docstrings
- **pdoc**: Simpler alternative to Sphinx
- **MkDocs**: Markdown-based documentation

### JavaScript
- **JSDoc**: Generate HTML from JSDoc comments
- **TypeDoc**: For TypeScript projects
- **Docusaurus**: Full documentation websites

### Go
- **godoc**: Built-in documentation tool
- **pkgsite**: Go package documentation

### Rust
- **rustdoc**: Built-in documentation with `cargo doc`

## Quick Documentation Checklist

```
□ Public APIs have docstrings/comments
□ Parameters and return values documented
□ Exceptions/errors documented
□ Usage examples provided
□ Edge cases and limitations noted
□ README includes quick start
□ API reference available
□ Configuration options documented
□ Docs are up to date with code
□ Breaking changes documented
```

## Remember

- **Code is read more than written** - Good docs save time
- **Examples speak louder than descriptions** - Show, don't just tell
- **The best docs are no docs** - Write self-documenting code
- **Keep it DRY** - Don't repeat what the code already says
- **Update docs with code** - Outdated docs mislead developers
