# Hooks and Services Reference

## Service Layer Pattern

The service layer is where ALL business logic belongs in EspoCRM. Never put business logic in hooks, controllers, or repositories.

### Service Layer Hierarchy

```
Base Record Service (Espo\Services\Record)
    ↓
Your Custom Service (extends Record)
    ↓
Business Logic Methods
```

### Creating a Service

```php
<?php
namespace Espo\Modules\MyModule\Services;

use Espo\Services\Record;
use Espo\ORM\Entity;
use Espo\Core\Exceptions\{BadRequest, Forbidden, NotFound};
use Espo\Core\Mail\EmailSender;
use Espo\Core\Utils\DateTime as DateTimeUtil;

class Opportunity extends Record
{
    public function __construct(
        private EmailSender $emailSender,
        private DateTimeUtil $dateTime
    ) {
        parent::__construct();
    }

    // Override create flow
    protected function beforeCreateEntity(Entity $entity, array $data): void
    {
        parent::beforeCreateEntity($entity, $data);

        // Business logic: Set expected close date to 30 days from now if not provided
        if (!$entity->get('closeDate')) {
            $closeDate = $this->dateTime->getDateTime()
                ->modify('+30 days')
                ->format('Y-m-d');
            $entity->set('closeDate', $closeDate);
        }

        // Business logic: Auto-assign to manager for large opportunities
        if ($entity->get('amount') > 100000 && !$entity->get('assignedUserId')) {
            $managerId = $this->getManagerForLargeDeals();
            $entity->set('assignedUserId', $managerId);
        }
    }

    // Override update flow
    protected function beforeUpdateEntity(Entity $entity, array $data): void
    {
        parent::beforeUpdateEntity($entity, $data);

        // Business logic: Track stage changes
        if ($entity->isAttributeChanged('stage')) {
            $this->trackStageChange($entity);
        }
    }

    // Custom business logic method
    public function markAsWon(string $id): Entity
    {
        $entity = $this->getEntity($id);

        if (!$entity) {
            throw new NotFound();
        }

        if (!$this->acl->check($entity, 'edit')) {
            throw new Forbidden();
        }

        // Validate can be marked as won
        if (!$this->canMarkAsWon($entity)) {
            throw new BadRequest('Opportunity cannot be marked as won in current state');
        }

        // Update entity
        $entity->set([
            'stage' => 'Closed Won',
            'probability' => 100,
            'closeDate' => date('Y-m-d')
        ]);

        $this->entityManager->saveEntity($entity);

        // Additional business logic
        $this->createWinNotification($entity);
        $this->updateAccountRevenue($entity);

        return $entity;
    }

    private function canMarkAsWon(Entity $opportunity): bool
    {
        // Business rules for winning
        $stage = $opportunity->get('stage');
        $allowedStages = ['Proposal', 'Negotiation'];

        return in_array($stage, $allowedStages);
    }

    private function createWinNotification(Entity $opportunity): void
    {
        $assignedUserId = $opportunity->get('assignedUserId');

        if (!$assignedUserId) {
            return;
        }

        // Send email notification
        $emailSender = $this->emailSender->create();

        $emailSender
            ->withSubject('Opportunity Won: ' . $opportunity->get('name'))
            ->withBody('Congratulations! Opportunity has been marked as won.')
            ->withToUserIdList([$assignedUserId])
            ->send();
    }

    private function updateAccountRevenue(Entity $opportunity): void
    {
        $accountId = $opportunity->get('accountId');

        if (!$accountId) {
            return;
        }

        $account = $this->entityManager->getEntityById('Account', $accountId);

        if (!$account) {
            return;
        }

        // Calculate total won opportunities
        $totalRevenue = $this->entityManager
            ->getRDBRepository('Opportunity')
            ->where([
                'accountId' => $accountId,
                'stage' => 'Closed Won'
            ])
            ->select(['SUM:amount'])
            ->findOne()
            ->get('SUM:amount') ?? 0;

        $account->set('totalRevenue', $totalRevenue);
        $this->entityManager->saveEntity($account);
    }

    private function trackStageChange(Entity $opportunity): void
    {
        $note = $this->entityManager->getNewEntity('Note');
        $note->set([
            'type' => 'Update',
            'parentType' => 'Opportunity',
            'parentId' => $opportunity->getId(),
            'data' => [
                'fields' => ['stage'],
                'attributes' => [
                    'stage' => [
                        'was' => $opportunity->getFetched('stage'),
                        'became' => $opportunity->get('stage')
                    ]
                ]
            ]
        ]);

        $this->entityManager->saveEntity($note);
    }

    private function getManagerForLargeDeals(): ?string
    {
        // Get sales manager role user
        $manager = $this->entityManager
            ->getRDBRepository('User')
            ->join('teams')
            ->where([
                'teams.name' => 'Sales Management',
                'isActive' => true
            ])
            ->findOne();

        return $manager?->getId();
    }
}
```

### Record Service Hook Points

Override these methods to inject custom logic into the standard CRUD flow:

```php
// Before operations
protected function beforeCreateEntity(Entity $entity, array $data): void
protected function beforeUpdateEntity(Entity $entity, array $data): void
protected function beforeDeleteEntity(Entity $entity): void

// After operations
protected function afterCreateEntity(Entity $entity, array $data): void
protected function afterUpdateEntity(Entity $entity, array $data): void
protected function afterDeleteEntity(Entity $entity): void

// Link operations
protected function beforeLink(Entity $entity, string $link, Entity $foreign): void
protected function afterLink(Entity $entity, string $link, Entity $foreign): void
protected function beforeUnlink(Entity $entity, string $link, Entity $foreign): void
protected function afterUnlink(Entity $entity, string $link, Entity $foreign): void
```

## Hook System

Hooks are for **validation and side effects ONLY**, not business logic. Business logic belongs in Services.

### The 7 Hook Types

#### 1. BeforeSave - Validation

```php
<?php
namespace Espo\Modules\MyModule\Hooks\Account;

use Espo\ORM\Entity;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\Core\Exceptions\BadRequest;

class ValidateData implements BeforeSave
{
    public function beforeSave(Entity $entity, array $options): void
    {
        // Validation: Check phone number format
        if ($entity->isAttributeChanged('phoneNumber')) {
            $phone = $entity->get('phoneNumber');

            if ($phone && !$this->isValidPhone($phone)) {
                throw new BadRequest('Invalid phone number format');
            }
        }

        // Validation: Ensure website starts with https
        if ($entity->isAttributeChanged('website')) {
            $website = $entity->get('website');

            if ($website && !str_starts_with($website, 'https://')) {
                $entity->set('website', 'https://' . ltrim($website, 'http://'));
            }
        }

        // Validation: Business rule
        if ($entity->get('type') === 'Customer' && !$entity->get('industry')) {
            throw new BadRequest('Industry is required for Customer accounts');
        }
    }

    private function isValidPhone(string $phone): bool
    {
        return preg_match('/^\+?[0-9\s\-\(\)]+$/', $phone);
    }
}
```

#### 2. AfterSave - Side Effects

```php
<?php
namespace Espo\Modules\MyModule\Hooks\Opportunity;

use Espo\ORM\Entity;
use Espo\Core\Hook\Hook\AfterSave;
use Espo\ORM\EntityManager;

class UpdateAccountStats implements AfterSave
{
    public function __construct(private EntityManager $entityManager) {}

    public function afterSave(Entity $entity, array $options): void
    {
        // Side effect: Update account statistics when opportunity stage changes
        if ($entity->isAttributeChanged('stage')) {
            $accountId = $entity->get('accountId');

            if ($accountId) {
                $this->updateAccountOpportunityStats($accountId);
            }
        }

        // Side effect: Create activity when opportunity is won
        if ($entity->isAttributeChanged('stage') && $entity->get('stage') === 'Closed Won') {
            $this->createWonActivity($entity);
        }
    }

    private function updateAccountOpportunityStats(string $accountId): void
    {
        $account = $this->entityManager->getEntityById('Account', $accountId);

        if (!$account) {
            return;
        }

        // Count opportunities
        $openCount = $this->entityManager
            ->getRDBRepository('Opportunity')
            ->where([
                'accountId' => $accountId,
                'stage!=' => ['Closed Won', 'Closed Lost']
            ])
            ->count();

        $account->set('openOpportunitiesCount', $openCount);
        $this->entityManager->saveEntity($account);
    }

    private function createWonActivity(Entity $opportunity): void
    {
        $meeting = $this->entityManager->getNewEntity('Meeting');
        $meeting->set([
            'name' => 'Follow-up: ' . $opportunity->get('name'),
            'parentType' => 'Opportunity',
            'parentId' => $opportunity->getId(),
            'assignedUserId' => $opportunity->get('assignedUserId'),
            'status' => 'Planned',
            'dateStart' => date('Y-m-d H:i:s', strtotime('+1 week'))
        ]);

        $this->entityManager->saveEntity($meeting);
    }
}
```

#### 3. BeforeRemove - Pre-deletion Validation

```php
<?php
namespace Espo\Modules\MyModule\Hooks\Account;

use Espo\ORM\Entity;
use Espo\Core\Hook\Hook\BeforeRemove;
use Espo\Core\Exceptions\Forbidden;
use Espo\ORM\EntityManager;

class PreventDeletionWithOpenOpportunities implements BeforeRemove
{
    public function __construct(private EntityManager $entityManager) {}

    public function beforeRemove(Entity $entity, array $options): void
    {
        // Validation: Prevent deletion if account has open opportunities
        $hasOpenOpportunities = $this->entityManager
            ->getRDBRepository('Opportunity')
            ->where([
                'accountId' => $entity->getId(),
                'stage!=' => ['Closed Won', 'Closed Lost']
            ])
            ->count() > 0;

        if ($hasOpenOpportunities) {
            throw new Forbidden('Cannot delete account with open opportunities');
        }
    }
}
```

#### 4. AfterRemove - Post-deletion Cleanup

```php
<?php
namespace Espo\Modules\MyModule\Hooks\Account;

use Espo\ORM\Entity;
use Espo\Core\Hook\Hook\AfterRemove;
use Espo\ORM\EntityManager;

class CleanupRelatedData implements AfterRemove
{
    public function __construct(private EntityManager $entityManager) {}

    public function afterRemove(Entity $entity, array $options): void
    {
        // Cleanup: Remove orphaned custom records
        $customRecords = $this->entityManager
            ->getRDBRepository('CustomEntity')
            ->where(['accountId' => $entity->getId()])
            ->find();

        foreach ($customRecords as $record) {
            $this->entityManager->removeEntity($record);
        }
    }
}
```

#### 5. AfterRelate - React to Relationship Creation

```php
<?php
namespace Espo\Modules\MyModule\Hooks\Contact;

use Espo\ORM\Entity;
use Espo\Core\Hook\Hook\AfterRelate;
use Espo\ORM\EntityManager;

class UpdateAccountContacts implements AfterRelate
{
    public function __construct(private EntityManager $entityManager) {}

    public function afterRelate(
        Entity $entity,
        string $relationName,
        Entity $foreign,
        ?array $columnData,
        array $options
    ): void {
        // React to contact being linked to account
        if ($relationName === 'account') {
            $account = $foreign;

            // Update account's primary contact if not set
            if (!$account->get('primaryContactId')) {
                $account->set('primaryContactId', $entity->getId());
                $this->entityManager->saveEntity($account);
            }
        }
    }
}
```

#### 6. AfterUnrelate - React to Relationship Removal

```php
<?php
namespace Espo\Modules\MyModule\Hooks\Contact;

use Espo\ORM\Entity;
use Espo\Core\Hook\Hook\AfterUnrelate;
use Espo\ORM\EntityManager;

class UpdateAccountOnUnlink implements AfterUnrelate
{
    public function __construct(private EntityManager $entityManager) {}

    public function afterUnrelate(
        Entity $entity,
        string $relationName,
        Entity $foreign,
        array $options
    ): void {
        // React to contact being unlinked from account
        if ($relationName === 'account') {
            $account = $foreign;

            // Clear primary contact if it was this contact
            if ($account->get('primaryContactId') === $entity->getId()) {
                $account->set('primaryContactId', null);
                $this->entityManager->saveEntity($account);
            }
        }
    }
}
```

#### 7. AfterMassRelate - React to Bulk Relationship Operations

```php
<?php
namespace Espo\Modules\MyModule\Hooks\Contact;

use Espo\ORM\Entity;
use Espo\Core\Hook\Hook\AfterMassRelate;
use Espo\ORM\EntityManager;

class RecalculateAccountStats implements AfterMassRelate
{
    public function __construct(private EntityManager $entityManager) {}

    public function afterMassRelate(
        Entity $entity,
        string $relationName,
        array $params,
        array $options
    ): void {
        // React to mass relate operation
        if ($relationName === 'accounts') {
            // Recalculate statistics for all affected accounts
            $this->recalculateStats($entity->getId());
        }
    }

    private function recalculateStats(string $contactId): void
    {
        // Implementation
    }
}
```

## Dependency Injection in Hooks

### Constructor Injection (CORRECT)

```php
<?php
namespace Espo\Modules\MyModule\Hooks\Account;

use Espo\ORM\Entity;
use Espo\Core\Hook\Hook\BeforeSave;
use Espo\ORM\EntityManager;
use Espo\Core\Utils\Metadata;
use Espo\Core\Mail\EmailSender;
use Espo\Core\ServiceFactory;

class MyHook implements BeforeSave
{
    public function __construct(
        private EntityManager $entityManager,
        private Metadata $metadata,
        private EmailSender $emailSender,
        private ServiceFactory $serviceFactory
    ) {}

    public function beforeSave(Entity $entity, array $options): void
    {
        // Use injected dependencies
        $config = $this->metadata->get(['app', 'myConfig']);

        // Access services
        $service = $this->serviceFactory->create('Account');
    }
}
```

### NEVER Pass Container

```php
// ❌ WRONG - Never inject Container
use Espo\Core\Container;

class BadHook implements BeforeSave
{
    public function __construct(private Container $container) {}
}

// ✅ CORRECT - Inject specific dependencies
use Espo\ORM\EntityManager;

class GoodHook implements BeforeSave
{
    public function __construct(private EntityManager $entityManager) {}
}
```

## Transaction Handling

Use TransactionManager for operations that must be atomic:

```php
<?php
namespace Espo\Modules\MyModule\Services;

use Espo\Services\Record;
use Espo\ORM\TransactionManager;

class MyEntity extends Record
{
    public function __construct(private TransactionManager $transactionManager)
    {
        parent::__construct();
    }

    public function complexOperation(string $id): void
    {
        $this->transactionManager->run(function () use ($id) {
            // All operations in this closure are transactional
            $entity = $this->getEntity($id);
            $entity->set('status', 'Processing');
            $this->entityManager->saveEntity($entity);

            // Related operation
            $relatedEntity = $this->entityManager->getNewEntity('RelatedEntity');
            $relatedEntity->set('parentId', $id);
            $this->entityManager->saveEntity($relatedEntity);

            // If any exception is thrown, ALL changes are rolled back
        });
    }
}
```

## Formula Scripts - Declarative Logic

Use Formula scripts for simple field calculations instead of hooks:

### Formula in Entity Metadata

```json
{
    "fields": {
        "totalPrice": {
            "type": "currency",
            "formula": "quantity * unitPrice"
        },
        "fullName": {
            "type": "varchar",
            "formula": "string\\concatenate(firstName, ' ', lastName)"
        },
        "daysUntilDue": {
            "type": "int",
            "formula": "datetime\\diff(datetime\\today(), dueDate, 'days')"
        }
    }
}
```

### Formula vs. Hooks Decision Matrix

| Use Case | Solution | Reason |
|----------|----------|--------|
| Calculate field from other fields | Formula | Simple, declarative |
| String concatenation | Formula | Built-in functions |
| Conditional field values | Formula | If/then logic available |
| Date calculations | Formula | Date functions available |
| Complex business rules | Service | Needs multiple entities |
| External API calls | Service | Needs async/error handling |
| Multi-entity operations | Service | Transaction support |
| Validation requiring DB query | Hook (BeforeSave) | Needs EntityManager |

### Formula Functions Reference

**String Functions:**
```javascript
string\concatenate(firstName, ' ', lastName)
string\substring(name, 0, 10)
string\length(description)
string\trim(input)
string\lowerCase(email)
string\upperCase(name)
```

**Date Functions:**
```javascript
datetime\today()
datetime\now()
datetime\diff(date1, date2, 'days')
datetime\addDays(dateStart, 5)
datetime\month(dateStart)
datetime\year(dateStart)
```

**Numeric Functions:**
```javascript
number\round(amount, 2)
number\floor(value)
number\ceil(value)
number\abs(value)
```

**Conditional Logic:**
```javascript
ifThen(
    status == 'Complete',
    100,
    probability
)

ifThenElse(
    amount > 10000,
    'High',
    'Normal'
)
```

## Best Practices

### 1. Business Logic Placement

```php
// ✅ CORRECT - Business logic in Service
class OpportunityService extends Record {
    public function calculateCommission(string $id): float {
        $opportunity = $this->getEntity($id);
        $amount = $opportunity->get('amount');
        $stage = $opportunity->get('stage');

        return $this->getCommissionCalculator()->calculate($amount, $stage);
    }
}

// ❌ WRONG - Business logic in Hook
class OpportunityHook implements AfterSave {
    public function afterSave(Entity $entity, array $options): void {
        // Don't put complex business logic here
        $commission = $this->calculateCommission($entity);
    }
}
```

### 2. Hook Complexity

```php
// ✅ CORRECT - Simple side effects in hooks
class NotificationHook implements AfterSave {
    public function afterSave(Entity $entity, array $options): void {
        if ($entity->isAttributeChanged('assignedUserId')) {
            $this->sendNotification($entity);
        }
    }
}

// ❌ WRONG - Complex logic in hooks
class ComplexHook implements AfterSave {
    public function afterSave(Entity $entity, array $options): void {
        // Too much logic - belongs in service
        $this->updateRelatedRecords($entity);
        $this->recalculateMetrics($entity);
        $this->syncWithExternalSystem($entity);
        $this->generateReports($entity);
    }
}
```

### 3. Avoid Recursive Hook Calls

```php
// ✅ CORRECT - Prevent recursive calls
class MyHook implements AfterSave {
    public function afterSave(Entity $entity, array $options): void {
        // Check if this is a programmatic save to avoid recursion
        if (!empty($options['silent'])) {
            return;
        }

        // Make changes to related entity
        $related = $this->entityManager->getEntityById('Related', $entity->get('relatedId'));
        $related->set('updated', true);

        // Save with 'silent' option to prevent triggering hooks
        $this->entityManager->saveEntity($related, ['silent' => true]);
    }
}
```

### 4. Type Safety

```php
// ✅ CORRECT - Strict types
declare(strict_types=1);

class MyHook implements BeforeSave {
    public function beforeSave(Entity $entity, array $options): void {
        $value = $entity->get('amount');

        if (!is_numeric($value)) {
            throw new BadRequest('Amount must be numeric');
        }
    }
}
```
