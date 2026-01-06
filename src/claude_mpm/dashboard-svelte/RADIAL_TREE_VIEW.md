# Radial Tree View for Modified Files

## Overview
The Files view now includes a radial tree visualization option alongside the traditional table view. This provides a hierarchical visualization of file operations with D3.js.

## Features

### View Toggle
- **📋 Table**: Traditional table view with columns for filename, operation, and timestamp
- **🌳 Tree**: Radial tree visualization showing file hierarchy

### Visual Encoding

#### Node Colors by Operation:
- **Blue** (#3b82f6): Read operations
- **Green** (#22c55e): Write operations
- **Amber** (#f59e0b): Edit operations
- **Gray** (#6b7280): Directory nodes

#### Node Sizes:
- **File nodes**: Larger circles (6px radius)
- **Directory nodes**: Smaller circles (4px radius)

#### Interactive Features:
- **Click**: Select a file (same behavior as table view)
- **Hover**: Enlarge node and show full path tooltip
- **Selected state**: Highlighted with cyan border

### Layout
- **Radial tree layout**: Files arranged in a circular hierarchy
- **Responsive**: Automatically scales to container size
- **Legend**: Bottom-left corner shows operation color key

## Implementation

### File Structure
```
src/lib/
├── components/
│   ├── FilesView.svelte          # Main view with toggle
│   └── FileTreeRadial.svelte     # New radial tree component
└── utils/
    └── file-tree-builder.ts      # Tree data structure builder
```

### Key Components

#### 1. `file-tree-builder.ts`
Converts flat file list to hierarchical tree:
```typescript
buildFileTree(files: TouchedFile[]): FileNode
convertToD3Hierarchy(root: FileNode): d3.HierarchyNode<FileNode>
```

#### 2. `FileTreeRadial.svelte`
D3.js-powered radial tree visualization:
- Uses `d3.tree()` with radial layout
- `d3.linkRadial()` for curved connections
- Reactive updates when files change
- SVG-based rendering

#### 3. `FilesView.svelte` Updates
- Added view mode state: `'table' | 'tree'`
- Toggle buttons in header
- Conditional rendering based on view mode
- Passes filtered files to radial view

## Usage

### For Users
1. Navigate to the Files tab in the dashboard
2. Click the "🌳 Tree" button to switch to radial view
3. Click the "📋 Table" button to return to table view
4. Click any file node to view its contents
5. Hover over nodes to see full path

### For Developers

#### Adding New Features
The radial tree component accepts these props:
```svelte
<FileTreeRadial
  files={filteredFiles}           // Array of TouchedFile
  selectedFile={selectedFile}      // Currently selected file (optional)
  onFileSelect={selectFile}        // Click handler
/>
```

#### Customization
Colors are defined in `file-tree-builder.ts`:
- `getOperationColor()`: Stroke colors
- `getLighterColor()`: Fill colors

Layout parameters in `FileTreeRadial.svelte`:
- `radius`: Tree radius (auto-calculated from container)
- `separation`: Node spacing multiplier
- Node sizes: 6px (files) / 4px (directories)

## Technical Details

### Dependencies
- **d3** (^7.x): Core D3 library for tree layout and SVG rendering
- **@types/d3**: TypeScript definitions

### D3 Functions Used
- `d3.tree()`: Hierarchical tree layout
- `d3.hierarchy()`: Convert data to hierarchy
- `d3.linkRadial()`: Radial link path generator
- `d3.select()`: DOM manipulation

### Performance
- Tree rebuilds reactively when files change (`$effect`)
- Efficient DOM updates via D3's enter/update/exit pattern
- SVG rendering scales well up to ~100 files
- For larger file sets, consider virtualization

## Testing

### Manual Testing Checklist
- [ ] Tree renders with sample files
- [ ] Clicking a file node selects it (cyan highlight)
- [ ] New files animate into the tree smoothly
- [ ] Colors match operation types (read/write/edit)
- [ ] Hover shows tooltip with full path
- [ ] Toggle between table and tree views works
- [ ] Selected file persists across view switches
- [ ] Filename filter affects tree view
- [ ] Stream filter affects tree view
- [ ] Responsive to container resize

### Known Limitations
- Large file lists (>100 files) may cause layout overlap
- Very deep hierarchies may be difficult to read
- Text labels may overlap on small screens

## Future Enhancements
- [ ] Zoom and pan controls
- [ ] Collapsible directory nodes
- [ ] Animation for file additions
- [ ] Search/highlight in tree view
- [ ] Export tree as SVG/PNG
- [ ] Alternative layouts (cluster, partition)
