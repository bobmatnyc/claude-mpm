# Common Tasks Reference

## Scheduled Jobs

Scheduled jobs run automatically at specified intervals via cron.

### Creating a Scheduled Job

#### Step 1: Define Job in Metadata

Create `src/files/custom/Espo/Modules/MyModule/Resources/metadata/app/scheduledJobs.json`:

```json
{
    "MyCustomJob": {
        "name": "My Custom Job",
        "scheduling": "*/30 * * * *"
    },
    "DataSyncJob": {
        "name": "Sync External Data",
        "scheduling": "0 2 * * *"
    }
}
```

Scheduling format (cron syntax):
```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-6, Sunday = 0)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

Common schedules:
- `*/5 * * * *` - Every 5 minutes
- `0 * * * *` - Every hour
- `0 2 * * *` - Daily at 2 AM
- `0 0 * * 0` - Weekly on Sunday at midnight

#### Step 2: Implement Job Class

Create `src/files/custom/Espo/Modules/MyModule/Jobs/MyCustomJob.php`:

```php
<?php
namespace Espo\Modules\MyModule\Jobs;

use Espo\Core\Job\JobDataLess;
use Espo\ORM\EntityManager;
use Espo\Core\Utils\Log;

class MyCustomJob implements JobDataLess
{
    public function __construct(
        private EntityManager $entityManager,
        private Log $log
    ) {}

    public function run(): void
    {
        $this->log->info('MyCustomJob started');

        try {
            // Job logic
            $this->processRecords();

            $this->log->info('MyCustomJob completed successfully');
        } catch (\Throwable $e) {
            $this->log->error('MyCustomJob failed: ' . $e->getMessage());
            throw $e;
        }
    }

    private function processRecords(): void
    {
        $accounts = $this->entityManager
            ->getRDBRepository('Account')
            ->where([
                'status' => 'Active',
                'lastContactedAt<' => date('Y-m-d', strtotime('-30 days'))
            ])
            ->find();

        foreach ($accounts as $account) {
            $account->set('needsFollowUp', true);
            $this->entityManager->saveEntity($account);
        }

        $this->log->info('Processed ' . count($accounts) . ' accounts');
    }
}
```

#### Advanced: Job with Data

For jobs that need parameters:

```php
<?php
namespace Espo\Modules\MyModule\Jobs;

use Espo\Core\Job\Job;
use Espo\Core\Job\Job\Data;

class DataSyncJob implements Job
{
    public function __construct(
        private EntityManager $entityManager,
        private Log $log
    ) {}

    public function run(Data $data): void
    {
        $entityType = $data->get('entityType');
        $limit = $data->get('limit') ?? 100;

        $this->syncData($entityType, $limit);
    }

    private function syncData(string $entityType, int $limit): void
    {
        // Implementation
    }
}
```

### Running Jobs Manually

```php
// Via service
use Espo\Core\Job\JobSchedulerFactory;

class MyService {
    public function __construct(
        private JobSchedulerFactory $jobSchedulerFactory
    ) {}

    public function triggerJob(): void
    {
        $jobScheduler = $this->jobSchedulerFactory->create();

        $jobScheduler->scheduleJob('MyCustomJob', [
            'entityType' => 'Account',
            'limit' => 50
        ]);
    }
}
```

## Email Management

### Sending Emails

```php
<?php
namespace Espo\Modules\MyModule\Services;

use Espo\Core\Mail\EmailSender;
use Espo\Entities\Email;
use Espo\ORM\EntityManager;

class NotificationService
{
    public function __construct(
        private EmailSender $emailSender,
        private EntityManager $entityManager
    ) {}

    public function sendWelcomeEmail(string $contactId): void
    {
        $contact = $this->entityManager->getEntityById('Contact', $contactId);

        if (!$contact) {
            return;
        }

        $emailAddress = $contact->get('emailAddress');

        if (!$emailAddress) {
            return;
        }

        $sender = $this->emailSender->create();

        $sender
            ->withSubject('Welcome to Our Platform')
            ->withBody('Dear ' . $contact->get('name') . ',\n\nWelcome!')
            ->withTo($emailAddress)
            ->send();
    }

    public function sendEmailWithTemplate(string $contactId): void
    {
        $contact = $this->entityManager->getEntityById('Contact', $contactId);

        if (!$contact) {
            return;
        }

        // Create email entity
        $email = $this->entityManager->getNewEntity('Email');

        $email->set([
            'to' => $contact->get('emailAddress'),
            'subject' => 'Welcome',
            'body' => $this->renderTemplate($contact),
            'isHtml' => true,
            'parentType' => 'Contact',
            'parentId' => $contactId
        ]);

        $this->entityManager->saveEntity($email);

        // Send
        $sender = $this->emailSender->create();
        $sender
            ->withEnvelopeOptions([
                'from' => 'noreply@example.com'
            ])
            ->send($email);
    }

    private function renderTemplate($contact): string
    {
        return '<h1>Welcome ' . htmlspecialchars($contact->get('name')) . '</h1>';
    }
}
```

### Email Templates

Create `src/files/custom/Espo/Modules/MyModule/Resources/metadata/app/emailTemplates.json`:

```json
{
    "welcomeEmail": {
        "subject": "Welcome {Contact.name}",
        "body": "<p>Dear {Contact.name},</p><p>Welcome to our platform!</p>"
    }
}
```

Using email templates:

```php
use Espo\Tools\EmailTemplate\Processor;

class EmailService {
    public function __construct(
        private Processor $emailTemplateProcessor,
        private EmailSender $emailSender,
        private EntityManager $entityManager
    ) {}

    public function sendFromTemplate(string $templateId, string $entityId): void
    {
        $template = $this->entityManager->getEntityById('EmailTemplate', $templateId);
        $entity = $this->entityManager->getEntityById('Contact', $entityId);

        // Process template (replace placeholders)
        $data = $this->emailTemplateProcessor->process($template, [
            'entityType' => 'Contact',
            'entity' => $entity
        ]);

        // Send
        $sender = $this->emailSender->create();
        $sender
            ->withSubject($data->getSubject())
            ->withBody($data->getBody())
            ->withTo($entity->get('emailAddress'))
            ->withIsHtml($data->isHtml())
            ->send();
    }
}
```

## PDF Generation

### Creating PDF Templates

PDF templates use HTML with placeholders.

Create `custom/Espo/Custom/Resources/templates/Invoice.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; }
        .header { text-align: center; margin-bottom: 30px; }
        .invoice-details { margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .total { text-align: right; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header">
        <h1>INVOICE</h1>
        <p>Invoice #{{number}}</p>
    </div>

    <div class="invoice-details">
        <p><strong>Date:</strong> {{dateInvoiced}}</p>
        <p><strong>Customer:</strong> {{account.name}}</p>
        <p><strong>Amount:</strong> {{amount}}</p>
    </div>

    <table>
        <thead>
            <tr>
                <th>Item</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            {{#each items}}
            <tr>
                <td>{{name}}</td>
                <td>{{quantity}}</td>
                <td>{{price}}</td>
                <td>{{total}}</td>
            </tr>
            {{/each}}
        </tbody>
    </table>

    <div class="total">
        <p>Total: {{amount}}</p>
    </div>
</body>
</html>
```

### Generating PDFs Programmatically

```php
<?php
namespace Espo\Modules\MyModule\Services;

use Espo\Tools\Pdf\Service as PdfService;
use Espo\ORM\EntityManager;

class InvoiceService
{
    public function __construct(
        private PdfService $pdfService,
        private EntityManager $entityManager
    ) {}

    public function generateInvoicePdf(string $invoiceId): string
    {
        $invoice = $this->entityManager->getEntityById('Invoice', $invoiceId);

        if (!$invoice) {
            throw new \Espo\Core\Exceptions\NotFound();
        }

        // Generate PDF
        $contents = $this->pdfService->generate(
            'Invoice',                    // Entity type
            $invoiceId,                   // Entity ID
            'Invoice'                     // Template name
        );

        // Save to file
        $fileName = 'invoice_' . $invoice->get('number') . '.pdf';
        $filePath = 'data/upload/' . $fileName;

        file_put_contents($filePath, $contents);

        return $filePath;
    }
}
```

## Access Control (ACL)

### Implementing Custom ACL

Create `src/files/custom/Espo/Modules/MyModule/Acl/MyEntity.php`:

```php
<?php
namespace Espo\Modules\MyModule\Acl;

use Espo\ORM\Entity;
use Espo\Core\Acl\Table;
use Espo\Entities\User;
use Espo\Core\Acl\AccessEntityCREDChecker;
use Espo\Core\Acl\DefaultAccessChecker;
use Espo\Core\Acl\ScopeData;
use Espo\Core\Acl\Traits\DefaultAccessCheckerDependency;

class MyEntity implements AccessEntityCREDChecker
{
    use DefaultAccessCheckerDependency;

    public function __construct(
        private DefaultAccessChecker $defaultAccessChecker
    ) {}

    public function checkEntityRead(User $user, Entity $entity, ScopeData $data): bool
    {
        // Custom read permission logic

        // Check if user is assigned
        if ($entity->get('assignedUserId') === $user->getId()) {
            return true;
        }

        // Check if user is in account team
        if ($entity->get('accountId')) {
            $account = $entity->get('account');
            if ($this->isUserInAccountTeams($user, $account)) {
                return true;
            }
        }

        // Fall back to default ACL check
        return $this->defaultAccessChecker->checkEntityRead($user, $entity, $data);
    }

    public function checkEntityCreate(User $user, Entity $entity, ScopeData $data): bool
    {
        // Custom create permission logic
        if ($user->get('type') === 'portal') {
            // Portal users can only create if they have an account
            return $entity->get('accountId') !== null;
        }

        return $this->defaultAccessChecker->checkEntityCreate($user, $entity, $data);
    }

    public function checkEntityEdit(User $user, Entity $entity, ScopeData $data): bool
    {
        // Custom edit permission logic

        // Only owner can edit after 7 days
        $createdAt = $entity->get('createdAt');
        if ($createdAt) {
            $daysSinceCreation = (time() - strtotime($createdAt)) / 86400;

            if ($daysSinceCreation > 7) {
                if ($entity->get('createdById') !== $user->getId()) {
                    return false;
                }
            }
        }

        return $this->defaultAccessChecker->checkEntityEdit($user, $entity, $data);
    }

    public function checkEntityDelete(User $user, Entity $entity, ScopeData $data): bool
    {
        // Custom delete permission logic

        // Prevent deletion of completed items
        if ($entity->get('status') === 'Complete') {
            return false;
        }

        return $this->defaultAccessChecker->checkEntityDelete($user, $entity, $data);
    }

    private function isUserInAccountTeams(User $user, ?Entity $account): bool
    {
        if (!$account) {
            return false;
        }

        $userTeamIds = array_column($user->get('teams')->toArray(), 'id');
        $accountTeamIds = array_column($account->get('teams')->toArray(), 'id');

        return !empty(array_intersect($userTeamIds, $accountTeamIds));
    }
}
```

### Checking ACL in Code

```php
// Check entity-level permission
if (!$this->acl->check($entity, 'read')) {
    throw new Forbidden();
}

// Check scope-level permission
if (!$this->acl->check('Account', 'create')) {
    throw new Forbidden();
}

// Check field-level permission
if (!$this->acl->checkField('Account', 'billingAddress', 'edit')) {
    throw new Forbidden('Cannot edit billing address');
}

// Check ownership level
$level = $this->acl->getLevel('Account', 'read');
// Levels: all, team, own, no

// Filter query by ACL
$query = $this->entityManager
    ->getQueryBuilder()
    ->select()
    ->from('Account')
    ->build();

$this->acl->applyFilter($query, 'Account', 'read');
```

## Workflow Customization

### Custom Workflow Action

Create `src/files/custom/Espo/Modules/MyModule/Classes/Workflow/Actions/SendSlackNotification.php`:

```php
<?php
namespace Espo\Modules\MyModule\Classes\Workflow\Actions;

use Espo\Core\Workflow\Action;
use Espo\Core\Workflow\Action\Params;
use Espo\ORM\Entity;

class SendSlackNotification implements Action
{
    public function __construct(
        private SlackClient $slackClient
    ) {}

    public function run(Entity $entity, Params $params): bool
    {
        $channel = $params->get('channel') ?? '#general';
        $message = $params->get('message') ?? 'Entity updated';

        // Replace placeholders
        $message = str_replace('{name}', $entity->get('name'), $message);

        $this->slackClient->sendMessage($channel, $message);

        return true;
    }
}
```

### Custom Workflow Condition

Create `src/files/custom/Espo/Modules/MyModule/Classes/Workflow/Conditions/IsHighValue.php`:

```php
<?php
namespace Espo\Modules\MyModule\Classes\Workflow\Conditions;

use Espo\Core\Workflow\Condition;
use Espo\Core\Workflow\Condition\Params;
use Espo\ORM\Entity;

class IsHighValue implements Condition
{
    public function check(Entity $entity, Params $params): bool
    {
        $threshold = $params->get('threshold') ?? 10000;
        $amount = $entity->get('amount') ?? 0;

        return $amount >= $threshold;
    }
}
```

## Integration Patterns

### REST API Integration

```php
<?php
namespace Espo\Modules\MyModule\Services;

use Espo\Core\Utils\Config;
use Espo\Core\Utils\Log;

class ExternalApiService
{
    private string $apiUrl;
    private string $apiKey;

    public function __construct(
        private Config $config,
        private Log $log
    ) {
        $this->apiUrl = $this->config->get('externalApiUrl');
        $this->apiKey = $this->config->get('externalApiKey');
    }

    public function fetchCustomerData(string $customerId): ?array
    {
        $url = $this->apiUrl . '/customers/' . $customerId;

        $ch = curl_init();

        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => [
                'Authorization: Bearer ' . $this->apiKey,
                'Content-Type: application/json'
            ]
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

        curl_close($ch);

        if ($httpCode !== 200) {
            $this->log->error('External API request failed: ' . $httpCode);
            return null;
        }

        return json_decode($response, true);
    }

    public function syncCustomer(Entity $account): bool
    {
        $data = [
            'name' => $account->get('name'),
            'email' => $account->get('emailAddress'),
            'phone' => $account->get('phoneNumber')
        ];

        $url = $this->apiUrl . '/customers';

        $ch = curl_init();

        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($data),
            CURLOPT_HTTPHEADER => [
                'Authorization: Bearer ' . $this->apiKey,
                'Content-Type: application/json'
            ]
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);

        curl_close($ch);

        if ($httpCode === 201) {
            $responseData = json_decode($response, true);
            $account->set('externalId', $responseData['id']);
            return true;
        }

        $this->log->error('Failed to sync customer: ' . $httpCode);
        return false;
    }
}
```

### Webhook Handler

```php
<?php
namespace Espo\Modules\MyModule\Controllers;

use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Controllers\Base;
use Espo\Core\Exceptions\BadRequest;

class Webhook extends Base
{
    public function postActionReceive(Request $request, Response $response): bool
    {
        $data = $request->getParsedBody();

        if (!$data->event) {
            throw new BadRequest('Missing event type');
        }

        // Verify webhook signature
        $signature = $request->getHeader('X-Webhook-Signature');
        if (!$this->verifySignature($signature, $request->getBodyContents())) {
            throw new Forbidden('Invalid signature');
        }

        // Process webhook
        $service = $this->getRecordService('WebhookEvent');
        $service->processWebhook($data->event, $data);

        $response->setStatus(200);
        return true;
    }

    private function verifySignature(?string $signature, string $payload): bool
    {
        if (!$signature) {
            return false;
        }

        $secret = $this->config->get('webhookSecret');
        $expectedSignature = hash_hmac('sha256', $payload, $secret);

        return hash_equals($expectedSignature, $signature);
    }
}
```

## File Handling

### File Upload and Storage

```php
<?php
namespace Espo\Modules\MyModule\Services;

use Espo\Core\FileStorage\Manager as FileStorageManager;
use Espo\Entities\Attachment;

class DocumentService
{
    public function __construct(
        private FileStorageManager $fileStorageManager,
        private EntityManager $entityManager
    ) {}

    public function uploadFile(string $filePath, string $name, string $type): Attachment
    {
        $contents = file_get_contents($filePath);

        $attachment = $this->entityManager->getNewEntity('Attachment');
        $attachment->set([
            'name' => $name,
            'type' => $type,
            'size' => strlen($contents),
            'role' => 'Attachment'
        ]);

        $this->entityManager->saveEntity($attachment);

        // Store file
        $this->fileStorageManager->putContents($attachment, $contents);

        return $attachment;
    }

    public function getFileContents(string $attachmentId): ?string
    {
        $attachment = $this->entityManager->getEntityById('Attachment', $attachmentId);

        if (!$attachment) {
            return null;
        }

        return $this->fileStorageManager->getContents($attachment);
    }
}
```

## Custom Entry Points

Entry points are public endpoints (no authentication required).

```php
<?php
namespace Espo\Modules\MyModule\EntryPoints;

use Espo\Core\EntryPoint\EntryPoint;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;

class PublicDownload implements EntryPoint
{
    public function run(Request $request, Response $response): void
    {
        $id = $request->getQueryParam('id');

        if (!$id) {
            $response->setStatus(400);
            return;
        }

        // Fetch file
        $attachment = $this->entityManager->getEntityById('Attachment', $id);

        if (!$attachment || !$attachment->get('isPublic')) {
            $response->setStatus(404);
            return;
        }

        // Serve file
        $contents = $this->fileStorageManager->getContents($attachment);

        $response->setHeader('Content-Type', $attachment->get('type'));
        $response->setHeader('Content-Disposition', 'attachment; filename="' . $attachment->get('name') . '"');
        $response->writeBody($contents);
    }
}
```

Register in metadata (`app/entryPoints.json`):
```json
{
    "publicDownload": {
        "className": "Espo\\Modules\\MyModule\\EntryPoints\\PublicDownload"
    }
}
```

Access via: `?entryPoint=publicDownload&id=ATTACHMENT_ID`
