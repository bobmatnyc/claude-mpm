# Testing and Debugging Reference

## Unit Testing

EspoCRM supports PHPUnit for testing.

### Test Setup

Install PHPUnit in your extension:

```bash
composer require --dev phpunit/phpunit
```

Create `phpunit.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<phpunit
    bootstrap="tests/bootstrap.php"
    colors="true"
    convertErrorsToExceptions="true"
    convertNoticesToExceptions="true"
    convertWarningsToExceptions="true"
    stopOnFailure="false">
    <testsuites>
        <testsuite name="Unit Tests">
            <directory>tests/unit</directory>
        </testsuite>
        <testsuite name="Integration Tests">
            <directory>tests/integration</directory>
        </testsuite>
    </testsuites>
</phpunit>
```

### Unit Test Example

Create `tests/unit/MyServiceTest.php`:

```php
<?php
namespace Espo\Modules\MyModule\Tests\Unit;

use PHPUnit\Framework\TestCase;
use Espo\Modules\MyModule\Services\MyEntity;
use Espo\ORM\EntityManager;
use Espo\Core\Acl;
use Espo\Entities\User;

class MyServiceTest extends TestCase
{
    private MyEntity $service;
    private EntityManager $entityManager;
    private Acl $acl;
    private User $user;

    protected function setUp(): void
    {
        parent::setUp();

        // Create mocks
        $this->entityManager = $this->createMock(EntityManager::class);
        $this->acl = $this->createMock(Acl::class);
        $this->user = $this->createMock(User::class);

        // Create service with mocked dependencies
        $this->service = new MyEntity();

        // Inject dependencies via reflection (if needed)
        $reflection = new \ReflectionClass($this->service);
        $property = $reflection->getProperty('entityManager');
        $property->setAccessible(true);
        $property->setValue($this->service, $this->entityManager);
    }

    public function testCalculateTotal(): void
    {
        // Arrange
        $entity = $this->createMock(\Espo\ORM\Entity::class);

        $entity->method('get')
            ->willReturnMap([
                ['quantity', null, 5],
                ['unitPrice', null, 10.50]
            ]);

        // Act
        $total = $this->service->calculateTotal($entity);

        // Assert
        $this->assertEquals(52.50, $total);
    }

    public function testValidateThrowsExceptionForInvalidData(): void
    {
        // Arrange
        $entity = $this->createMock(\Espo\ORM\Entity::class);
        $entity->method('get')
            ->willReturn(-100);

        // Assert
        $this->expectException(\Espo\Core\Exceptions\BadRequest::class);
        $this->expectExceptionMessage('Amount cannot be negative');

        // Act
        $this->service->validate($entity);
    }

    public function testCreateEntitySetsDefaults(): void
    {
        // Arrange
        $entity = $this->createMock(\Espo\ORM\Entity::class);

        $this->user->method('getId')
            ->willReturn('user-123');

        $entity->expects($this->once())
            ->method('set')
            ->with('assignedUserId', 'user-123');

        // Act
        $this->service->setDefaults($entity);
    }
}
```

### Integration Test Example

Create `tests/integration/HookTest.php`:

```php
<?php
namespace Espo\Modules\MyModule\Tests\Integration;

use PHPUnit\Framework\TestCase;
use Espo\Core\Container;
use Espo\ORM\EntityManager;

class HookTest extends TestCase
{
    private Container $container;
    private EntityManager $entityManager;

    protected function setUp(): void
    {
        parent::setUp();

        // Load EspoCRM container (requires EspoCRM installation)
        require_once 'bootstrap.php';

        $this->container = $GLOBALS['container'];
        $this->entityManager = $this->container->get('entityManager');
    }

    public function testAccountHookUpdatesRelatedContacts(): void
    {
        // Create test account
        $account = $this->entityManager->getNewEntity('Account');
        $account->set('name', 'Test Account');
        $this->entityManager->saveEntity($account);

        // Create related contact
        $contact = $this->entityManager->getNewEntity('Contact');
        $contact->set([
            'firstName' => 'John',
            'lastName' => 'Doe',
            'accountId' => $account->getId()
        ]);
        $this->entityManager->saveEntity($contact);

        // Update account status
        $account->set('status', 'Inactive');
        $this->entityManager->saveEntity($account);

        // Refresh contact
        $contact = $this->entityManager->getEntityById('Contact', $contact->getId());

        // Assert hook updated contact
        $this->assertEquals('Inactive', $contact->get('accountStatus'));

        // Cleanup
        $this->entityManager->removeEntity($contact);
        $this->entityManager->removeEntity($account);
    }
}
```

### Running Tests

```bash
# Run all tests
vendor/bin/phpunit

# Run specific test file
vendor/bin/phpunit tests/unit/MyServiceTest.php

# Run specific test method
vendor/bin/phpunit --filter testCalculateTotal

# Run with coverage
vendor/bin/phpunit --coverage-html coverage
```

## Debugging Techniques

### Enable Debug Mode

Edit `data/config.php`:

```php
<?php
return [
    // ... other config ...
    'logger' => [
        'level' => 'DEBUG', // Change from 'WARNING' to 'DEBUG'
        'maxFileNumber' => 30,
    ],
    'isDeveloperMode' => true, // Enable developer mode
];
```

### Logging

```php
<?php
namespace Espo\Modules\MyModule\Services;

use Espo\Core\Utils\Log;

class MyService
{
    public function __construct(private Log $log) {}

    public function processData(array $data): void
    {
        // Debug logging
        $this->log->debug('Processing data', ['data' => $data]);

        try {
            // ... processing ...

            $this->log->info('Data processed successfully', ['count' => count($data)]);
        } catch (\Throwable $e) {
            $this->log->error('Failed to process data: ' . $e->getMessage(), [
                'exception' => $e,
                'trace' => $e->getTraceAsString()
            ]);

            throw $e;
        }
    }

    public function debugQuery(): void
    {
        $query = $this->entityManager
            ->getQueryBuilder()
            ->select()
            ->from('Account')
            ->where(['type' => 'Customer'])
            ->build();

        // Log the SQL query
        $sql = $this->entityManager->getQueryComposer()->compose($query);
        $this->log->debug('SQL Query', ['sql' => $sql]);
    }
}
```

### Check Logs

```bash
# Today's log
tail -f data/logs/espo-$(date +%Y-%m-%d).log

# Search logs
grep "ERROR" data/logs/espo-*.log

# Filter by component
grep "MyService" data/logs/espo-*.log
```

### XDebug Setup

Install XDebug PHP extension:

```bash
# Ubuntu/Debian
sudo apt-get install php-xdebug

# macOS (Homebrew)
brew install php-xdebug
```

Configure XDebug in `php.ini`:

```ini
[xdebug]
zend_extension=xdebug.so
xdebug.mode=debug
xdebug.start_with_request=yes
xdebug.client_host=127.0.0.1
xdebug.client_port=9003
xdebug.idekey=PHPSTORM
```

### Step Debugging with PhpStorm

1. Set breakpoints in code
2. Click "Start Listening for PHP Debug Connections"
3. Trigger the code path (API call, scheduled job, etc.)
4. PhpStorm will pause at breakpoints

### Debug API Requests

```bash
# Using curl with verbose output
curl -v -X GET \
  'http://espocrm.local/api/v1/Account/123' \
  -H 'X-Api-Key: your-api-key'

# Debug POST request
curl -v -X POST \
  'http://espocrm.local/api/v1/Account' \
  -H 'Content-Type: application/json' \
  -H 'X-Api-Key: your-api-key' \
  -d '{
    "name": "Test Account",
    "type": "Customer"
  }'

# Save response to file for analysis
curl -X GET \
  'http://espocrm.local/api/v1/Account' \
  -H 'X-Api-Key: your-api-key' \
  -o response.json
```

### Browser DevTools for Frontend Debugging

```javascript
// Add console logging in custom views
define('custom:views/my-view', ['view'], function (Dep) {
    return Dep.extend({
        setup: function () {
            Dep.prototype.setup.call(this);

            console.log('View setup', {
                model: this.model.attributes,
                options: this.options
            });
        },

        afterRender: function () {
            Dep.prototype.afterRender.call(this);

            console.log('View rendered', {
                el: this.$el,
                modelId: this.model.id
            });
        }
    });
});

// Debug AJAX requests
this.ajaxPostRequest('Account/action/myAction', data)
    .then(response => {
        console.log('Response received', response);
    })
    .catch(xhr => {
        console.error('Request failed', {
            status: xhr.status,
            response: xhr.responseJSON,
            error: xhr.responseText
        });
    });
```

### Database Debugging

```bash
# Connect to MySQL
mysql -u espocrm_user -p espocrm_db

# Enable query logging
SET GLOBAL general_log = 'ON';
SET GLOBAL log_output = 'TABLE';

# View query log
SELECT * FROM mysql.general_log
WHERE command_type = 'Query'
ORDER BY event_time DESC
LIMIT 100;

# Disable query logging
SET GLOBAL general_log = 'OFF';
```

### SQL Query Analysis

```php
// Log query execution time
$startTime = microtime(true);

$result = $this->entityManager
    ->getRDBRepository('Account')
    ->where(['type' => 'Customer'])
    ->find();

$executionTime = microtime(true) - $startTime;

$this->log->debug('Query execution time', [
    'time' => $executionTime,
    'count' => count($result)
]);

// Explain query
$query = $this->entityManager
    ->getQueryBuilder()
    ->select()
    ->from('Account')
    ->where(['type' => 'Customer'])
    ->build();

$sql = $this->entityManager->getQueryComposer()->compose($query);

$pdo = $this->entityManager->getPDO();
$sth = $pdo->prepare('EXPLAIN ' . $sql);
$sth->execute();

$explain = $sth->fetchAll(\PDO::FETCH_ASSOC);
$this->log->debug('Query explain', ['explain' => $explain]);
```

## Performance Optimization

### Use STH Collections for Large Datasets

```php
// ❌ WRONG - Loads all records into memory
$contacts = $this->entityManager
    ->getRDBRepository('Contact')
    ->find();

foreach ($contacts as $contact) {
    // Process
}

// ✅ CORRECT - Streams records one at a time
$sthCollection = $this->entityManager
    ->getRDBRepository('Contact')
    ->sth()
    ->find();

foreach ($sthCollection as $contact) {
    // Process without loading all into memory
}
```

### Batch Operations

```php
// ❌ WRONG - One query per update
$accounts = $this->entityManager
    ->getRDBRepository('Account')
    ->where(['type' => 'Customer'])
    ->find();

foreach ($accounts as $account) {
    $account->set('updated', true);
    $this->entityManager->saveEntity($account);  // Individual query
}

// ✅ CORRECT - Batch update with single query
$this->entityManager
    ->getQueryBuilder()
    ->update()
    ->in('Account')
    ->set(['updated' => true])
    ->where(['type' => 'Customer'])
    ->build()
    ->execute();
```

### Query Optimization

```php
// ❌ WRONG - N+1 queries
$opportunities = $this->entityManager
    ->getRDBRepository('Opportunity')
    ->find();

foreach ($opportunities as $opportunity) {
    // Each iteration makes a query for account
    $account = $this->entityManager
        ->getEntityById('Account', $opportunity->get('accountId'));
}

// ✅ CORRECT - Single query with JOIN
$opportunities = $this->entityManager
    ->getRDBRepository('Opportunity')
    ->distinct()
    ->join('account')
    ->select(['*', 'account.name AS accountName'])
    ->find();

foreach ($opportunities as $opportunity) {
    // Account name already loaded
    $accountName = $opportunity->get('accountName');
}
```

### Caching

```php
use Espo\Core\Utils\DataCache;

class MyService
{
    public function __construct(private DataCache $dataCache) {}

    public function getExpensiveData(): array
    {
        $cacheKey = 'myExpensiveData';

        // Try to get from cache
        if ($this->dataCache->has($cacheKey)) {
            return $this->dataCache->get($cacheKey);
        }

        // Calculate if not cached
        $data = $this->performExpensiveCalculation();

        // Store in cache for 1 hour
        $this->dataCache->store($cacheKey, $data, 3600);

        return $data;
    }

    private function performExpensiveCalculation(): array
    {
        // Expensive operation
        return [];
    }
}
```

### Profiling with Xdebug

```php
// Enable profiling in php.ini
xdebug.mode=profile
xdebug.output_dir=/tmp/xdebug
xdebug.start_with_request=trigger

// Trigger with request parameter
// http://espocrm.local/api/v1/Account?XDEBUG_PROFILE=1

// Analyze with tools like:
// - KCachegrind (Linux)
// - QCachegrind (macOS/Windows)
// - PhpStorm built-in profiler
```

## Common Pitfalls and Solutions

### Pitfall 1: Infinite Hook Loops

**Problem:**
```php
// Hook triggers itself infinitely
class MyHook implements AfterSave {
    public function afterSave(Entity $entity, array $options): void {
        $entity->set('updated', true);
        $this->entityManager->saveEntity($entity); // Triggers hook again!
    }
}
```

**Solution:**
```php
class MyHook implements AfterSave {
    public function afterSave(Entity $entity, array $options): void {
        // Check if already processing
        if (!empty($options['skipHooks'])) {
            return;
        }

        $entity->set('updated', true);
        $this->entityManager->saveEntity($entity, ['skipHooks' => true]);
    }
}
```

### Pitfall 2: Missing Cache Rebuild

**Problem:**
- Metadata changes not reflected
- New classes not found

**Solution:**
```bash
# Always rebuild after metadata or class changes
bin/command rebuild
```

### Pitfall 3: Type Mismatches

**Problem:**
```php
// Method expects string, gets null
public function process(string $id): void {
    // $id is null, causes error
}
```

**Solution:**
```php
// Use nullable types
public function process(?string $id): void {
    if (!$id) {
        throw new BadRequest('ID is required');
    }
    // Process
}
```

### Pitfall 4: Container Dependency

**Problem:**
```php
// Tight coupling to Container
class MyService {
    public function __construct(private Container $container) {}
}
```

**Solution:**
```php
// Inject specific dependencies
class MyService {
    public function __construct(
        private EntityManager $entityManager,
        private Metadata $metadata
    ) {}
}
```

### Pitfall 5: Not Using Transactions

**Problem:**
```php
// Partial updates on error
$entity1->set('status', 'Processing');
$this->entityManager->saveEntity($entity1);

// Error occurs here
throw new \Exception('Error');

// entity2 never updated, data inconsistent
$entity2->set('status', 'Complete');
$this->entityManager->saveEntity($entity2);
```

**Solution:**
```php
use Espo\ORM\TransactionManager;

// Atomic operation
$this->transactionManager->run(function () {
    $entity1->set('status', 'Processing');
    $this->entityManager->saveEntity($entity1);

    // If error occurs, both changes rolled back
    if ($error) {
        throw new \Exception('Error');
    }

    $entity2->set('status', 'Complete');
    $this->entityManager->saveEntity($entity2);
});
```

### Pitfall 6: Direct PDO Usage

**Problem:**
```php
// Bypassing ORM
$pdo = $this->entityManager->getPDO();
$pdo->query("INSERT INTO account (name) VALUES ('Test')");
```

**Solution:**
```php
// Use ORM
$account = $this->entityManager->getNewEntity('Account');
$account->set('name', 'Test');
$this->entityManager->saveEntity($account);
```

### Pitfall 7: Memory Exhaustion

**Problem:**
```php
// Loading 100k records into memory
$contacts = $this->entityManager
    ->getRDBRepository('Contact')
    ->find();  // Memory exhausted!
```

**Solution:**
```php
// Use STH collection
$sthCollection = $this->entityManager
    ->getRDBRepository('Contact')
    ->sth()
    ->find();

foreach ($sthCollection as $contact) {
    // Process one at a time
}
```

## Error Handling Best Practices

### Use Specific Exceptions

```php
use Espo\Core\Exceptions\{
    BadRequest,
    Forbidden,
    NotFound,
    Conflict,
    Error
};

class MyService {
    public function process(string $id): Entity {
        // Validate input
        if (!$id) {
            throw new BadRequest('ID is required');
        }

        // Check existence
        $entity = $this->entityManager->getEntityById('Account', $id);
        if (!$entity) {
            throw new NotFound('Account not found');
        }

        // Check permissions
        if (!$this->acl->check($entity, 'edit')) {
            throw new Forbidden('No edit access');
        }

        // Check business rules
        if ($entity->get('locked')) {
            throw new Conflict('Account is locked');
        }

        // Process...
        return $entity;
    }
}
```

### Try-Catch Patterns

```php
// Catch and log
try {
    $this->performRiskyOperation();
} catch (\Throwable $e) {
    $this->log->error('Operation failed: ' . $e->getMessage(), [
        'exception' => $e
    ]);
    throw $e;  // Re-throw
}

// Catch and convert
try {
    $result = $this->externalApi->call();
} catch (\GuzzleHttp\Exception\RequestException $e) {
    throw new Error('External API failed: ' . $e->getMessage());
}

// Catch specific, let others propagate
try {
    $this->operation();
} catch (NotFound $e) {
    // Handle not found specifically
    return $this->createDefault();
}
// Other exceptions propagate up
```

## Debugging Checklist

When something doesn't work:

1. **Check Logs**
   - `data/logs/espo-YYYY-MM-DD.log`
   - PHP error logs

2. **Verify Cache Rebuild**
   - `bin/command rebuild`

3. **Check Permissions**
   - File permissions (files should be writable)
   - ACL permissions (user has access)

4. **Validate Metadata**
   - JSON syntax correct
   - Required fields present

5. **Check Database**
   - Table exists
   - Columns exist
   - Indexes present

6. **Test API Directly**
   - Use curl or Postman
   - Check request/response

7. **Enable Debug Mode**
   - `'logger' => ['level' => 'DEBUG']`
   - `'isDeveloperMode' => true`

8. **Use XDebug**
   - Set breakpoints
   - Step through code
   - Inspect variables
