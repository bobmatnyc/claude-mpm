# Development Workflow Reference

## Extension Development Setup

### Using ext-template

The official ext-template provides the recommended structure for EspoCRM extensions.

```bash
# Clone the template
git clone https://github.com/espocrm/ext-template.git my-extension
cd my-extension

# Install dependencies
composer install
npm install
```

### Extension Directory Structure (EspoCRM 7.4+)

```
my-extension/
├── src/
│   ├── files/
│   │   └── custom/Espo/Modules/MyModule/
│   │       ├── Resources/
│   │       │   ├── metadata/
│   │       │   │   ├── entityDefs/
│   │       │   │   ├── clientDefs/
│   │       │   │   └── scopes/
│   │       │   └── layouts/
│   │       ├── Services/
│   │       ├── Controllers/
│   │       ├── Repositories/
│   │       ├── Hooks/
│   │       └── Entities/
│   └── scripts/
├── tests/
├── package.json
└── manifest.json
```

### Manifest File

```json
{
    "name": "My Extension",
    "version": "1.0.0",
    "acceptableVersions": [">=7.4.0"],
    "author": "Your Name",
    "description": "Extension description",
    "license": "MIT",
    "releaseDate": "2024-01-01",
    "skipBackup": true
}
```

### Building Extension

```bash
# Build installable package
npm run build

# Output: build/MyExtension-1.0.0.zip
```

## Creating Custom Entities

### Step 1: Entity Definition

Create `src/files/custom/Espo/Modules/MyModule/Resources/metadata/entityDefs/MyEntity.json`:

```json
{
    "fields": {
        "name": {
            "type": "varchar",
            "required": true,
            "maxLength": 255,
            "trim": true,
            "view": "views/fields/varchar"
        },
        "description": {
            "type": "text",
            "rows": 4
        },
        "status": {
            "type": "enum",
            "options": ["New", "In Progress", "Complete", "Cancelled"],
            "default": "New",
            "required": true,
            "audited": true,
            "isSorted": true
        },
        "priority": {
            "type": "enum",
            "options": ["Low", "Normal", "High", "Urgent"],
            "default": "Normal",
            "audited": true
        },
        "dueDate": {
            "type": "date",
            "audited": true
        },
        "assignedUser": {
            "type": "link"
        },
        "account": {
            "type": "link"
        },
        "contacts": {
            "type": "linkMultiple"
        }
    },
    "links": {
        "assignedUser": {
            "type": "belongsTo",
            "entity": "User",
            "foreign": "myEntities"
        },
        "account": {
            "type": "belongsTo",
            "entity": "Account",
            "foreign": "myEntities"
        },
        "contacts": {
            "type": "hasMany",
            "entity": "Contact",
            "foreign": "myEntities",
            "layoutRelationshipsDisabled": true
        },
        "teams": {
            "type": "hasMany",
            "entity": "Team",
            "relationName": "EntityTeam",
            "layoutRelationshipsDisabled": true
        }
    },
    "collection": {
        "orderBy": "createdAt",
        "order": "desc"
    },
    "indexes": {
        "name": {
            "columns": ["name", "deleted"]
        },
        "assignedUser": {
            "columns": ["assignedUserId", "deleted"]
        }
    }
}
```

### Step 2: Scope Definition

Create `src/files/custom/Espo/Modules/MyModule/Resources/metadata/scopes/MyEntity.json`:

```json
{
    "entity": true,
    "object": true,
    "layouts": true,
    "tab": true,
    "acl": true,
    "aclActionList": [
        "create",
        "read",
        "edit",
        "delete",
        "stream"
    ],
    "aclLevelList": [
        "all",
        "team",
        "own",
        "no"
    ],
    "aclPortal": true,
    "aclPortalLevelList": [
        "all",
        "account",
        "contact",
        "own",
        "no"
    ],
    "customizable": true,
    "type": "Base",
    "module": "MyModule",
    "stream": true,
    "activities": true,
    "historyDisabled": false,
    "importable": true,
    "notifications": true,
    "activityStatusList": ["Planned", "Held", "Not Held"]
}
```

### Step 3: Client Definitions

Create `src/files/custom/Espo/Modules/MyModule/Resources/metadata/clientDefs/MyEntity.json`:

```json
{
    "controller": "controllers/record",
    "iconClass": "fas fa-tasks",
    "color": "#6FA8D6",
    "createDisabled": false,
    "dynamicLogic": {
        "fields": {
            "dueDate": {
                "required": {
                    "conditionGroup": [
                        {
                            "type": "equals",
                            "attribute": "status",
                            "value": "In Progress"
                        }
                    ]
                }
            }
        }
    },
    "filterList": [
        "active",
        "completed"
    ],
    "boolFilterList": [
        "onlyMy"
    ],
    "defaultFilterData": {
        "primary": "active"
    },
    "sidePanels": {
        "detail": [
            {
                "name": "activities",
                "label": "Activities",
                "view": "crm:views/record/panels/activities",
                "aclScope": "Activities"
            }
        ]
    }
}
```

### Step 4: Language Translations

Create `src/files/custom/Espo/Modules/MyModule/Resources/i18n/en_US/MyEntity.json`:

```json
{
    "fields": {
        "name": "Name",
        "description": "Description",
        "status": "Status",
        "priority": "Priority",
        "dueDate": "Due Date",
        "assignedUser": "Assigned To",
        "account": "Account",
        "contacts": "Contacts"
    },
    "links": {
        "assignedUser": "Assigned To",
        "account": "Account",
        "contacts": "Contacts"
    },
    "options": {
        "status": {
            "New": "New",
            "In Progress": "In Progress",
            "Complete": "Complete",
            "Cancelled": "Cancelled"
        },
        "priority": {
            "Low": "Low",
            "Normal": "Normal",
            "High": "High",
            "Urgent": "Urgent"
        }
    },
    "labels": {
        "Create MyEntity": "Create MyEntity"
    },
    "presetFilters": {
        "active": "Active",
        "completed": "Completed"
    },
    "boolFilters": {
        "onlyMy": "Only My"
    }
}
```

### Step 5: Service Layer

Create `src/files/custom/Espo/Modules/MyModule/Services/MyEntity.php`:

```php
<?php
namespace Espo\Modules\MyModule\Services;

use Espo\Services\Record;
use Espo\ORM\Entity;

class MyEntity extends Record
{
    protected function beforeCreateEntity(Entity $entity, array $data): void
    {
        parent::beforeCreateEntity($entity, $data);

        // Set default assigned user to creator if not specified
        if (!$entity->get('assignedUserId')) {
            $entity->set('assignedUserId', $this->user->getId());
        }
    }

    protected function beforeUpdateEntity(Entity $entity, array $data): void
    {
        parent::beforeUpdateEntity($entity, $data);

        // Auto-complete when status set to Complete
        if ($entity->isAttributeChanged('status') && $entity->get('status') === 'Complete') {
            $entity->set('completedAt', date('Y-m-d H:i:s'));
        }
    }
}
```

### Step 6: Rebuild Cache

```bash
bin/command rebuild
```

## Creating Custom Fields

### Custom Field Type Definition

Create `src/files/custom/Espo/Modules/MyModule/Resources/metadata/fields/myFieldType.json`:

```json
{
    "params": [
        {
            "name": "required",
            "type": "bool",
            "default": false
        },
        {
            "name": "maxLength",
            "type": "int"
        },
        {
            "name": "customParam",
            "type": "varchar"
        }
    ],
    "view": "custom:views/fields/my-field-type",
    "personalData": false
}
```

### Custom Field Backend

Create `src/files/custom/Espo/Modules/MyModule/Classes/FieldType/MyFieldTypeType.php`:

```php
<?php
namespace Espo\Modules\MyModule\Classes\FieldType;

use Espo\ORM\Entity;
use Espo\ORM\Type\AttributeType;
use Espo\Core\Field\FieldType;

class MyFieldTypeType implements FieldType
{
    public function getAttributeParamList(): array
    {
        return [
            AttributeType::VARCHAR,
        ];
    }

    public function getActualAttributeParamList(Entity $entity, string $field): array
    {
        return [
            AttributeType::VARCHAR,
        ];
    }
}
```

### Custom Field Frontend

Create `client/custom/src/views/fields/my-field-type.js`:

```javascript
define('custom:views/fields/my-field-type', ['views/fields/varchar'], function (Dep) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);

            // Custom setup logic
            this.customParam = this.params.customParam || '';
        },

        afterRender: function () {
            Dep.prototype.afterRender.call(this);

            // Custom rendering logic
        },

        validateRequired: function () {
            if (this.params.required) {
                if (!this.model.get(this.name)) {
                    var msg = this.translate('fieldIsRequired', 'messages')
                        .replace('{field}', this.getLabelText());
                    this.showValidationMessage(msg);
                    return true;
                }
            }
        },

        fetch: function () {
            var data = {};
            data[this.name] = this.$element.val() || null;
            return data;
        }
    });
});
```

## Custom API Endpoints

### Step 1: Define Route

Create `src/files/custom/Espo/Modules/MyModule/Resources/metadata/api.json`:

```json
{
    "routes": [
        {
            "route": "/MyEntity/:id/customAction",
            "method": "post",
            "controller": "MyModule:MyEntity",
            "action": "customAction"
        }
    ]
}
```

### Step 2: Create Controller

Create `src/files/custom/Espo/Modules/MyModule/Controllers/MyEntity.php`:

```php
<?php
namespace Espo\Modules\MyModule\Controllers;

use Espo\Core\Controllers\Record;
use Espo\Core\Api\Request;
use Espo\Core\Api\Response;
use Espo\Core\Exceptions\BadRequest;
use Espo\Core\Exceptions\Forbidden;
use stdClass;

class MyEntity extends Record
{
    public function postActionCustomAction(Request $request, Response $response): stdClass
    {
        $id = $request->getRouteParam('id');

        if (!$id) {
            throw new BadRequest();
        }

        $data = $request->getParsedBody();

        if (!$this->acl->check($this->name, 'edit')) {
            throw new Forbidden();
        }

        // Delegate to service layer
        $service = $this->getRecordService();
        $result = $service->customAction($id, $data);

        return $result->getValueMap();
    }
}
```

### Step 3: Implement Service Method

```php
<?php
namespace Espo\Modules\MyModule\Services;

use Espo\Services\Record;
use Espo\Core\Exceptions\NotFound;
use stdClass;

class MyEntity extends Record
{
    public function customAction(string $id, stdClass $data): object
    {
        $entity = $this->getEntity($id);

        if (!$entity) {
            throw new NotFound();
        }

        // Business logic
        $entity->set('status', $data->status ?? 'In Progress');
        $entity->set('processedAt', date('Y-m-d H:i:s'));

        $this->entityManager->saveEntity($entity);

        return $entity;
    }
}
```

### Step 4: Call from Frontend

```javascript
this.ajaxPostRequest('MyEntity/' + id + '/customAction', {
    status: 'Complete'
}).then(response => {
    console.log('Action completed', response);
    this.model.set(response);
});
```

## Custom Repositories

### Creating Custom Repository

Create `src/files/custom/Espo/Modules/MyModule/Repositories/MyEntity.php`:

```php
<?php
namespace Espo\Modules\MyModule\Repositories;

use Espo\Core\Repositories\Database;
use Espo\ORM\Entity;

class MyEntity extends Database
{
    protected function beforeSave(Entity $entity, array $options = []): void
    {
        parent::beforeSave($entity, $options);

        // Repository-level validation or data transformation
        if ($entity->isNew()) {
            $entity->set('customIdentifier', $this->generateIdentifier());
        }
    }

    private function generateIdentifier(): string
    {
        // Generate unique identifier
        $prefix = 'ME-';
        $number = $this->getNewNumber();
        return $prefix . str_pad($number, 6, '0', STR_PAD_LEFT);
    }

    private function getNewNumber(): int
    {
        $query = $this->entityManager
            ->getQueryBuilder()
            ->select()
            ->from('MyEntity')
            ->select('COUNT(*) as count')
            ->build();

        $sth = $this->entityManager->getQueryExecutor()->execute($query);
        $row = $sth->fetch();

        return ($row['count'] ?? 0) + 1;
    }

    public function findActive(): \Espo\ORM\Collection
    {
        return $this->where([
            'status!=' => ['Complete', 'Cancelled']
        ])->find();
    }
}
```

## Layouts

### List Layout

Create `src/files/custom/Espo/Modules/MyModule/Resources/layouts/MyEntity/list.json`:

```json
[
    {
        "name": "name",
        "width": "30"
    },
    {
        "name": "status",
        "width": "15"
    },
    {
        "name": "priority",
        "width": "15"
    },
    {
        "name": "assignedUser",
        "width": "15"
    },
    {
        "name": "dueDate",
        "width": "15"
    },
    {
        "name": "createdAt",
        "width": "10"
    }
]
```

### Detail Layout

Create `src/files/custom/Espo/Modules/MyModule/Resources/layouts/MyEntity/detail.json`:

```json
[
    {
        "label": "Overview",
        "rows": [
            [
                {"name": "name"},
                {"name": "status"}
            ],
            [
                {"name": "assignedUser"},
                {"name": "priority"}
            ],
            [
                {"name": "account"},
                {"name": "dueDate"}
            ],
            [
                {"name": "description", "fullWidth": true}
            ]
        ]
    },
    {
        "label": "Contacts",
        "rows": [
            [
                {"name": "contacts", "fullWidth": true}
            ]
        ]
    }
]
```

## Development Best Practices

### Cache Rebuild Workflow

```bash
# After any metadata changes
bin/command rebuild

# Clear cache only (faster, but may miss some changes)
bin/command clear-cache

# Hard rebuild (if issues persist)
rm -rf data/cache/*
bin/command rebuild
```

### Testing Extension Installation

```bash
# Build extension
npm run build

# Install in test EspoCRM instance
# Administration > Extensions > Upload
# Upload build/MyExtension-1.0.0.zip

# After changes, rebuild extension and reinstall
npm run build
# Uninstall old version via Administration > Extensions
# Install new version
```

### Version Compatibility

```php
// Check EspoCRM version in code
$version = $this->config->get('version');

if (version_compare($version, '8.0.0', '>=')) {
    // EspoCRM 8.0+ features
}

// Use version-specific metadata
// For EspoCRM 7.x
custom/Espo/Modules/MyModule/Resources/metadata/entityDefs/MyEntity.json

// For EspoCRM 8.x+
custom/Espo/Modules/MyModule/Resources/metadata/entityDefs/MyEntity/MyEntity.json
```

### Debugging Development Issues

```bash
# Enable debug mode
# data/config.php
'logger' => [
    'level' => 'DEBUG',
],

# Check logs
tail -f data/logs/espo-$(date +%Y-%m-%d).log

# Check for PHP errors
tail -f /var/log/apache2/error.log  # or nginx error log
```

### Module Dependencies

```json
// In manifest.json
{
    "dependencies": {
        "Advanced Pack": {
            "version": ">=2.14.0"
        }
    }
}
```
