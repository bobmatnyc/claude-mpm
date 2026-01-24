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
  sessionId?: string; // Stream/session ID for filtering by stream
  oldContent?: string; // Content before edit/write
  newContent?: string; // Content after edit/write
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
 *
 * Handles multiple event structures:
 * - Direct field: data.file_path
 * - Tool parameters: data.tool_parameters.file_path
 * - Notebook path: data.tool_parameters.notebook_path
 */
export function extractFilePath(data: unknown): string | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return null;
  }

  const dataRecord = data as Record<string, unknown>;

  // Check direct fields (file_path and notebook_path)
  if (dataRecord.file_path && typeof dataRecord.file_path === 'string') {
    return dataRecord.file_path;
  }
  if (dataRecord.notebook_path && typeof dataRecord.notebook_path === 'string') {
    return dataRecord.notebook_path;
  }

  // Check tool_parameters (standard hook event structure)
  const toolParams = dataRecord.tool_parameters;
  if (toolParams && typeof toolParams === 'object' && !Array.isArray(toolParams)) {
    const params = toolParams as Record<string, unknown>;

    // Check file_path
    if (params.file_path && typeof params.file_path === 'string') {
      return params.file_path;
    }

    // Check notebook_path (for NotebookEdit, NotebookRead)
    if (params.notebook_path && typeof params.notebook_path === 'string') {
      return params.notebook_path;
    }

    // Check path (for Grep, Glob)
    if (params.path && typeof params.path === 'string') {
      return params.path;
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

/**
 * Extract content from tool parameters (for Write/Edit operations)
 */
export function extractContent(data: unknown): { oldContent?: string; newContent?: string } {
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    return {};
  }

  const dataRecord = data as Record<string, unknown>;
  const toolParams = dataRecord.tool_parameters;

  if (!toolParams || typeof toolParams !== 'object' || Array.isArray(toolParams)) {
    return {};
  }

  const params = toolParams as Record<string, unknown>;
  const result: { oldContent?: string; newContent?: string } = {};

  // For Write operations: new_string or content is the new content
  if (params.content && typeof params.content === 'string') {
    result.newContent = params.content;
  } else if (params.new_string && typeof params.new_string === 'string') {
    result.newContent = params.new_string;
  }

  // For Edit operations: old_string is the old content
  if (params.old_string && typeof params.old_string === 'string') {
    result.oldContent = params.old_string;
  }

  return result;
}

/**
 * Generate a simple unified diff from old and new content
 * Returns array of diff lines with metadata
 */
export interface DiffLine {
  type: 'add' | 'remove' | 'context';
  content: string;
  lineNumber?: number;
}

export function generateDiff(oldContent: string, newContent: string): DiffLine[] {
  const oldLines = oldContent.split('\n');
  const newLines = newContent.split('\n');
  const diff: DiffLine[] = [];

  // Simple line-by-line diff (not a full LCS algorithm, but sufficient for our use case)
  const maxLen = Math.max(oldLines.length, newLines.length);

  let oldIdx = 0;
  let newIdx = 0;

  while (oldIdx < oldLines.length || newIdx < newLines.length) {
    const oldLine = oldLines[oldIdx];
    const newLine = newLines[newIdx];

    if (oldIdx >= oldLines.length) {
      // Only new lines remaining
      diff.push({ type: 'add', content: newLine, lineNumber: newIdx + 1 });
      newIdx++;
    } else if (newIdx >= newLines.length) {
      // Only old lines remaining
      diff.push({ type: 'remove', content: oldLine });
      oldIdx++;
    } else if (oldLine === newLine) {
      // Lines match - context
      diff.push({ type: 'context', content: oldLine, lineNumber: newIdx + 1 });
      oldIdx++;
      newIdx++;
    } else {
      // Lines differ - check if it's a replacement or insertion/deletion
      // Look ahead to see if the next old line matches current new line (deletion)
      // or if the next new line matches current old line (insertion)
      const nextOldMatchesNew = oldIdx + 1 < oldLines.length && oldLines[oldIdx + 1] === newLine;
      const nextNewMatchesOld = newIdx + 1 < newLines.length && newLines[newIdx + 1] === oldLine;

      if (nextOldMatchesNew && !nextNewMatchesOld) {
        // Next old line matches current new line - this old line was deleted
        diff.push({ type: 'remove', content: oldLine });
        oldIdx++;
      } else if (nextNewMatchesOld && !nextOldMatchesNew) {
        // Next new line matches current old line - this new line was inserted
        diff.push({ type: 'add', content: newLine, lineNumber: newIdx + 1 });
        newIdx++;
      } else {
        // Lines are different - show as remove + add (replacement)
        diff.push({ type: 'remove', content: oldLine });
        diff.push({ type: 'add', content: newLine, lineNumber: newIdx + 1 });
        oldIdx++;
        newIdx++;
      }
    }
  }

  return diff;
}
