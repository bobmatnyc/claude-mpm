/**
 * Files Store
 *
 * Extracts file references from ALL events in the stream.
 * Simplified approach: scan all event data for file paths.
 */

import { writable, derived } from 'svelte/store';
import type { ClaudeEvent } from '$lib/types/events';

export interface FileOperation {
  type: 'Read' | 'Write' | 'Edit' | 'Glob' | 'Grep';
  timestamp: string;
  correlation_id?: string;
  pre_event?: ClaudeEvent;
  post_event?: ClaudeEvent;
  // For Edit operations
  old_string?: string;
  new_string?: string;
  // For Read operations
  content?: string;
  // For Write operations
  written_content?: string;
  // For Grep/Glob
  pattern?: string;
  matches?: number;
}

export interface FileEntry {
  file_path: string;
  filename: string; // basename
  directory: string; // dirname
  operations: FileOperation[];
  last_modified: string; // most recent operation timestamp
  operation_types: Set<string>; // unique operation types
}

/**
 * Recursively find file paths in any object
 */
function findFilePathsInObject(obj: unknown, paths: Set<string> = new Set(), depth = 0): Set<string> {
  // Prevent infinite recursion
  if (depth > 5 || !obj || typeof obj !== 'object') return paths;

  const record = obj as Record<string, unknown>;

  // Check common file path field names
  const filePathFields = ['file_path', 'path', 'filePath', 'filename'];
  for (const field of filePathFields) {
    const value = record[field];
    if (typeof value === 'string' && value.startsWith('/')) {
      paths.add(value);
    }
  }

  // Recurse into nested objects (but not arrays to avoid noise)
  for (const key of Object.keys(record)) {
    const value = record[key];
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      findFilePathsInObject(value, paths, depth + 1);
    }
  }

  return paths;
}

function createFilesStore(eventsStore: ReturnType<typeof writable<ClaudeEvent[]>>) {
  const files = derived(eventsStore, ($events) => {
    console.log('[FILES] Processing events:', $events.length);
    const fileOperationsMap = new Map<string, FileOperation[]>();

    // Extract file operations from events
    $events.forEach(event => {
      const eventData = event.data as Record<string, unknown> | undefined;
      if (!eventData) return;

      const timestamp = typeof event.timestamp === 'string'
        ? event.timestamp
        : new Date(event.timestamp).toISOString();

      // Extract file path
      let filePath: string | undefined;
      if (typeof eventData.file_path === 'string') {
        filePath = eventData.file_path;
      } else if (typeof eventData.path === 'string') {
        filePath = eventData.path;
      }

      if (!filePath) return;

      console.log('[FILES] Found file path:', filePath, 'in event type:', event.type, 'tool:', eventData.tool);

      // Determine operation type
      let operationType: FileOperation['type'] | undefined;
      let operation: FileOperation | undefined;

      // Check for Read operations
      if (event.type === 'post_tool' && eventData.tool === 'Read') {
        const result = eventData.result as Record<string, unknown> | undefined;
        const content = typeof result?.content === 'string' ? result.content : undefined;

        operation = {
          type: 'Read',
          timestamp,
          correlation_id: event.correlation_id,
          content,
          pre_event: event,
          post_event: event
        };
      }
      // Check for Write operations
      else if (event.type === 'pre_tool' && eventData.tool === 'Write') {
        const parameters = eventData.parameters as Record<string, unknown> | undefined;
        const content = typeof parameters?.content === 'string' ? parameters.content : undefined;

        operation = {
          type: 'Write',
          timestamp,
          correlation_id: event.correlation_id,
          written_content: content,
          pre_event: event,
          post_event: event
        };
      }
      // Check for Edit operations
      else if (event.type === 'pre_tool' && eventData.tool === 'Edit') {
        const parameters = eventData.parameters as Record<string, unknown> | undefined;
        const oldString = typeof parameters?.old_string === 'string' ? parameters.old_string : undefined;
        const newString = typeof parameters?.new_string === 'string' ? parameters.new_string : undefined;

        operation = {
          type: 'Edit',
          timestamp,
          correlation_id: event.correlation_id,
          old_string: oldString,
          new_string: newString,
          pre_event: event,
          post_event: event
        };
      }
      // Check for Grep operations
      else if (event.type === 'pre_tool' && eventData.tool === 'Grep') {
        const parameters = eventData.parameters as Record<string, unknown> | undefined;
        const pattern = typeof parameters?.pattern === 'string' ? parameters.pattern : undefined;

        operation = {
          type: 'Grep',
          timestamp,
          correlation_id: event.correlation_id,
          pattern,
          pre_event: event,
          post_event: event
        };
      }
      // Check for Glob operations
      else if (event.type === 'pre_tool' && eventData.tool === 'Glob') {
        const parameters = eventData.parameters as Record<string, unknown> | undefined;
        const pattern = typeof parameters?.pattern === 'string' ? parameters.pattern : undefined;

        operation = {
          type: 'Glob',
          timestamp,
          correlation_id: event.correlation_id,
          pattern,
          pre_event: event,
          post_event: event
        };
      }

      if (operation) {
        const operations = fileOperationsMap.get(filePath) || [];
        operations.push(operation);
        fileOperationsMap.set(filePath, operations);
        console.log('[FILES] Added operation:', operation.type, 'for file:', filePath);
      }
    });

    console.log('[FILES] Total files with operations:', fileOperationsMap.size);
    console.log('[FILES] Files map:', Array.from(fileOperationsMap.keys()));

    // Convert to FileEntry array for display
    const fileList = Array.from(fileOperationsMap.entries()).map(([path, operations]) => {
      // Sort operations by timestamp (most recent first)
      const sortedOps = operations.sort((a, b) => {
        return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      });

      const operationTypes = new Set(operations.map(op => op.type));
      const lastModified = sortedOps[0]?.timestamp || new Date().toISOString();

      return {
        file_path: path,
        filename: getFilename(path),
        directory: getDirectory(path),
        operations: sortedOps,
        last_modified: lastModified,
        operation_types: operationTypes
      };
    });

    // Sort by most recently modified
    const sorted = fileList.sort((a, b) => {
      const aTime = new Date(a.last_modified).getTime();
      const bTime = new Date(b.last_modified).getTime();
      return bTime - aTime;
    });

    console.log('[FILES] Returning sorted file list:', sorted.length, 'files');
    return sorted;
  });

  return files;
}

/**
 * Get filename from path (basename)
 */
function getFilename(path: string): string {
  const parts = path.split('/');
  return parts[parts.length - 1] || path;
}

/**
 * Get directory from path (dirname)
 */
function getDirectory(path: string): string {
  const parts = path.split('/');
  if (parts.length === 1) return '.';
  return parts.slice(0, -1).join('/') || '/';
}

export { createFilesStore };
