/**
 * Theme Store (Traditional Svelte Stores)
 *
 * Manages light/dark theme state with localStorage persistence.
 * Uses traditional Svelte stores for module-level reactivity.
 *
 * IMPORTANT: This file uses traditional stores instead of Svelte 5 runes
 * because the store is created at module-load time, outside component context.
 * Runes ($state, $derived) can only be used inside components.
 */

import { writable } from 'svelte/store';

// Get stored theme or default to light
function getStoredTheme() {
  if (typeof window === 'undefined') {
    return 'light';
  }
  return localStorage.getItem('theme') || 'light';
}

function createThemeStore() {
  const { subscribe, set, update } = writable(getStoredTheme());

  return {
    subscribe,
    toggle: () => {
      update(current => {
        const newTheme = current === 'light' ? 'dark' : 'light';

        // Persist to localStorage
        if (typeof window !== 'undefined') {
          localStorage.setItem('theme', newTheme);
          document.documentElement.setAttribute('data-theme', newTheme);
        }

        return newTheme;
      });
    },
    set: (value) => {
      // Validate theme value
      if (value !== 'light' && value !== 'dark') {
        console.error(`Invalid theme value: ${value}. Using 'light' instead.`);
        value = 'light';
      }

      // Persist to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('theme', value);
        document.documentElement.setAttribute('data-theme', value);
      }

      set(value);
    },
    initialize: () => {
      // Set initial theme on document
      if (typeof window !== 'undefined') {
        const theme = getStoredTheme();
        document.documentElement.setAttribute('data-theme', theme);
      }
    }
  };
}

export const themeStore = createThemeStore();
