# Frontend Customization Reference

## EspoCRM View System

EspoCRM uses a custom View architecture (not Backbone.View or Knockout). Views follow a specific lifecycle and pattern.

### View Lifecycle

```
constructor → setup() → afterRender() → user interaction → onRemove()
```

### Basic View Structure

```javascript
define('custom:views/my-custom-view', ['view'], function (Dep) {

    return Dep.extend({

        // Template path (optional)
        template: 'custom:my-custom-view',

        // Events (optional)
        events: {
            'click [data-action="save"]': function (e) {
                this.actionSave();
            },
            'change input[name="status"]': function (e) {
                this.handleStatusChange(e);
            }
        },

        // Data for template
        data: function () {
            return {
                name: this.model.get('name'),
                status: this.model.get('status'),
                customValue: this.options.customValue
            };
        },

        // Setup (called before rendering)
        setup: function () {
            Dep.prototype.setup.call(this);

            // Initialize properties
            this.customProperty = this.options.customProperty || 'default';

            // Listen to model changes
            this.listenTo(this.model, 'change:status', function () {
                this.reRender();
            });

            // Create child views
            this.createView('myChild', 'custom:views/my-child-view', {
                el: this.getSelector() + ' .child-container',
                model: this.model
            });
        },

        // After render (DOM is ready)
        afterRender: function () {
            Dep.prototype.afterRender.call(this);

            // DOM manipulation
            this.$el.find('.my-element').addClass('active');

            // Initialize plugins
            this.$el.find('[data-toggle="tooltip"]').tooltip();

            // Fetch data
            this.loadAdditionalData();
        },

        // Cleanup (called when view is removed)
        onRemove: function () {
            Dep.prototype.onRemove.call(this);

            // Cleanup listeners, timers, etc.
            if (this.intervalId) {
                clearInterval(this.intervalId);
            }
        },

        // Custom methods
        actionSave: function () {
            var data = {
                name: this.$el.find('[name="name"]').val(),
                status: this.$el.find('[name="status"]').val()
            };

            this.model.save(data, {
                patch: true
            }).then(function () {
                Espo.Ui.success(this.translate('Saved'));
            }.bind(this));
        },

        handleStatusChange: function (e) {
            var status = $(e.currentTarget).val();
            console.log('Status changed to:', status);
        },

        loadAdditionalData: function () {
            this.ajaxGetRequest('MyEntity/' + this.model.id + '/additionalData')
                .then(function (response) {
                    this.additionalData = response;
                    this.reRender();
                }.bind(this));
        }
    });
});
```

## Custom Record Views

### Detail View Customization

```javascript
define('custom:views/account/record/detail', ['views/record/detail'], function (Dep) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);

            // Add custom button
            this.addButton({
                name: 'customAction',
                label: 'Custom Action',
                style: 'primary'
            });

            // Add dropdown action
            this.addDropdownItem({
                name: 'exportToPdf',
                label: 'Export to PDF',
                action: 'exportToPdf'
            });

            // Hide default button
            this.removeButton('delete');
        },

        actionCustomAction: function () {
            // Button clicked
            this.confirm(this.translate('Are you sure?'), function () {
                this.performCustomAction();
            }, this);
        },

        performCustomAction: function () {
            Espo.Ui.notify(this.translate('Loading...'));

            this.ajaxPostRequest('Account/' + this.model.id + '/customAction', {
                param: 'value'
            }).then(function (response) {
                Espo.Ui.success(this.translate('Done'));
                this.model.fetch();
            }.bind(this));
        },

        actionExportToPdf: function () {
            window.open('?entryPoint=download&id=' + this.model.id, '_blank');
        }
    });
});
```

### Edit View Customization

```javascript
define('custom:views/opportunity/record/edit', ['views/record/edit'], function (Dep) {

    return Dep.extend({

        setup: function () {
            Dep.prototype.setup.call(this);

            // Dynamic field logic
            this.controlFieldVisibility();

            // Listen for field changes
            this.listenTo(this.model, 'change:stage', function () {
                this.controlFieldVisibility();
            }, this);
        },

        controlFieldVisibility: function () {
            var stage = this.model.get('stage');

            if (stage === 'Closed Won') {
                this.showField('closeDate');
                this.setFieldRequired('closeDate');
            } else {
                this.hideField('closeDate');
                this.setFieldNotRequired('closeDate');
            }
        },

        // Override save to add custom logic
        save: function () {
            // Custom validation
            var amount = this.model.get('amount');
            if (amount > 1000000) {
                this.notify('Please get manager approval for deals over $1M', 'warning');
                return Promise.reject();
            }

            // Call parent save
            return Dep.prototype.save.call(this);
        }
    });
});
```

### List View Customization

```javascript
define('custom:views/account/record/list', ['views/record/list'], function (Dep) {

    return Dep.extend({

        // Add mass action
        massActionList: Dep.prototype.massActionList.concat([
            'exportToExcel',
            'sendEmail'
        ]),

        setup: function () {
            Dep.prototype.setup.call(this);

            // Add custom row action
            this.addRowAction('viewWebsite', {
                label: 'View Website',
                action: 'viewWebsite'
            });
        },

        // Handle mass action
        massActionExportToExcel: function () {
            var ids = this.getSelected();

            this.ajaxPostRequest('Account/action/exportToExcel', {
                ids: ids
            }).then(function (response) {
                window.location = response.downloadUrl;
            });
        },

        // Handle row action
        actionViewWebsite: function (data) {
            var model = this.collection.get(data.id);
            var website = model.get('website');

            if (website) {
                window.open(website, '_blank');
            }
        }
    });
});
```

## Custom Field Views

### Creating Custom Field View

```javascript
define('custom:views/fields/color-picker', ['views/fields/varchar'], function (Dep) {

    return Dep.extend({

        // Detail mode template
        detailTemplate: 'custom:fields/color-picker/detail',

        // Edit mode template
        editTemplate: 'custom:fields/color-picker/edit',

        // Events specific to this field
        events: {
            'change input.color-input': function (e) {
                this.trigger('change');
            }
        },

        // Setup
        setup: function () {
            Dep.prototype.setup.call(this);

            this.defaultColor = this.params.defaultColor || '#000000';
        },

        // After render in edit mode
        afterRenderEdit: function () {
            Dep.prototype.afterRenderEdit.call(this);

            // Initialize color picker plugin
            this.$el.find('input.color-input').spectrum({
                preferredFormat: 'hex',
                showInput: true,
                allowEmpty: true
            });
        },

        // Fetch value from DOM
        fetch: function () {
            var value = this.$el.find('input.color-input').val();

            var data = {};
            data[this.name] = value || null;

            return data;
        },

        // Validation
        validateRequired: function () {
            if (this.isRequired()) {
                var value = this.model.get(this.name);

                if (!value) {
                    var msg = this.translate('fieldIsRequired', 'messages')
                        .replace('{field}', this.getLabelText());

                    this.showValidationMessage(msg);
                    return true;
                }
            }
        },

        // Custom validation
        validate: function () {
            if (Dep.prototype.validate.call(this)) {
                return true;
            }

            var value = this.model.get(this.name);

            if (value && !this.isValidHexColor(value)) {
                var msg = 'Invalid color format';
                this.showValidationMessage(msg);
                return true;
            }

            return false;
        },

        isValidHexColor: function (color) {
            return /^#[0-9A-F]{6}$/i.test(color);
        }
    });
});
```

### Field Template (Handlebars)

Detail template (`client/custom/res/templates/fields/color-picker/detail.tpl`):
```handlebars
<div class="color-preview" style="background-color: {{value}}; width: 50px; height: 20px; border: 1px solid #ccc;"></div>
<span>{{value}}</span>
```

Edit template (`client/custom/res/templates/fields/color-picker/edit.tpl`):
```handlebars
<input
    type="text"
    class="form-control color-input"
    name="{{name}}"
    value="{{value}}"
    autocomplete="espo-{{name}}"
>
```

## AJAX Helpers

### Making AJAX Requests

```javascript
// GET request
this.ajaxGetRequest('Account/' + id)
    .then(function (response) {
        console.log(response);
    });

// POST request
this.ajaxPostRequest('Account/action/customAction', {
    param1: 'value1',
    param2: 'value2'
}).then(function (response) {
    console.log(response);
});

// PUT request
this.ajaxPutRequest('Account/' + id, {
    name: 'Updated Name'
}).then(function (response) {
    console.log(response);
});

// DELETE request
this.ajaxDeleteRequest('Account/' + id)
    .then(function () {
        console.log('Deleted');
    });

// With error handling
this.ajaxPostRequest('Account/action/risky', data)
    .then(function (response) {
        Espo.Ui.success('Success');
    })
    .catch(function (xhr) {
        var reason = xhr.responseJSON?.reason || 'Unknown error';
        Espo.Ui.error(reason);
    });
```

## Notifications and Dialogs

### UI Notifications

```javascript
// Success notification
Espo.Ui.success(this.translate('Saved'));

// Error notification
Espo.Ui.error(this.translate('Error occurred'));

// Warning notification
Espo.Ui.warning(this.translate('Please review'));

// Info notification
Espo.Ui.notify(this.translate('Loading...'));

// Remove notification
Espo.Ui.notify(false);
```

### Confirmation Dialogs

```javascript
// Simple confirmation
this.confirm('Are you sure?', function () {
    // User clicked OK
    this.performAction();
}, this);

// Confirmation with translated message
this.confirm(
    this.translate('confirmDeletion', 'messages'),
    function () {
        this.delete();
    },
    this
);
```

### Custom Dialogs

```javascript
// Create dialog view
this.createView('dialog', 'custom:views/modals/my-dialog', {
    model: this.model
}, function (view) {
    view.render();
});

// Dialog with callback
this.createView('dialog', 'views/modals/edit', {
    scope: 'Account',
    id: accountId
}, function (view) {
    view.render();

    this.listenToOnce(view, 'after:save', function () {
        // Dialog saved
        this.model.fetch();
    }, this);
}, this);
```

## Custom Controllers

```javascript
define('custom:controllers/my-entity', ['controllers/record'], function (Dep) {

    return Dep.extend({

        // Default action
        defaultAction: 'list',

        // Custom action
        actionCustomDashboard: function (options) {
            this.main('custom:views/my-entity/dashboard', {
                scope: this.name
            });
        },

        // Before default action
        beforeList: function () {
            Dep.prototype.beforeList.call(this);
            console.log('Before list action');
        },

        // After default action
        afterList: function () {
            Dep.prototype.afterList.call(this);
            console.log('After list action');
        }
    });
});
```

## Working with Models

### Model Operations

```javascript
// Get model value
var name = this.model.get('name');

// Set model value (doesn't save)
this.model.set('name', 'New Name');

// Set multiple values
this.model.set({
    name: 'New Name',
    status: 'Active'
});

// Save model
this.model.save().then(function () {
    Espo.Ui.success('Saved');
});

// Save specific attributes (PATCH)
this.model.save({
    status: 'Complete'
}, {
    patch: true
}).then(function () {
    console.log('Status updated');
});

// Fetch model from server
this.model.fetch().then(function () {
    console.log('Model refreshed');
});

// Delete model
this.model.destroy().then(function () {
    console.log('Deleted');
});

// Check if model is new
if (this.model.isNew()) {
    console.log('New record');
}

// Check if attribute changed
if (this.model.hasChanged('status')) {
    console.log('Status changed');
}

// Get previous value
var previousStatus = this.model.previous('status');
```

### Model Events

```javascript
// Listen to any change
this.listenTo(this.model, 'change', function () {
    console.log('Model changed');
});

// Listen to specific attribute change
this.listenTo(this.model, 'change:status', function (model, value) {
    console.log('Status changed to:', value);
});

// Listen to save
this.listenTo(this.model, 'sync', function () {
    console.log('Model saved');
});

// Listen once
this.listenToOnce(this.model, 'change:status', function () {
    console.log('First status change');
});

// Stop listening
this.stopListening(this.model, 'change:status');
```

## Collections

### Working with Collections

```javascript
// Fetch collection
this.collection.fetch().then(function () {
    console.log('Collection loaded:', this.collection.length);
}.bind(this));

// Iterate collection
this.collection.forEach(function (model) {
    console.log(model.get('name'));
});

// Filter collection
var activeModels = this.collection.filter(function (model) {
    return model.get('status') === 'Active';
});

// Find in collection
var model = this.collection.find(function (model) {
    return model.id === targetId;
});

// Get by ID
var model = this.collection.get(id);

// Collection events
this.listenTo(this.collection, 'sync', function () {
    console.log('Collection synced');
});
```

## Metadata Access

```javascript
// Get entity metadata
var entityDefs = this.getMetadata().get(['entityDefs', 'Account']);

// Get field definitions
var fields = this.getMetadata().get(['entityDefs', 'Account', 'fields']);

// Get specific field metadata
var nameFieldDef = this.getMetadata().get(['entityDefs', 'Account', 'fields', 'name']);

// Get client definitions
var clientDefs = this.getMetadata().get(['clientDefs', 'Account']);

// Check if entity has field
var hasField = this.getMetadata().get(['entityDefs', 'Account', 'fields', 'website']);
```

## Translation

```javascript
// Translate label
var label = this.translate('Account', 'scopeNames');

// Translate with category
var requiredMsg = this.translate('fieldIsRequired', 'messages');

// Translate field label
var nameLabel = this.translate('name', 'fields', 'Account');

// Translate option
var statusLabel = this.translate('Active', 'status', 'Account');

// String replacement
var msg = this.translate('recordSaved', 'messages')
    .replace('{record}', this.model.get('name'));
```

## Best Practices

### 1. Always Call Parent Methods

```javascript
// ✅ CORRECT
setup: function () {
    Dep.prototype.setup.call(this);
    // Your code
}

// ❌ WRONG - Missing parent call
setup: function () {
    // Your code only
}
```

### 2. Proper Cleanup in onRemove

```javascript
// ✅ CORRECT
onRemove: function () {
    Dep.prototype.onRemove.call(this);

    // Cleanup timers
    if (this.interval) {
        clearInterval(this.interval);
    }

    // Cleanup event listeners (automatically done by listenTo)
    // Manual jQuery listeners need cleanup
    $(window).off('resize.myView');
}
```

### 3. Use this.listenTo Instead of model.on

```javascript
// ✅ CORRECT - Auto cleanup
this.listenTo(this.model, 'change', callback);

// ❌ WRONG - Memory leak, manual cleanup needed
this.model.on('change', callback);
```

### 4. Proper Promise Handling

```javascript
// ✅ CORRECT
this.model.save().then(function () {
    Espo.Ui.success('Saved');
}.bind(this)).catch(function () {
    Espo.Ui.error('Error');
}.bind(this));

// ❌ WRONG - Unhandled rejection
this.model.save().then(function () {
    Espo.Ui.success('Saved');
});
```
