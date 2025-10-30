---
skill_id: database-migration
skill_version: 0.1.0
description: Safe patterns for evolving database schemas in production.
updated_at: 2025-10-30T17:00:00Z
tags: [database, migration, schema, production]
---

# Database Migration

Safe patterns for evolving database schemas in production.

## Migration Principles

1. **Backward compatible** - New code works with old schema
2. **Reversible** - Can rollback if needed
3. **Tested** - Verify on staging before production
4. **Incremental** - Small changes, not big-bang
5. **Zero downtime** - No service interruption

## Safe Migration Pattern

### Phase 1: Add New (Compatible)
```sql
-- Add new column (nullable initially)
ALTER TABLE users ADD COLUMN full_name VARCHAR(255) NULL;

-- Deploy new code that writes to both old and new
UPDATE users SET full_name = CONCAT(first_name, ' ', last_name);
```

### Phase 2: Migrate Data
```sql
-- Backfill existing data
UPDATE users
SET full_name = CONCAT(first_name, ' ', last_name)
WHERE full_name IS NULL;
```

### Phase 3: Make Required
```sql
-- Make column required
ALTER TABLE users ALTER COLUMN full_name SET NOT NULL;
```

### Phase 4: Remove Old (After New Code Deployed)
```sql
-- Remove old columns
ALTER TABLE users DROP COLUMN first_name;
ALTER TABLE users DROP COLUMN last_name;
```

## Common Migrations

### Adding Index
```sql
-- Create index concurrently (PostgreSQL)
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

### Renaming Column
```sql
-- Phase 1: Add new column
ALTER TABLE users ADD COLUMN email_address VARCHAR(255);

-- Phase 2: Copy data
UPDATE users SET email_address = email;

-- Phase 3: Drop old column (after deploy)
ALTER TABLE users DROP COLUMN email;
```

### Changing Column Type
```sql
-- Phase 1: Add new column with new type
ALTER TABLE products ADD COLUMN price_cents INTEGER;

-- Phase 2: Migrate data
UPDATE products SET price_cents = CAST(price * 100 AS INTEGER);

-- Phase 3: Drop old column
ALTER TABLE products DROP COLUMN price;
ALTER TABLE products RENAME COLUMN price_cents TO price;
```

### Adding Foreign Key
```sql
-- Add column first
ALTER TABLE orders ADD COLUMN user_id INTEGER NULL;

-- Populate data
UPDATE orders SET user_id = (
    SELECT id FROM users WHERE users.email = orders.user_email
);

-- Add foreign key
ALTER TABLE orders
ADD CONSTRAINT fk_orders_users
FOREIGN KEY (user_id) REFERENCES users(id);
```

## Migration Tools

### Python (Alembic)
```python
# Generate migration
alembic revision --autogenerate -m "add user full_name"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### JavaScript (Knex)
```javascript
// Create migration
knex migrate:make add_full_name

// Apply migrations
knex migrate:latest

// Rollback
knex migrate:rollback
```

### Rails
```ruby
# Generate migration
rails generate migration AddFullNameToUsers full_name:string

# Run migrations
rails db:migrate

# Rollback
rails db:rollback
```

## Testing Migrations

```python
def test_migration_forward_backward():
    # Apply migration
    apply_migration("add_full_name")

    # Verify schema
    assert column_exists("users", "full_name")

    # Rollback
    rollback_migration()

    # Verify rollback
    assert not column_exists("users", "full_name")
```

## Dangerous Operations

### ❌ Avoid in Production
```sql
-- Locks table for long time
ALTER TABLE users ADD COLUMN email VARCHAR(255) NOT NULL;

-- Can't rollback
DROP TABLE old_users;

-- Breaks existing code immediately
ALTER TABLE users DROP COLUMN email;
```

### ✅ Safe Alternatives
```sql
-- Add as nullable first
ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL;

-- Rename instead of drop
ALTER TABLE old_users RENAME TO archived_users;

-- Keep old column until new code deployed
-- (multi-phase approach)
```

## Rollback Strategy

```sql
-- Every migration needs DOWN
-- UP
ALTER TABLE users ADD COLUMN full_name VARCHAR(255);

-- DOWN
ALTER TABLE users DROP COLUMN full_name;
```

## Remember
- Test migrations on copy of production data
- Have rollback plan ready
- Monitor during deployment
- Communicate with team about schema changes
- Keep migrations small and focused
