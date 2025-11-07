---
name: espocrm-development
description: Comprehensive guide for developing on EspoCRM - metadata-driven CRM with service layer architecture
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Metadata-driven CRM development using service layer, ORM EntityManager, and hook-based business logic"
    when_to_use: "When developing custom modules, entities, hooks, or integrations for EspoCRM"
    quick_start: "1. Understand metadata-driven architecture 2. Use EntityManager for data access 3. Implement business logic in Services 4. Register hooks for lifecycle events 5. Rebuild cache after changes"
  references:
    - architecture.md
    - development-workflow.md
    - hooks-and-services.md
    - frontend-customization.md
    - common-tasks.md
    - testing-debugging.md
context_limit: 800
tags:
  - espocrm
  - php
  - crm
  - metadata-driven
  - orm
requires_tools: []
---

# EspoCRM Development

## Overview

EspoCRM is a metadata-driven CRM platform where configuration lives in JSON files, business logic belongs in Services, and data access happens through ORM EntityManager. This skill enforces architectural patterns to prevent common mistakes like passing Container dependencies, bypassing the service layer, or implementing business logic in hooks.

## When to Use This Skill

Activate when developing custom EspoCRM modules, entities, relationships, hooks, services, API endpoints, or integrations. **Use especially when:** working with ORM (EntityManager required), implementing business logic (belongs in Services), creating hooks (use interfaces), modifying metadata (requires cache rebuild), or building custom field types.

## The Iron Law

**BUSINESS LOGIC IN SERVICES, NOT HOOKS | DATA ACCESS VIA ENTITYMANAGER, NEVER DIRECT PDO | NEVER PASS CONTAINER AS DEPENDENCY**

If you're accessing Container directly or writing business logic in hooks, you're violating architecture.

## Core Architecture Principles

1. **Metadata-Driven**: Entity definitions, layouts, field configs live in JSON
2. **Service Layer**: All business logic implemented in Service classes
3. **ORM EntityManager**: Central access point for all database operations
4. **Dependency Injection**: Constructor injection, never pass Container
5. **Hook System**: Lifecycle events for validation and side effects (not business logic)
6. **Repository Pattern**: Entities accessed through repositories

## Quick Start

1. **Setup Development Environment** - Use ext-template, work in `src/` directory (EspoCRM 7.4+), understand metadata structure: `custom/Espo/Modules/{ModuleName}/Resources/metadata/`

2. **Access Data with EntityManager**
   ```php
   use Espo\ORM\EntityManager;

   public function __construct(private EntityManager $entityManager) {}

   // Find entity
   $account = $this->entityManager->getEntityById('Account', $id);

   // Query with conditions
   $collection = $this->entityManager
       ->getRDBRepository('Contact')
       ->where(['accountId' => $accountId])
       ->find();
   ```

3. **Implement Business Logic in Services**
   ```php
   namespace Espo\Modules\MyModule\Services;

   use Espo\Services\Record;

   class MyEntity extends Record {
       public function customAction(string $id, object $data): object {
           // Business logic here
           $entity = $this->entityManager->getEntityById($this->entityType, $id);
           // ... process ...
           $this->entityManager->saveEntity($entity);
           return $entity;
       }
   }
   ```

4. **Register Hooks for Lifecycle Events**
   ```php
   namespace Espo\Modules\MyModule\Hooks\Account;

   use Espo\ORM\Entity;
   use Espo\Core\Hook\Hook\BeforeSave;

   class MyHook implements BeforeSave {
       public function beforeSave(Entity $entity, array $options): void {
           // Validation or side effects only
           if ($entity->isAttributeChanged('status')) {
               // React to changes
           }
       }
   }
   ```

5. **Rebuild Cache After Changes**
   ```bash
   bin/command rebuild
   ```

## Hook Types (Interfaces)

EspoCRM provides 7 hook types - ALWAYS use interfaces: `BeforeSave` (validation before save), `AfterSave` (side effects after save), `BeforeRemove` (validation before delete), `AfterRemove` (cleanup after delete), `AfterRelate` (relationship creation), `AfterUnrelate` (relationship removal), `AfterMassRelate` (bulk relationship operations).

## Navigation

For detailed information:
- **[Architecture](references/architecture.md)**: Metadata system, ORM, DI container, repository pattern, and core architectural patterns
- **[Development Workflow](references/development-workflow.md)**: Module creation, custom entities, fields, APIs, and extension development process
- **[Hooks and Services](references/hooks-and-services.md)**: Service layer implementation, hook types, dependency injection, and business logic patterns
- **[Frontend Customization](references/frontend-customization.md)**: View system, client-side development, and UI customization
- **[Common Tasks](references/common-tasks.md)**: Scheduled jobs, emails, PDFs, ACL, workflows, and integration patterns
- **[Testing and Debugging](references/testing-debugging.md)**: Unit tests, debugging techniques, performance optimization, and common pitfalls

## Key Patterns

**Correct Pattern:**
```php
✅ Service with injected dependencies
✅ EntityManager for data access
✅ Hooks using interfaces
✅ Type declarations on all methods
✅ Exceptions for error handling
```

**Incorrect Patterns:**
```php
❌ Passing Container as dependency
❌ Direct PDO database access
❌ Business logic in hooks
❌ Hook base classes instead of interfaces
❌ Missing type declarations
```

## Common Mistakes to Avoid

- **Never pass Container** - Inject specific dependencies instead
- **Don't bypass EntityManager** - Use ORM, not raw queries
- **Business logic doesn't belong in hooks** - Use Services
- **Always rebuild cache** - After metadata changes (`bin/command rebuild`)
- **Use interfaces for hooks** - Not base classes
- **Type everything** - PHP 7.4+ requires type declarations
- **Throw exceptions** - Don't return booleans for errors

## Integration with Other Skills

- **systematic-debugging**: Debug EspoCRM issues using logs and step debugging
- **verification-before-completion**: Always test with cache rebuild before claiming complete
- **test-driven-development**: Write unit tests for Services and hooks

## The Bottom Line

**EspoCRM is metadata-driven with a service layer architecture.**

Understand the metadata system. Use EntityManager for data. Implement business logic in Services. Use hooks for lifecycle events only. Rebuild cache after changes.

This is the EspoCRM way.
