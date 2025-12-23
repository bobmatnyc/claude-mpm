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

    // DEBUG: Log first event to see structure
    if ($events.length > 0) {
      console.log('[FILES] First event structure:', JSON.stringify($events[0], null, 2));
    }

    const fileOperationsMap = new Map<string, FileOperation[]>();

    // Extract file operations from events
    $events.forEach((event, index) => {
      // 🔴 RAW EVENT LOGGING - Debug content extraction
      console.log('🔴 RAW EVENT:', JSON.stringify(event, null, 2));
      console.log('🔴 EVENT KEYS:', Object.keys(event));
      console.log('🔴 EVENT.DATA:', event.data);
      console.log('🔴 EVENT.DATA KEYS:', event.data ? Object.keys(event.data) : 'no data');
      console.log('🔴 EVENT.TYPE:', event.type);
      console.log('🔴 EVENT.SUBTYPE:', event.subtype);

      console.log(`[FILES] Event ${index}:`, {
        type: event.type,
        hasData: !!event.data,
        dataKeys: event.data ? Object.keys(event.data as any) : []
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
      // Backend emits events as 'claude_event' with type='hook' and subtype='post_tool'
      if (event.type === 'hook' && event.subtype === 'post_tool' && toolName === 'Read') {
        // Extract content from output field
        // Backend structure: { data: { output: "content", tool_name: "Read", tool_parameters: {...} } }
        // CRITICAL: The event structure from SSE might wrap the data

        // 🔴 DEBUG: Check if event.data.data exists (nested wrapping)
        console.log('🔴 CHECKING NESTED DATA:');
        console.log('🔴 eventData.data exists?', !!eventData.data);
        console.log('🔴 eventData.data type:', typeof eventData.data);
        if (eventData.data && typeof eventData.data === 'object') {
          console.log('🔴 eventData.data keys:', Object.keys(eventData.data));
          console.log('🔴 eventData.data.output?', (eventData.data as any).output);
        }

        // Try to unwrap if event.data is the actual payload
        const actualEventData = eventData.data && typeof eventData.data === 'object'
          ? eventData.data as Record<string, unknown>
          : eventData;

        console.log('🔴 actualEventData === eventData?', actualEventData === eventData);
        console.log('🔴 actualEventData.output type:', typeof actualEventData.output);

        const content = (
          // PRIORITY 1: Check actualEventData.output (unwrapped from event.data.data.output)
          typeof actualEventData.output === 'string' ? actualEventData.output :
          // PRIORITY 2: Check eventData.output (direct format from backend)
          typeof eventData.output === 'string' ? eventData.output :
          // Check eventData.result (alternative format)
          typeof eventData.result === 'string' ? eventData.result :
          // Check for nested data.output (shouldn't be needed but defensive)
          typeof (eventData.data as any)?.output === 'string' ? (eventData.data as any).output :
          // Check hook_output_data (alternative backend format)
          typeof eventData.hook_output_data === 'string' ? eventData.hook_output_data :
          // Check return_value (yet another backend format)
          typeof eventData.return_value === 'string' ? eventData.return_value :
          undefined
        );

        // Enhanced debug logging to help diagnose content extraction
        console.log(`[FILES] Read operation for ${filePath}:`, {
          hasContent: !!content,
          contentLength: content?.length,
          contentPreview: content ? content.substring(0, 100) : null,
          eventDataKeys: Object.keys(eventData),
          eventDataOutput: {
            exists: 'output' in eventData,
            type: typeof eventData.output,
            isString: typeof eventData.output === 'string',
            lengthIfString: typeof eventData.output === 'string' ? (eventData.output as string).length : 0
          },
          // CRITICAL: Log ALL possible content fields
          allPossibleContentFields: {
            output: typeof eventData.output,
            result: typeof eventData.result,
            hook_output_data: typeof eventData.hook_output_data,
            return_value: typeof eventData.return_value,
            data_output: typeof (eventData.data as any)?.output
          }
        });

        // ALWAYS store the operation, even without content (will fallback to pre/post events)
        operation = {
          type: 'Read',
          timestamp,
          correlation_id: event.correlation_id,
          content: content || undefined, // Explicitly set undefined if no content
          pre_event: event,
          post_event: event
        };

        // Additional logging to verify operation was created
        console.log(`[FILES] Created Read operation:`, {
          hasContent: !!operation.content,
          contentLength: operation.content?.length || 0,
          hasPreEvent: !!operation.pre_event,
          hasPostEvent: !!operation.post_event
        });
      }
      // Check for Write operations
      else if (event.type === 'hook' && event.subtype === 'pre_tool' && toolName === 'Write') {
        // Extract content - prioritize tool_parameters (backend format)
        const content = (
          (eventData.tool_parameters as any)?.content ||
          hookParams?.content ||
          toolParams?.content
        ) as string | undefined;

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
