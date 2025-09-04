# Enhanced Code Viewer

The Enhanced Code Viewer provides a comprehensive D3.js-based tree visualization for exploring project structure and code files with integrated AST (Abstract Syntax Tree) analysis.

## Features

### 🌳 **Interactive Project Tree**
- **Filtered Directory View**: Shows only code files and relevant directories (no gitignored or dot files)
- **D3.js Visualization**: Beautiful tree layout with linear (default) and radial options
- **Lazy Loading**: Directories expand on-demand for better performance
- **Language Filtering**: Filter by Python, JavaScript, TypeScript, and more

### 📄 **File Content Display**
When you click on a file:
1. **Data Viewer Integration**: File information appears in the structured data pane
2. **File Viewer Option**: Notification offers to open full syntax-highlighted viewer
3. **Metadata Display**: Shows file type, size, language, and tree path

### 🧬 **AST Tree Visualization**
For code files (Python, JavaScript, etc.):
1. **Automatic Analysis**: AST parsing happens when you click a code file
2. **Tree Expansion**: File node automatically expands to show code structure
3. **Hierarchical Display**: Classes, functions, and methods shown as child nodes
4. **Complexity Indicators**: Visual indicators for code complexity

## Usage

### Basic Navigation
1. **Open Code Tab**: Click the "🧬 Code" tab in the dashboard
2. **Auto-Discovery**: Project structure loads automatically from working directory
3. **Expand Folders**: Click folder icons to explore subdirectories
4. **View Files**: Click file names to see content and AST

### File Interaction
```
📁 Project Root
├── 📁 src/
│   ├── 📁 claude_mpm/
│   │   ├── 🐍 __init__.py
│   │   ├── 🐍 core.py
│   │   │   ├── 🏛️ CoreManager (class)
│   │   │   ├── ⚡ initialize (function)
│   │   │   └── 🔧 process (method)
│   │   └── 📁 services/
└── 📁 tests/
```

### Controls
- **Language Filter**: Check/uncheck language types in top-left
- **Layout Toggle**: Switch between Tree and Radial layouts
- **Search**: Find specific files or code elements
- **Ignore Patterns**: Customize file filtering

### File Viewer Integration
1. **Click File**: Shows metadata in data viewer
2. **Notification**: Appears offering full file viewer
3. **Full Viewer**: Syntax-highlighted code with copy functionality
4. **AST Elements**: Clickable code structure in tree

## Technical Details

### Supported Languages
- **Python** (🐍): Full AST analysis with classes, functions, methods
- **JavaScript** (📜): Function and class detection
- **TypeScript** (📘): Enhanced type information
- **React** (⚛️): JSX/TSX component analysis
- **Others**: Basic file structure for HTML, CSS, JSON, etc.

### API Integration
- **Directory Listing**: `/api/directory/list` for folder contents
- **File Reading**: `/api/file/read` for file content
- **AST Analysis**: WebSocket events for code parsing
- **Real-time Updates**: Live tree updates during analysis

### Performance Features
- **Lazy Loading**: Only load directories when expanded
- **Caching**: File content and AST results cached
- **Connection Pooling**: Efficient WebSocket communication
- **Debounced Updates**: Smooth UI during rapid interactions

## Configuration

### Language Selection
```javascript
// Default enabled languages
const defaultLanguages = ['python', 'javascript', 'typescript'];

// Available languages
const supportedLanguages = [
    'python', 'javascript', 'typescript', 'jsx', 'tsx',
    'html', 'css', 'json', 'markdown', 'yaml', 'sql'
];
```

### Ignore Patterns
```
# Default ignore patterns
test*, *.spec.js, node_modules, __pycache__, .git, .vscode
```

### Tree Layout Options
- **Linear Tree**: Traditional hierarchical layout (default)
- **Radial Tree**: Circular layout for large projects
- **Auto-sizing**: Responsive to content and screen size

## Troubleshooting

### Common Issues

**Tree Not Loading**
- Check working directory is set correctly
- Verify project contains supported file types
- Check browser console for API errors

**AST Not Expanding**
- Ensure file is a supported code language
- Check language filters are enabled
- Verify file contains parseable code

**File Viewer Not Opening**
- Check file is a text file type
- Verify file permissions and accessibility
- Check browser popup blockers

### Debug Mode
Enable debug logging in browser console:
```javascript
localStorage.setItem('code-tree-debug', 'true');
```

## Integration

### With Other Dashboard Components
- **Event Viewer**: File operations appear in events tab
- **Activity Tree**: Code analysis shows in activity timeline
- **Module Viewer**: File details in structured data pane
- **Working Directory**: Synced with current project path

### API Endpoints
- `GET /api/directory/list?path=<path>` - Directory contents
- `GET /api/file/read?path=<path>` - File content
- WebSocket events for real-time AST analysis

## Future Enhancements

### Planned Features
- **Multi-language AST**: Enhanced support for more languages
- **Code Metrics**: Complexity analysis and quality indicators
- **Search Integration**: Full-text search within files
- **Git Integration**: Show file status and history
- **Collaborative Features**: Multi-user code exploration

### Performance Improvements
- **Virtual Scrolling**: Handle very large directory trees
- **Web Workers**: Background AST parsing
- **Progressive Loading**: Incremental tree building
- **Compression**: Optimized data transfer

---

The Enhanced Code Viewer transforms the dashboard into a powerful code exploration tool, combining project navigation with deep code analysis in an intuitive visual interface.
