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
      // Add type guards to prevent runtime errors when event.data is array/string
      const data = event.data;
      const dataSubtype =
        data && typeof data === 'object' && !Array.isArray(data)
          ? (data as Record<string, unknown>).subtype as string | undefined
          : undefined;
      const eventSubtype = event.subtype || dataSubtype;

      // Only process pre_tool and post_tool events
      if (eventSubtype !== 'pre_tool' && eventSubtype !== 'post_tool') {
        return;
      }

      const toolName =
        data && typeof data === 'object' && !Array.isArray(data)
          ? ((data as Record<string, unknown>).tool_name as string) || 'Unknown'
          : 'Unknown';
      if (!fileTools.has(toolName)) return;

      // Extract file path
      const filePath = extractFilePath(toolName, data);
      if (!filePath) return;

      // Extract correlation ID with type guards
      const dataRecord = data && typeof data === 'object' && !Array.isArray(data)
        ? data as Record<string, unknown>
        : null;
      const correlationId =
        event.correlation_id ||
        (dataRecord?.correlation_id as string) ||
        (dataRecord?.tool_call_id as string);

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

        // Extract operation-specific data with type guards
        if (dataRecord) {
          if (toolName === 'Edit') {
            operation.old_string = dataRecord.old_string as string;
            operation.new_string = dataRecord.new_string as string;
          } else if (toolName === 'Grep' || toolName === 'Glob') {
            operation.pattern = dataRecord.pattern as string;
          }
        }
      } else if (eventSubtype === 'post_tool') {
        operation.post_event = event;

        // Extract results from post event with type guards
        if (dataRecord) {
          if (toolName === 'Read') {
            // Content might be in result or output
            const result = dataRecord.result;
            if (typeof result === 'string') {
              operation.content = result;
            } else if (result && typeof result === 'object' && !Array.isArray(result)) {
              operation.content = (result as Record<string, unknown>).content as string;
            }
          } else if (toolName === 'Write') {
            // For Write, content is in pre_event
            const preData = operation.pre_event?.data;
            if (preData && typeof preData === 'object' && !Array.isArray(preData)) {
              operation.written_content = (preData as Record<string, unknown>).content as string;
            }
          } else if (toolName === 'Grep' || toolName === 'Glob') {
            const result = dataRecord.result;
            if (result && typeof result === 'object' && !Array.isArray(result)) {
              const resultRecord = result as Record<string, unknown>;
              if (resultRecord.matches && Array.isArray(resultRecord.matches)) {
                operation.matches = resultRecord.matches.length;
              }
            }
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
 *
 * NOTE: File paths can be in two locations:
 * 1. Directly in data.file_path (legacy or simplified events)
 * 2. In data.tool_parameters.file_path (standard hook event structure)
 */
function extractFilePath(toolName: string, data: unknown): string | null {
  // Add type guard at function entry
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null;
  }

  const dataRecord = data as Record<string, unknown>;

  // Extract tool_parameters if present (standard hook event structure)
  const toolParams = dataRecord.tool_parameters &&
                     typeof dataRecord.tool_parameters === 'object' &&
                     !Array.isArray(dataRecord.tool_parameters)
    ? dataRecord.tool_parameters as Record<string, unknown>
    : null;

  switch (toolName) {
    case 'Read':
    case 'Write':
    case 'Edit':
      // Check both direct field AND tool_parameters (hook events use tool_parameters)
      return (dataRecord.file_path as string) ||
             (toolParams?.file_path as string) ||
             null;

    case 'Grep':
    case 'Glob':
      // For search tools, use the path parameter (directory searched)
      // Check both direct field AND tool_parameters
      return (dataRecord.path as string) ||
             (toolParams?.path as string) ||
             null;

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
