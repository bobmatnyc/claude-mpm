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
    const allFilePaths = new Set<string>();
    const fileTimestamps = new Map<string, string>();

    // Extract file paths from ALL events
    $events.forEach(event => {
      const paths = findFilePathsInObject(event);
      paths.forEach(path => {
        allFilePaths.add(path);
        // Track most recent timestamp for each file
        const timestamp = typeof event.timestamp === 'string'
          ? event.timestamp
          : new Date(event.timestamp).toISOString();

        const existing = fileTimestamps.get(path);
        if (!existing || new Date(timestamp) > new Date(existing)) {
          fileTimestamps.set(path, timestamp);
        }
      });
    });

    console.log('[FILES] Found paths:', allFilePaths.size, Array.from(allFilePaths).slice(0, 10));

    // Convert to FileEntry array for display
    const fileList = Array.from(allFilePaths).map(path => ({
      file_path: path,
      filename: getFilename(path),
      directory: getDirectory(path),
      operations: [], // TODO: populate later if needed
      last_modified: fileTimestamps.get(path) || new Date().toISOString(),
      operation_types: new Set<string>()
    }));

    // Sort by most recently modified
    return fileList.sort((a, b) => {
      const aTime = new Date(a.last_modified).getTime();
      const bTime = new Date(b.last_modified).getTime();
      return bTime - aTime;
    });
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
