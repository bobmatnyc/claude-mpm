/**
 * Files Store - Direct File Browser
 *
 * WHY: Files tab should be a direct file browser, NOT dependent on hook events.
 * This store fetches files directly from the working directory via API.
 */

import { writable } from 'svelte/store';

export interface FileEntry {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size: number;
  modified: number;
  extension?: string;
}

export interface DirectoryListing {
  path: string;
  directories: FileEntry[];
  files: FileEntry[];
  total_files: number;
  total_directories: number;
}

/**
 * Fetch files from the working directory
 */
export async function fetchFiles(path?: string): Promise<DirectoryListing> {
  try {
    const url = path ? `/api/files?path=${encodeURIComponent(path)}` : '/api/files';
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to fetch files: ${response.statusText}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(data.error || 'Failed to load files');
    }

    return {
      path: data.path,
      directories: data.directories || [],
      files: data.files || [],
      total_files: data.total_files || 0,
      total_directories: data.total_directories || 0,
    };
  } catch (error) {
    console.error('[files.svelte.ts] Error fetching files:', error);
    throw error;
  }
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
 * Create a reactive store for directory listing
 */
export function createFilesStore() {
  const { subscribe, set, update } = writable<DirectoryListing>({
    path: '',
    directories: [],
    files: [],
    total_files: 0,
    total_directories: 0,
  });

  return {
    subscribe,
    set,
    update,
    /**
     * Load files from a directory
     */
    async load(path?: string) {
      try {
        const listing = await fetchFiles(path);
        set(listing);
      } catch (error) {
        console.error('[FilesStore] Failed to load files:', error);
        // Set empty listing on error
        set({
          path: path || '',
          directories: [],
          files: [],
          total_files: 0,
          total_directories: 0,
        });
      }
    },
  };
}
