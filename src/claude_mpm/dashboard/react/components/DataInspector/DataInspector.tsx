import React, { useState, useMemo } from 'react';
import styles from './DataInspector.module.css';

interface DataInspectorProps {
  data: any;
  maxHeight?: string;
  searchable?: boolean;
}

interface TreeNode {
  key: string;
  value: any;
  type: 'object' | 'array' | 'string' | 'number' | 'boolean' | 'null' | 'undefined';
  children?: TreeNode[];
  path: string;
  level: number;
}

function getValueType(value: any): TreeNode['type'] {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (Array.isArray(value)) return 'array';
  return typeof value as TreeNode['type'];
}

function buildTree(data: any, path: string = '', level: number = 0): TreeNode[] {
  if (data === null || data === undefined || typeof data !== 'object') {
    return [];
  }

  const nodes: TreeNode[] = [];

  Object.entries(data).forEach(([key, value]) => {
    const currentPath = path ? `${path}.${key}` : key;
    const type = getValueType(value);

    const node: TreeNode = {
      key,
      value,
      type,
      path: currentPath,
      level,
      children: type === 'object' || type === 'array' ? buildTree(value, currentPath, level + 1) : undefined
    };

    nodes.push(node);
  });

  return nodes;
}

function formatValue(value: any, type: TreeNode['type']): string {
  switch (type) {
    case 'string':
      return `"${value}"`;
    case 'number':
      return String(value);
    case 'boolean':
      return String(value);
    case 'null':
      return 'null';
    case 'undefined':
      return 'undefined';
    case 'array':
      return `Array(${value.length})`;
    case 'object':
      const keys = Object.keys(value || {});
      return `Object(${keys.length})`;
    default:
      return String(value);
  }
}

function TreeNodeComponent({ node, expandedPaths, onToggle, searchTerm }: {
  node: TreeNode;
  expandedPaths: Set<string>;
  onToggle: (path: string) => void;
  searchTerm: string;
}) {
  const isExpanded = expandedPaths.has(node.path);
  const hasChildren = node.children && node.children.length > 0;
  const isExpandable = node.type === 'object' || node.type === 'array';

  // Highlight search matches
  const highlightText = (text: string) => {
    if (!searchTerm) return text;
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    const parts = text.split(regex);
    return parts.map((part, index) =>
      regex.test(part) ? (
        <span key={index} className={styles.highlight}>{part}</span>
      ) : part
    );
  };

  const handleClick = () => {
    if (isExpandable) {
      onToggle(node.path);
    }
  };

  const handleCopy = () => {
    const textToCopy = typeof node.value === 'object'
      ? JSON.stringify(node.value, null, 2)
      : String(node.value);
    navigator.clipboard.writeText(textToCopy);
  };

  return (
    <div className={styles.treeNode} style={{ paddingLeft: `${node.level * 20}px` }}>
      <div className={styles.nodeHeader} onClick={handleClick}>
        {isExpandable && (
          <span className={`${styles.expandIcon} ${isExpanded ? styles.expanded : ''}`}>
            ▶
          </span>
        )}
        {!isExpandable && <span className={styles.leafIcon}>•</span>}

        <span className={styles.nodeKey}>
          {highlightText(node.key)}:
        </span>

        <span className={`${styles.nodeValue} ${styles[node.type]}`}>
          {highlightText(formatValue(node.value, node.type))}
        </span>

        <button
          className={styles.copyButton}
          onClick={(e) => {
            e.stopPropagation();
            handleCopy();
          }}
          title="Copy value"
        >
          📋
        </button>
      </div>

      {isExpanded && hasChildren && (
        <div className={styles.nodeChildren}>
          {node.children!.map((child, index) => (
            <TreeNodeComponent
              key={`${child.path}-${index}`}
              node={child}
              expandedPaths={expandedPaths}
              onToggle={onToggle}
              searchTerm={searchTerm}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function DataInspector({
  data,
  maxHeight = '300px',
  searchable = true
}: DataInspectorProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set(['root']));
  const [searchTerm, setSearchTerm] = useState('');

  const tree = useMemo(() => buildTree(data), [data]);

  const filteredTree = useMemo(() => {
    if (!searchTerm) return tree;

    const filter = (nodes: TreeNode[]): TreeNode[] => {
      return nodes.filter(node => {
        const matchesKey = node.key.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesValue = String(node.value).toLowerCase().includes(searchTerm.toLowerCase());
        const hasMatchingChildren = node.children && filter(node.children).length > 0;

        if (matchesKey || matchesValue || hasMatchingChildren) {
          // Auto-expand paths that contain matches
          setExpandedPaths(prev => new Set([...prev, node.path]));
          return true;
        }

        return false;
      }).map(node => ({
        ...node,
        children: node.children ? filter(node.children) : undefined
      }));
    };

    return filter(tree);
  }, [tree, searchTerm]);

  const togglePath = (path: string) => {
    setExpandedPaths(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const expandAll = () => {
    const getAllPaths = (nodes: TreeNode[]): string[] => {
      const paths: string[] = [];
      nodes.forEach(node => {
        paths.push(node.path);
        if (node.children) {
          paths.push(...getAllPaths(node.children));
        }
      });
      return paths;
    };

    setExpandedPaths(new Set(getAllPaths(tree)));
  };

  const collapseAll = () => {
    setExpandedPaths(new Set());
  };

  const copyAll = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
  };

  return (
    <div className={styles.dataInspector}>
      {searchable && (
        <div className={styles.inspectorHeader}>
          <input
            type="text"
            placeholder="Search in data..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={styles.searchInput}
          />
          <div className={styles.actions}>
            <button onClick={expandAll} className={styles.actionButton}>
              Expand All
            </button>
            <button onClick={collapseAll} className={styles.actionButton}>
              Collapse All
            </button>
            <button onClick={copyAll} className={styles.actionButton}>
              Copy All
            </button>
          </div>
        </div>
      )}

      <div
        className={styles.treeContainer}
        style={{ maxHeight }}
      >
        {filteredTree.length > 0 ? (
          filteredTree.map((node, index) => (
            <TreeNodeComponent
              key={`${node.path}-${index}`}
              node={node}
              expandedPaths={expandedPaths}
              onToggle={togglePath}
              searchTerm={searchTerm}
            />
          ))
        ) : (
          <div className={styles.noData}>
            {searchTerm ? 'No matching data found' : 'No data to display'}
          </div>
        )}
      </div>
    </div>
  );
}