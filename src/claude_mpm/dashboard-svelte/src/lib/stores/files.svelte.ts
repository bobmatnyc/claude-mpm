/**
 * Files Store
 *
 * Tracks file operations (Read, Write, Edit, Glob, Grep) from event stream.
 * Consolidates all operations on the same file path into a single FileEntry.
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

function createFilesStore(eventsStore: ReturnType<typeof writable<ClaudeEvent[]>>) {
  const files = derived(eventsStore, ($events) => {
    const fileMap = new Map<string, FileEntry>();

    // File operation tool names
    const fileTools = new Set(['Read', 'Write', 'Edit', 'Glob', 'Grep']);

    // Process all events
    $events.forEach(event => {
      const data = event.data as Record<string, unknown> | null;
      const eventSubtype = event.subtype || (data?.subtype as string);

      // Only process pre_tool and post_tool events
      if (eventSubtype !== 'pre_tool' && eventSubtype !== 'post_tool') {
        return;
      }

      const toolName = (data?.tool_name as string) || 'Unknown';
      if (!fileTools.has(toolName)) return;

      // Extract file path
      const filePath = extractFilePath(toolName, data);
      if (!filePath) return;

      // Extract correlation ID
      const correlationId =
        event.correlation_id ||
        (data?.correlation_id as string) ||
        (data?.tool_call_id as string);

      // Get or create file entry
      let fileEntry = fileMap.get(filePath);
      if (!fileEntry) {
        fileEntry = {
          file_path: filePath,
          filename: getFilename(filePath),
          directory: getDirectory(filePath),
          operations: [],
          last_modified: typeof event.timestamp === 'string'
            ? event.timestamp
            : new Date(event.timestamp).toISOString(),
          operation_types: new Set()
        };
        fileMap.set(filePath, fileEntry);
      }

      // Find or create operation for this correlation_id
      const operationKey = correlationId || `${toolName}_${event.timestamp}`;
      let operation = fileEntry.operations.find(op => op.correlation_id === operationKey);

      if (!operation) {
        operation = {
          type: toolName as 'Read' | 'Write' | 'Edit' | 'Glob' | 'Grep',
          timestamp: typeof event.timestamp === 'string'
            ? event.timestamp
            : new Date(event.timestamp).toISOString(),
          correlation_id: operationKey
        };
        fileEntry.operations.push(operation);
        fileEntry.operation_types.add(toolName);
      }

      // Store pre/post events
      if (eventSubtype === 'pre_tool') {
        operation.pre_event = event;

        // Extract operation-specific data
        if (toolName === 'Edit') {
          operation.old_string = data?.old_string as string;
          operation.new_string = data?.new_string as string;
        } else if (toolName === 'Grep' || toolName === 'Glob') {
          operation.pattern = data?.pattern as string;
        }
      } else if (eventSubtype === 'post_tool') {
        operation.post_event = event;

        // Extract results from post event
        if (toolName === 'Read') {
          // Content might be in result or output
          const result = data?.result as Record<string, unknown> | string | null;
          if (typeof result === 'string') {
            operation.content = result;
          } else if (result && typeof result === 'object') {
            operation.content = result.content as string;
          }
        } else if (toolName === 'Write') {
          // For Write, content is in pre_event
          const preData = operation.pre_event?.data as Record<string, unknown> | null;
          operation.written_content = preData?.content as string;
        } else if (toolName === 'Grep' || toolName === 'Glob') {
          const result = data?.result as Record<string, unknown> | null;
          if (result?.matches) {
            operation.matches = (result.matches as any[]).length;
          }
        }
      }

      // Update last_modified to most recent operation
      const opTime = new Date(operation.timestamp).getTime();
      const currentTime = new Date(fileEntry.last_modified).getTime();
      if (opTime > currentTime) {
        fileEntry.last_modified = operation.timestamp;
      }
    });

    // Convert to sorted array (most recently modified first)
    return Array.from(fileMap.values()).sort((a, b) => {
      const aTime = new Date(a.last_modified).getTime();
      const bTime = new Date(b.last_modified).getTime();
      return bTime - aTime;
    });
  });

  return files;
}

/**
 * Extract file path from tool data
 */
function extractFilePath(toolName: string, data: Record<string, unknown> | null): string | null {
  if (!data) return null;

  switch (toolName) {
    case 'Read':
    case 'Write':
    case 'Edit':
      return data.file_path as string;

    case 'Grep':
    case 'Glob':
      // For search tools, use the path parameter (directory searched)
      return data.path as string || null;

    default:
      return null;
  }
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
