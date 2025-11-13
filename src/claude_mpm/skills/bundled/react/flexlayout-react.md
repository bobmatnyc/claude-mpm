---
name: flexlayout-react
description: FlexLayout for React - Advanced docking layout manager with drag-and-drop, tabs, splitters, and complex window management
version: 1.0.0
category: development
author: Claude MPM Team
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Professional docking layout system: drag-and-drop panels, tabs, splitters, persistence, complex multi-pane interfaces"
    when_to_use: "Building IDE-like interfaces, dashboard builders, multi-document editors, complex admin panels with draggable panes"
    quick_start: "1. Create model with Model.fromJson() 2. Wrap app in Layout component 3. Define factory function 4. Persist with model.toJson()"
context_limit: 700
tags:
  - react
  - layout
  - docking
  - drag-drop
  - ide
  - dashboard
  - flexlayout
requires_tools: []
---

# FlexLayout-React - Professional Docking Layouts

## Overview

FlexLayout-React provides IDE-quality docking layouts with drag-and-drop, tabs, splitters, and complex window management. Perfect for dashboards, IDEs, admin panels, and any interface requiring flexible, user-customizable layouts.

**Key Features**:
- Drag-and-drop panel repositioning
- Tabbed interfaces with close, maximize, minimize
- Splitters for resizable panes
- Border docking areas
- Layout persistence (save/restore)
- Programmatic layout control
- TypeScript support

**Installation**:
```bash
npm install flexlayout-react
```

## Basic Setup

### 1. Define Layout Model

```typescript
import { Model, IJsonModel } from 'flexlayout-react';

const initialLayout: IJsonModel = {
    global: {
        tabEnableClose: true,
        tabEnableRename: false,
    },
    borders: [],
    layout: {
        type: 'row',
        weight: 100,
        children: [
            {
                type: 'tabset',
                weight: 50,
                children: [
                    {
                        type: 'tab',
                        name: 'Explorer',
                        component: 'explorer',
                    }
                ]
            },
            {
                type: 'tabset',
                weight: 50,
                children: [
                    {
                        type: 'tab',
                        name: 'Editor',
                        component: 'editor',
                    }
                ]
            }
        ]
    }
};

// Create model
const model = Model.fromJson(initialLayout);
```

### 2. Create Layout Component

```typescript
import React, { useRef } from 'react';
import { Layout, Model, TabNode, IJsonTabNode } from 'flexlayout-react';
import 'flexlayout-react/style/dark.css';  // or light.css

interface ComponentRegistry {
    explorer: React.ComponentType;
    editor: React.ComponentType;
    terminal: React.ComponentType;
}

function App() {
    const modelRef = useRef(Model.fromJson(initialLayout));

    const factory = (node: TabNode) => {
        const component = node.getComponent();

        switch (component) {
            case 'explorer':
                return <ExplorerPanel />;
            case 'editor':
                return <EditorPanel />;
            case 'terminal':
                return <TerminalPanel />;
            default:
                return <div>Unknown component: {component}</div>;
        }
    };

    return (
        <div style={{ width: '100vw', height: '100vh' }}>
            <Layout
                model={modelRef.current}
                factory={factory}
            />
        </div>
    );
}
```

### 3. Component Implementation

```typescript
function ExplorerPanel() {
    return (
        <div className="panel-explorer">
            <h3>File Explorer</h3>
            <ul>
                <li>src/</li>
                <li>public/</li>
                <li>package.json</li>
            </ul>
        </div>
    );
}

function EditorPanel() {
    return (
        <div className="panel-editor">
            <textarea
                style={{ width: '100%', height: '100%' }}
                placeholder="Start typing..."
            />
        </div>
    );
}
```

## Advanced Layout Configurations

### Complex Multi-Pane Layout

```typescript
const complexLayout: IJsonModel = {
    global: {
        tabEnableClose: true,
        tabEnableRename: false,
        tabEnableDrag: true,
        tabEnableFloat: true,
        borderSize: 200,
    },
    borders: [
        {
            type: 'border',
            location: 'left',
            size: 250,
            children: [
                {
                    type: 'tab',
                    name: 'Explorer',
                    component: 'explorer',
                }
            ]
        },
        {
            type: 'border',
            location: 'bottom',
            size: 200,
            children: [
                {
                    type: 'tab',
                    name: 'Terminal',
                    component: 'terminal',
                },
                {
                    type: 'tab',
                    name: 'Output',
                    component: 'output',
                }
            ]
        }
    ],
    layout: {
        type: 'row',
        weight: 100,
        children: [
            {
                type: 'tabset',
                weight: 70,
                children: [
                    {
                        type: 'tab',
                        name: 'Editor 1',
                        component: 'editor',
                    },
                    {
                        type: 'tab',
                        name: 'Editor 2',
                        component: 'editor',
                    }
                ]
            },
            {
                type: 'tabset',
                weight: 30,
                children: [
                    {
                        type: 'tab',
                        name: 'Properties',
                        component: 'properties',
                    },
                    {
                        type: 'tab',
                        name: 'Outline',
                        component: 'outline',
                    }
                ]
            }
        ]
    }
};
```

### Nested Rows and Columns

```typescript
const nestedLayout: IJsonModel = {
    global: {},
    borders: [],
    layout: {
        type: 'row',
        children: [
            {
                type: 'col',
                weight: 50,
                children: [
                    {
                        type: 'tabset',
                        weight: 70,
                        children: [
                            { type: 'tab', name: 'Top Left', component: 'panel-a' }
                        ]
                    },
                    {
                        type: 'tabset',
                        weight: 30,
                        children: [
                            { type: 'tab', name: 'Bottom Left', component: 'panel-b' }
                        ]
                    }
                ]
            },
            {
                type: 'col',
                weight: 50,
                children: [
                    {
                        type: 'tabset',
                        weight: 30,
                        children: [
                            { type: 'tab', name: 'Top Right', component: 'panel-c' }
                        ]
                    },
                    {
                        type: 'tabset',
                        weight: 70,
                        children: [
                            { type: 'tab', name: 'Bottom Right', component: 'panel-d' }
                        ]
                    }
                ]
            }
        ]
    }
};
```

## Layout Persistence

### Save and Restore Layout

```typescript
import { useState, useEffect } from 'react';
import { Model, Actions } from 'flexlayout-react';

function LayoutManager() {
    const [model, setModel] = useState(() => {
        // Load from localStorage
        const saved = localStorage.getItem('layout');
        return saved
            ? Model.fromJson(JSON.parse(saved))
            : Model.fromJson(defaultLayout);
    });

    // Save on model change
    const onModelChange = (newModel: Model) => {
        const json = newModel.toJson();
        localStorage.setItem('layout', JSON.stringify(json));
    };

    return (
        <Layout
            model={model}
            factory={factory}
            onModelChange={onModelChange}
        />
    );
}
```

### Reset to Default Layout

```typescript
function LayoutControls({ model }: { model: Model }) {
    const resetLayout = () => {
        const newModel = Model.fromJson(defaultLayout);
        // Need to replace model reference
        window.location.reload(); // Simple approach
    };

    const saveLayout = () => {
        const json = model.toJson();
        const blob = new Blob([JSON.stringify(json, null, 2)], {
            type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'layout.json';
        a.click();
    };

    return (
        <div className="layout-controls">
            <button onClick={resetLayout}>Reset Layout</button>
            <button onClick={saveLayout}>Export Layout</button>
        </div>
    );
}
```

## Dynamic Tab Management

### Adding Tabs Programmatically

```typescript
import { Actions, DockLocation } from 'flexlayout-react';

function addNewTab(model: Model, tabsetId: string) {
    model.doAction(Actions.addNode(
        {
            type: 'tab',
            name: `New Tab ${Date.now()}`,
            component: 'editor',
        },
        tabsetId,
        DockLocation.CENTER,
        -1
    ));
}

// Add to specific tabset
const addToExplorer = () => {
    addNewTab(model, 'explorer-tabset-id');
};

// Add to active tabset
const addToActive = () => {
    const activeTabset = model.getActiveTabset();
    if (activeTabset) {
        addNewTab(model, activeTabset.getId());
    }
};
```

### Closing Tabs

```typescript
function closeTab(model: Model, tabId: string) {
    model.doAction(Actions.deleteTab(tabId));
}

function closeAllTabs(model: Model) {
    const tabsets = model.getRoot().getChildren();
    tabsets.forEach(tabset => {
        if (tabset.getType() === 'tabset') {
            const tabs = tabset.getChildren();
            tabs.forEach(tab => {
                if (tab.getType() === 'tab') {
                    model.doAction(Actions.deleteTab(tab.getId()));
                }
            });
        }
    });
}
```

## Tab Context and Props

### Passing Data to Components

```typescript
interface EditorTabProps {
    node: TabNode;
}

function EditorTab({ node }: EditorTabProps) {
    const filepath = node.getConfig()?.filepath as string;
    const readonly = node.getConfig()?.readonly as boolean;

    return (
        <div>
            <p>Editing: {filepath}</p>
            <textarea readOnly={readonly} />
        </div>
    );
}

// Factory with data passing
const factory = (node: TabNode) => {
    const component = node.getComponent();

    switch (component) {
        case 'editor':
            return <EditorTab node={node} />;
        default:
            return <div>Unknown</div>;
    }
};

// Create tab with config
const newTab: IJsonTabNode = {
    type: 'tab',
    name: 'my-file.ts',
    component: 'editor',
    config: {
        filepath: '/src/my-file.ts',
        readonly: false,
    }
};
```

### Accessing Tab State

```typescript
function SmartPanel({ node }: { node: TabNode }) {
    const name = node.getName();
    const isActive = node.isSelected();
    const isVisible = node.isVisible();

    return (
        <div className={isActive ? 'active' : 'inactive'}>
            <h3>{name}</h3>
            {isVisible && <p>This tab is visible</p>}
        </div>
    );
}
```

## Styling and Theming

### Custom CSS

```css
/* Override FlexLayout styles */
.flexlayout__layout {
    background: #1e1e1e;
}

.flexlayout__tab {
    background: #2d2d2d;
    color: #cccccc;
}

.flexlayout__tab:hover {
    background: #3e3e3e;
}

.flexlayout__tab_button--selected {
    background: #1e1e1e;
    border-bottom: 2px solid #007acc;
}

.flexlayout__splitter {
    background: #2d2d2d;
}

.flexlayout__splitter:hover {
    background: #007acc;
}
```

### Dark/Light Theme Toggle

```typescript
import 'flexlayout-react/style/dark.css';
// or
import 'flexlayout-react/style/light.css';

function ThemeToggle() {
    const [theme, setTheme] = useState<'dark' | 'light'>('dark');

    useEffect(() => {
        // Dynamically load theme
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = `flexlayout-react/style/${theme}.css`;
        document.head.appendChild(link);

        return () => {
            document.head.removeChild(link);
        };
    }, [theme]);

    return (
        <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            Toggle Theme
        </button>
    );
}
```

## Integration with Tauri

### Persisting Layout to Tauri Backend

```typescript
import { invoke } from '@tauri-apps/api/core';

async function saveLayoutToTauri(model: Model) {
    const json = model.toJson();
    await invoke('save_layout', {
        layout: JSON.stringify(json)
    });
}

async function loadLayoutFromTauri(): Promise<Model> {
    const layout = await invoke<string>('load_layout');
    return Model.fromJson(JSON.parse(layout));
}

// Tauri command (Rust)
// #[tauri::command]
// async fn save_layout(layout: String) -> Result<(), String> {
//     let app_dir = app.path_resolver().app_data_dir()?;
//     let layout_file = app_dir.join("layout.json");
//     tokio::fs::write(layout_file, layout).await?;
//     Ok(())
// }
```

### Window-Specific Layouts

```typescript
import { invoke } from '@tauri-apps/api/core';
import { getCurrent } from '@tauri-apps/api/window';

function WindowLayout() {
    const [model, setModel] = useState<Model | null>(null);

    useEffect(() => {
        const currentWindow = getCurrent();
        const windowLabel = currentWindow.label;

        // Load layout for this specific window
        invoke<string>('load_window_layout', { windowLabel })
            .then(layout => {
                setModel(Model.fromJson(JSON.parse(layout)));
            })
            .catch(() => {
                setModel(Model.fromJson(defaultLayout));
            });
    }, []);

    const onModelChange = (newModel: Model) => {
        const currentWindow = getCurrent();
        const json = newModel.toJson();

        invoke('save_window_layout', {
            windowLabel: currentWindow.label,
            layout: JSON.stringify(json)
        });
    };

    if (!model) return <div>Loading...</div>;

    return (
        <Layout
            model={model}
            factory={factory}
            onModelChange={onModelChange}
        />
    );
}
```

## Advanced Patterns

### Custom Tab Headers

```typescript
import { Layout, Model, TabNode, ITabRenderValues } from 'flexlayout-react';

function App() {
    const onRenderTab = (
        node: TabNode,
        renderValues: ITabRenderValues
    ) => {
        const modified = node.getConfig()?.modified as boolean;

        renderValues.content = (
            <div className="custom-tab-header">
                <span>{node.getName()}</span>
                {modified && <span className="modified-indicator">●</span>}
            </div>
        );
    };

    return (
        <Layout
            model={model}
            factory={factory}
            onRenderTab={onRenderTab}
        />
    );
}
```

### Tab Actions (Custom Buttons)

```typescript
const onRenderTab = (node: TabNode, renderValues: ITabRenderValues) => {
    renderValues.buttons.push(
        <button
            key="save"
            onClick={() => saveTabContent(node)}
            title="Save"
        >
            💾
        </button>
    );

    renderValues.buttons.push(
        <button
            key="duplicate"
            onClick={() => duplicateTab(node)}
            title="Duplicate"
        >
            📋
        </button>
    );
};
```

## Best Practices

1. **Persist layouts** - Save to localStorage or backend for user experience
2. **Use unique component names** - Avoid collisions in factory function
3. **Handle missing components** - Factory should have default case
4. **Memoize factory function** - Prevent unnecessary re-renders
5. **Use config for tab data** - Store tab-specific props in config
6. **Provide reset mechanism** - Users can restore default layout
7. **Test layout changes** - Verify persistence works correctly
8. **Handle edge cases** - Empty tabsets, deleted components
9. **Use borders wisely** - Left/right/top/bottom for tools, main area for content
10. **Optimize large layouts** - Lazy-load components when possible

## Common Pitfalls

❌ **Not memoizing model**:
```typescript
// WRONG - creates new model on every render
function App() {
    const model = Model.fromJson(layout);  // Bad!
    return <Layout model={model} />;
}

// CORRECT
function App() {
    const modelRef = useRef(Model.fromJson(layout));
    return <Layout model={modelRef.current} />;
}
```

❌ **Forgetting CSS import**:
```typescript
// WRONG - layout won't display correctly
import { Layout } from 'flexlayout-react';
// Missing: import 'flexlayout-react/style/dark.css';
```

❌ **Not handling onModelChange**:
```typescript
// WRONG - layout changes not persisted
<Layout model={model} factory={factory} />

// CORRECT
<Layout
    model={model}
    factory={factory}
    onModelChange={saveLayout}
/>
```

## Resources

- **Documentation**: https://github.com/caplin/FlexLayout
- **Examples**: https://rawgit.com/caplin/FlexLayout/demos/demos/index.html
- **TypeScript Types**: Included in package

## Summary

- **FlexLayout** provides IDE-quality docking layouts
- **Model-driven** - Define layout as JSON, control programmatically
- **Persistent** - Save/restore user layouts easily
- **Customizable** - Custom tabs, borders, themes
- **React-friendly** - Hooks, TypeScript support
- **Perfect for** - IDEs, dashboards, admin panels, complex UIs
- **Tauri integration** - Persist to backend, window-specific layouts
