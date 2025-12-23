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
  // For Edit operations (extracted from hook events)
  old_string?: string;
  new_string?: string;
  // For Grep/Glob
  pattern?: string;
  matches?: number;
  // Note: File content for Read/Write is fetched from server API, not stored here
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

    // DEBUG: Log first event to see structure
    if ($events.length > 0) {
      console.log('[FILES] First event structure:', JSON.stringify($events[0], null, 2));
    }

    const fileOperationsMap = new Map<string, FileOperation[]>();

    // Extract file operations from events
    $events.forEach((event, index) => {
      console.log(`[FILES] Processing event ${index}:`, {
        type: event.type,
        subtype: event.subtype,
        hasData: !!event.data
      });

      const eventData = event.data as Record<string, unknown> | undefined;
      if (!eventData) {
        console.log(`[FILES] Event ${index}: No event data, skipping`);
        return;
      }

      const timestamp = typeof event.timestamp === 'string'
        ? event.timestamp
        : new Date(event.timestamp).toISOString();

      // Extract hook_input_data (hook event structure from backend)
      const hookInputData = eventData.hook_input_data &&
                            typeof eventData.hook_input_data === 'object' &&
                            !Array.isArray(eventData.hook_input_data)
        ? eventData.hook_input_data as Record<string, unknown>
        : null;

      // Extract params from hook_input_data
      const hookParams = hookInputData?.params &&
                         typeof hookInputData.params === 'object' &&
                         !Array.isArray(hookInputData.params)
        ? hookInputData.params as Record<string, unknown>
        : null;

      // Extract tool_parameters (alternative format)
      const toolParams = eventData.tool_parameters &&
                         typeof eventData.tool_parameters === 'object' &&
                         !Array.isArray(eventData.tool_parameters)
        ? eventData.tool_parameters as Record<string, unknown>
        : null;

      // Extract file path - prioritize tool_parameters (backend sends tool_parameters.file_path)
      const filePath = (
        (eventData.tool_parameters as any)?.file_path ||  // Backend format (PRIORITY 1)
        (eventData.tool_parameters as any)?.path ||
        hookParams?.file_path ||
        hookParams?.path ||
        toolParams?.file_path ||
        toolParams?.path ||
        eventData.file_path ||
        eventData.path
      ) as string | undefined;

      if (!filePath) {
        console.log(`[FILES] Event ${index}: No file path found`);
        return;
      }

      // Get tool name - prioritize direct field (backend sends tool_name directly)
      const toolName = (
        eventData.tool_name ||  // Backend format (PRIORITY 1)
        (hookInputData as any)?.tool_name
      ) as string | undefined;

      // DEBUG: Log detailed extraction info
      console.log(`[FILES] Event ${index}: Found file path:`, {
        filePath,
        eventSubtype: event.subtype,
        toolName,
        hasToolParams: !!toolParams
      });

      // Determine operation type
      let operationType: FileOperation['type'] | undefined;
      let operation: FileOperation | undefined;

      // Check for Read operations
      if (event.type === 'hook' && event.subtype === 'post_tool' && toolName === 'Read') {
        // Read operations: we don't extract content here anymore
        // Content will be fetched from server when user selects the file
        operation = {
          type: 'Read',
          timestamp,
          correlation_id: event.correlation_id,
          pre_event: event,
          post_event: event
        };
      }
      // Check for Write operations
      else if (event.type === 'hook' && event.subtype === 'pre_tool' && toolName === 'Write') {
        // Write operations: content will be fetched from server when user selects the file
        operation = {
          type: 'Write',
          timestamp,
          correlation_id: event.correlation_id,
          pre_event: event,
          post_event: event
        };
      }
      // Check for Edit operations
      else if (event.type === 'hook' && event.subtype === 'pre_tool' && toolName === 'Edit') {
        // Extract from tool_parameters first (backend format)
        const oldString = (
          (eventData.tool_parameters as any)?.old_string ||
          hookParams?.old_string ||
          toolParams?.old_string
        ) as string | undefined;

        const newString = (
          (eventData.tool_parameters as any)?.new_string ||
          hookParams?.new_string ||
          toolParams?.new_string
        ) as string | undefined;

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
      else if (event.type === 'hook' && event.subtype === 'pre_tool' && toolName === 'Grep') {
        // Extract pattern - prioritize tool_parameters (backend format)
        const pattern = (
          (eventData.tool_parameters as any)?.pattern ||
          hookParams?.pattern ||
          toolParams?.pattern
        ) as string | undefined;

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
      else if (event.type === 'hook' && event.subtype === 'pre_tool' && toolName === 'Glob') {
        // Extract pattern - prioritize tool_parameters (backend format)
        const pattern = (
          (eventData.tool_parameters as any)?.pattern ||
          hookParams?.pattern ||
          toolParams?.pattern
        ) as string | undefined;

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
        console.log(`[FILES] Event ${index}: Added operation:`, operation.type, 'for file:', filePath);
      } else {
        console.log(`[FILES] Event ${index}: No operation created for event type:`, event.type, 'tool:', toolName);
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
