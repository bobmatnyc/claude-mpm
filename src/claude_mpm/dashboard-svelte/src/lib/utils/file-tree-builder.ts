/**
 * File Tree Builder - Convert flat file list to hierarchical tree for D3
 *
 * WHY: D3's tree layout requires hierarchical data structure.
 * This converts flat file paths into a tree for radial visualization.
 */

import type { TouchedFile } from '$lib/stores/files.svelte';
import * as d3 from 'd3';

export interface FileNode {
  name: string;
  path: string;
  children?: FileNode[];
  operation?: 'read' | 'write' | 'edit';
  timestamp?: string | number;
  isFile: boolean;
  file?: TouchedFile; // Original file data for leaf nodes
}

/**
 * Build hierarchical tree from flat list of files
 */
export function buildFileTree(files: TouchedFile[]): FileNode {
  const root: FileNode = {
    name: 'root',
    path: '/',
    children: [],
    isFile: false
  };

  // Sort files by path for consistent tree structure
  const sortedFiles = [...files].sort((a, b) => a.path.localeCompare(b.path));

  for (const file of sortedFiles) {
    // Split path into segments, filter out empty strings
    const segments = file.path.split('/').filter(Boolean);

    // Navigate/create tree structure
    let current = root;

    for (let i = 0; i < segments.length; i++) {
      const segment = segments[i];
      const isLastSegment = i === segments.length - 1;

      // Build path up to this segment
      const pathSoFar = '/' + segments.slice(0, i + 1).join('/');

      // Find existing child with this name
      if (!current.children) {
        current.children = [];
      }

      let child = current.children.find(c => c.name === segment);

      if (!child) {
        // Create new node
        child = {
          name: segment,
          path: pathSoFar,
          isFile: isLastSegment,
          children: isLastSegment ? undefined : []
        };

        // If this is a file (leaf node), add metadata
        if (isLastSegment) {
          child.operation = file.operation;
          child.timestamp = file.timestamp;
          child.file = file;
        }

        current.children.push(child);
      } else if (isLastSegment) {
        // Update existing leaf with latest operation
        child.operation = file.operation;
        child.timestamp = file.timestamp;
        child.file = file;
      }

      current = child;
    }
  }

  return root;
}

/**
 * Convert FileNode tree to D3 HierarchyNode
 */
export function convertToD3Hierarchy(root: FileNode): d3.HierarchyNode<FileNode> {
  return d3.hierarchy(root, d => d.children);
}

/**
 * Get color for operation type (matches FilesView colors)
 */
export function getOperationColor(operation?: 'read' | 'write' | 'edit'): string {
  switch (operation) {
    case 'read':
      return '#3b82f6'; // blue
    case 'write':
      return '#22c55e'; // green
    case 'edit':
      return '#f59e0b'; // amber
    default:
      return '#6b7280'; // gray (directories)
  }
}

/**
 * Get lighter version of color for fill
 */
export function getLighterColor(operation?: 'read' | 'write' | 'edit'): string {
  switch (operation) {
    case 'read':
      return '#93c5fd'; // blue-300
    case 'write':
      return '#86efac'; // green-300
    case 'edit':
      return '#fcd34d'; // amber-300
    default:
      return '#9ca3af'; // gray-400
  }
}
