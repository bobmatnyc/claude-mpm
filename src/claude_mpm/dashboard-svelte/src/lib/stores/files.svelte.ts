/**
 * Files Store - Tracks files touched by Claude during session
 *
 * WHY: Files tab should show files that Claude has interacted with (Read, Write, Edit),
 * NOT a general file browser. This provides session-specific file activity.
 */

export interface TouchedFile {
  path: string;
  name: string;
  operation: 'read' | 'write' | 'edit';
  timestamp: string | number;
  toolName: string;
  eventId: string;
}

// FileEntry type for compatibility with FileViewer component
export interface FileEntry {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size: number;
  modified: number;
  extension?: string;
}

/**
 * Fetch file content from the server
 */
export async function fetchFileContent(filePath: string): Promise<string> {
  try {
    const response = await fetch(`/api/file/read?path=${encodeURIComponent(filePath)}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch file: ${response.statusText}`);
    }

    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    return data.content || '';
  } catch (error) {
    console.error('[files.svelte.ts] Error fetching file content:', error);
    throw error;
  }
}

/**
 * Extract file path from tool event data
 */
export function extractFilePath(data: unknown): string | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null;
  }

  const dataRecord = data as Record<string, unknown>;

  // Check direct fields
  if (dataRecord.file_path && typeof dataRecord.file_path === 'string') {
    return dataRecord.file_path;
  }

  // Check tool_parameters (standard hook event structure)
  const toolParams = dataRecord.tool_parameters;
  if (toolParams && typeof toolParams === 'object' && !Array.isArray(toolParams)) {
    const params = toolParams as Record<string, unknown>;
    if (params.file_path && typeof params.file_path === 'string') {
      return params.file_path;
    }
  }

  return null;
}

/**
 * Determine operation type from tool name
 */
export function getOperationType(toolName: string): 'read' | 'write' | 'edit' | null {
  switch (toolName.toLowerCase()) {
    case 'read':
      return 'read';
    case 'write':
      return 'write';
    case 'edit':
    case 'multiedit':
      return 'edit';
    default:
      return null;
  }
}

/**
 * Extract filename from full path
 */
export function getFileName(path: string): string {
  return path.split('/').filter(Boolean).pop() || path;
}
