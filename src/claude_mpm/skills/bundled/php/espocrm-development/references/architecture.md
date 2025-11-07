# EspoCRM Architecture Reference

## Metadata-Driven Architecture

EspoCRM's core architecture is built on metadata - JSON configuration files that define entities, fields, relationships, and behaviors.

### Metadata Structure

Metadata lives in several locations with a priority order:

```
1. custom/Espo/Custom/Resources/metadata/          (highest priority)
2. custom/Espo/Modules/{ModuleName}/Resources/metadata/
3. application/Espo/Modules/{ModuleName}/Resources/metadata/
4. application/Espo/Resources/metadata/            (lowest priority)
```

### Key Metadata Types

**Entity Definitions** (`entityDefs/{EntityType}.json`):
```json
{
    "fields": {
        "name": {
            "type": "varchar",
            "required": true,
            "maxLength": 255
        },
        "status": {
            "type": "enum",
            "options": ["New", "In Progress", "Complete"],
            "default": "New"
        }
    },
    "links": {
        "account": {
            "type": "belongsTo",
            "entity": "Account",
            "foreign": "contacts"
        }
    }
}
```

**Client Definitions** (`clientDefs/{EntityType}.json`):
```json
{
    "controller": "custom:controllers/my-entity",
    "views": {
        "detail": "custom:views/my-entity/detail"
    },
    "recordViews": {
        "detail": "custom:views/my-entity/record/detail"
    },
    "sidePanels": {
        "detail": [
            {
                "name": "activities",
                "label": "Activities",
                "view": "crm:views/record/panels/activities"
            }
        ]
    }
}
```

**Scopes** (`scopes/{EntityType}.json`):
```json
{
    "entity": true,
    "object": true,
    "layouts": true,
    "tab": true,
    "acl": true,
    "module": "MyModule",
    "stream": true
}
```

### Metadata Access in Code

```php
use Espo\Core\Utils\Metadata;

class MyService {
    public function __construct(private Metadata $metadata) {}

    public function getEntityFields(string $entityType): array {
        return $this->metadata->get(['entityDefs', $entityType, 'fields']) ?? [];
    }

    public function isFieldRequired(string $entityType, string $field): bool {
        return $this->metadata
            ->get(['entityDefs', $entityType, 'fields', $field, 'required']) ?? false;
    }
}
```

## ORM EntityManager

EntityManager is the central access point for ALL database operations in EspoCRM.

### Core EntityManager Methods

```php
use Espo\ORM\EntityManager;

class DataService {
    public function __construct(private EntityManager $entityManager) {}

    // Get entity by ID
    public function getById(string $entityType, string $id): ?Entity {
        return $this->entityManager->getEntityById($entityType, $id);
    }

    // Create new entity
    public function create(string $entityType): Entity {
        return $this->entityManager->getNewEntity($entityType);
    }

    // Save entity
    public function save(Entity $entity): void {
        $this->entityManager->saveEntity($entity);
    }

    // Delete entity
    public function delete(Entity $entity): void {
        $this->entityManager->removeEntity($entity);
    }

    // Get repository
    public function getRepository(string $entityType): RDBRepository {
        return $this->entityManager->getRDBRepository($entityType);
    }
}
```

### Repository Pattern

Never access repositories directly - always through EntityManager:

```php
// Query with conditions
$contacts = $this->entityManager
    ->getRDBRepository('Contact')
    ->where([
        'accountId' => $accountId,
        'deleted' => false
    ])
    ->find();

// Complex queries
$query = $this->entityManager
    ->getQueryBuilder()
    ->select()
    ->from('Opportunity')
    ->where([
        'stage' => ['Proposal', 'Negotiation'],
        'amount>=' => 10000
    ])
    ->order('createdAt', 'DESC')
    ->build();

$collection = $this->entityManager
    ->getRDBRepository('Opportunity')
    ->clone($query)
    ->find();
```

### Transaction Handling

```php
use Espo\ORM\TransactionManager;

class TransactionalService {
    public function __construct(
        private EntityManager $entityManager,
        private TransactionManager $transactionManager
    ) {}

    public function performComplexOperation(): void {
        $this->transactionManager->run(function () {
            // All operations within this closure are transactional
            $entity1 = $this->entityManager->getNewEntity('Account');
            $entity1->set('name', 'Test');
            $this->entityManager->saveEntity($entity1);

            $entity2 = $this->entityManager->getNewEntity('Contact');
            $entity2->set('accountId', $entity1->getId());
            $this->entityManager->saveEntity($entity2);

            // If any exception is thrown, all changes are rolled back
        });
    }
}
```

### STH Collections for Large Datasets

For operations on large datasets, use STH (Statement Handle) collections to avoid memory issues:

```php
$sthCollection = $this->entityManager
    ->getRDBRepository('Contact')
    ->sth()  // Returns STH collection instead of loading all into memory
    ->where(['accountId' => $accountId])
    ->find();

foreach ($sthCollection as $contact) {
    // Process one at a time
    $contact->set('status', 'Active');
    $this->entityManager->saveEntity($contact);
}
```

## Dependency Injection Container

EspoCRM uses a DI container for dependency management.

### Constructor Injection (CORRECT)

```php
namespace Espo\Modules\MyModule\Services;

use Espo\ORM\EntityManager;
use Espo\Core\Utils\Metadata;
use Espo\Core\Mail\EmailSender;

class MyService {
    public function __construct(
        private EntityManager $entityManager,
        private Metadata $metadata,
        private EmailSender $emailSender
    ) {}
}
```

### NEVER Pass Container

```php
// ❌ WRONG - Never do this
use Espo\Core\Container;

class BadService {
    public function __construct(private Container $container) {}
}

// ✅ CORRECT - Inject specific dependencies
class GoodService {
    public function __construct(
        private EntityManager $entityManager,
        private Metadata $metadata
    ) {}
}
```

### Injectable Services

Common services available for injection:

- `EntityManager` - ORM access
- `Metadata` - Metadata access
- `Config` - Application configuration
- `FileStorageManager` - File operations
- `InjectableFactory` - Create objects with DI
- `ServiceFactory` - Access record services
- `EmailSender` - Send emails
- `Acl` - Access control
- `User` - Current user
- `DateTime` - Date/time utilities
- `Language` - Translations
- `TransactionManager` - Database transactions

## Service Layer Architecture

Business logic belongs in Service classes, not hooks or controllers.

### Service Hierarchy

```
Record Service (base for all entity services)
    ↓
Custom Service (your entity-specific logic)
```

### Extending Record Service

```php
namespace Espo\Modules\MyModule\Services;

use Espo\Services\Record;
use Espo\ORM\Entity;

class Opportunity extends Record {
    // Override to add custom logic before create
    protected function beforeCreateEntity(Entity $entity, array $data): void {
        parent::beforeCreateEntity($entity, $data);

        // Custom logic
        if ($entity->get('amount') > 100000) {
            $entity->set('priority', 'High');
        }
    }

    // Custom action
    public function markAsWon(string $id): Entity {
        $entity = $this->getEntity($id);

        if (!$entity) {
            throw new NotFound();
        }

        $entity->set('stage', 'Closed Won');
        $this->entityManager->saveEntity($entity);

        // Trigger additional business logic
        $this->createWinNotification($entity);

        return $entity;
    }

    private function createWinNotification(Entity $opportunity): void {
        // Implementation
    }
}
```

### Service Access

```php
use Espo\Core\ServiceFactory;

class MyClass {
    public function __construct(private ServiceFactory $serviceFactory) {}

    public function useService(): void {
        $opportunityService = $this->serviceFactory->create('Opportunity');
        $opportunityService->markAsWon($id);
    }
}
```

## Hook System Architecture

Hooks are for lifecycle events - validation and side effects ONLY. Business logic belongs in Services.

### The 7 Hook Interfaces

```php
namespace Espo\Core\Hook\Hook;

interface BeforeSave {
    public function beforeSave(Entity $entity, array $options): void;
}

interface AfterSave {
    public function afterSave(Entity $entity, array $options): void;
}

interface BeforeRemove {
    public function beforeRemove(Entity $entity, array $options): void;
}

interface AfterRemove {
    public function afterRemove(Entity $entity, array $options): void;
}

interface AfterRelate {
    public function afterRelate(Entity $entity, string $relationName, Entity $foreign, ?array $columnData, array $options): void;
}

interface AfterUnrelate {
    public function afterUnrelate(Entity $entity, string $relationName, Entity $foreign, array $options): void;
}

interface AfterMassRelate {
    public function afterMassRelate(Entity $entity, string $relationName, array $params, array $options): void;
}
```

### Hook Implementation Example

```php
namespace Espo\Modules\MyModule\Hooks\Account;

use Espo\ORM\Entity;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\ServiceFactory;

class ValidateWebsite implements BeforeSave {
    public function __construct(private ServiceFactory $serviceFactory) {}

    public function beforeSave(Entity $entity, array $options): void {
        // Validation only
        if ($entity->isAttributeChanged('website')) {
            $website = $entity->get('website');
            if ($website && !filter_var($website, FILTER_VALIDATE_URL)) {
                throw new \Espo\Core\Exceptions\BadRequest('Invalid website URL');
            }
        }
    }
}
```

### Hook Registration

Hooks are auto-discovered in:
```
custom/Espo/Modules/{ModuleName}/Hooks/{EntityType}/{HookName}.php
```

## Coding Standards

### Type Declarations (Required)

```php
// ✅ CORRECT - All types declared
class MyService {
    public function processData(string $id, array $data): object {
        return $this->entityManager->getEntityById('Account', $id);
    }
}

// ❌ WRONG - Missing types
class BadService {
    public function processData($id, $data) {
        return $this->entityManager->getEntityById('Account', $id);
    }
}
```

### Exception Handling (Not Booleans)

```php
// ✅ CORRECT - Use exceptions
use Espo\Core\Exceptions\{NotFound, Forbidden, BadRequest};

public function getAccount(string $id): Entity {
    $account = $this->entityManager->getEntityById('Account', $id);

    if (!$account) {
        throw new NotFound();
    }

    if (!$this->acl->check($account, 'read')) {
        throw new Forbidden();
    }

    return $account;
}

// ❌ WRONG - Returning booleans for errors
public function getAccount(string $id): ?Entity {
    $account = $this->entityManager->getEntityById('Account', $id);
    if (!$account) {
        return null;  // Lost error context
    }
    return $account;
}
```

### Composition Over Inheritance

```php
// ✅ CORRECT - Composition with traits/utilities
class MyService extends Record {
    use ValidationTrait;

    public function __construct(
        private ValidationHelper $validationHelper,
        private NotificationHelper $notificationHelper
    ) {
        parent::__construct();
    }
}

// ❌ WRONG - Deep inheritance hierarchy
class MyService extends IntermediateService extends BaseService extends Record {
    // Too many levels
}
```

### DTOs Over Arrays

```php
// ✅ CORRECT - Use DTOs
class CreateAccountData {
    public function __construct(
        public readonly string $name,
        public readonly ?string $website,
        public readonly array $tags
    ) {}
}

public function createAccount(CreateAccountData $data): Entity {
    // Type-safe operations
}

// ❌ WRONG - Untyped arrays
public function createAccount(array $data): Entity {
    $name = $data['name'] ?? '';  // Fragile, no IDE support
}
```

### Maximum 2 Indentation Levels

```php
// ✅ CORRECT - Early returns, extracted methods
public function process(Entity $entity): void {
    if (!$this->validate($entity)) {
        return;
    }

    $this->performUpdate($entity);
}

private function performUpdate(Entity $entity): void {
    if ($entity->isNew()) {
        $this->handleNew($entity);
        return;
    }

    $this->handleExisting($entity);
}

// ❌ WRONG - Deep nesting
public function process(Entity $entity): void {
    if ($this->validate($entity)) {
        if ($entity->isNew()) {
            if ($this->hasPermission()) {
                // Three levels deep - hard to read
            }
        }
    }
}
```

## Formula Scripting

EspoCRM supports declarative logic through Formula scripts - use for simple field calculations instead of hooks.

### Formula in Metadata

```json
{
    "fields": {
        "totalPrice": {
            "type": "currency",
            "formula": "quantity * unitPrice"
        },
        "displayName": {
            "type": "varchar",
            "formula": "string\\concatenate(firstName, ' ', lastName)"
        }
    }
}
```

### When to Use Formula vs. Hooks

**Use Formula for:**
- Simple field calculations
- String concatenation
- Conditional field values
- Date calculations

**Use Hooks/Services for:**
- Complex business logic
- External API calls
- Multi-entity operations
- Validation requiring database queries

## Cache Management

### Rebuild Cache After Metadata Changes

```bash
# Always run after changing metadata
bin/command rebuild
```

### Clear Cache Programmatically

```php
use Espo\Core\Utils\DataCache;

class MyService {
    public function __construct(private DataCache $dataCache) {}

    public function clearCache(): void {
        $this->dataCache->clear();
    }
}
```

### Cache Keys

Common cache keys to be aware of:
- `metadata` - All metadata
- `entityDefs` - Entity definitions
- `clientDefs` - Client definitions
- `aclDefs` - ACL definitions
