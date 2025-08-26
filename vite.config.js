import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  // Build configuration
  build: {
    // Output directory for built assets
    outDir: 'src/claude_mpm/dashboard/static/dist',

    // Clear output directory before build
    emptyOutDir: true,

    // Generate source maps for debugging
    sourcemap: true,

    // Minification
    minify: 'terser',

    // Rollup options for advanced configuration
    rollupOptions: {
      // Multiple entry points for different dashboard components
      input: {
        // Main dashboard application
        dashboard: resolve(__dirname, 'src/claude_mpm/dashboard/static/js/dashboard.js'),

        // Individual components that can be loaded separately
        'socket-client': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/socket-client.js'),

        // Component modules
        'components/event-viewer': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/event-viewer.js'),
        'components/file-tool-tracker': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/file-tool-tracker.js'),
        'components/agent-inference': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/agent-inference.js'),
        'components/event-processor': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/event-processor.js'),
        'components/session-manager': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/session-manager.js'),
        'components/socket-manager': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/socket-manager.js'),
        'components/ui-state-manager': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/ui-state-manager.js'),
        'components/hud-manager': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/hud-manager.js'),
        'components/hud-visualizer': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/hud-visualizer.js'),
        'components/export-manager': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/export-manager.js'),
        'components/module-viewer': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/module-viewer.js'),
        'components/working-directory': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/working-directory.js'),
        'components/hud-library-loader': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/hud-library-loader.js'),
        'components/activity-tree': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/activity-tree.js'),
        'components/code-tree': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/code-tree.js'),
        'components/code-viewer': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components/code-viewer.js')
      },

      // Output configuration
      output: {
        // Use modern ES modules format
        format: 'es',

        // Entry point naming pattern
        entryFileNames: '[name].js',

        // Chunk naming for code splitting
        chunkFileNames: 'chunks/[name].[hash].js',

        // Asset naming (CSS, images, etc.)
        assetFileNames: 'assets/[name].[hash].[ext]',

        // Manual chunks for better caching
        manualChunks: {
          // Vendor libraries (if any are added later)
          vendor: [],

          // Core dashboard functionality
          core: [
            'src/claude_mpm/dashboard/static/js/components/socket-manager.js',
            'src/claude_mpm/dashboard/static/js/components/ui-state-manager.js'
          ],

          // Event handling components
          events: [
            'src/claude_mpm/dashboard/static/js/components/event-viewer.js',
            'src/claude_mpm/dashboard/static/js/components/event-processor.js'
          ],

          // HUD and visualization components
          visualization: [
            'src/claude_mpm/dashboard/static/js/components/hud-manager.js',
            'src/claude_mpm/dashboard/static/js/components/hud-visualizer.js'
          ]
        }
      }
    },

    // Target modern browsers for better optimization
    target: 'es2020',

    // CSS code splitting
    cssCodeSplit: true,

    // Asset inlining threshold (in bytes)
    assetsInlineLimit: 4096
  },

  // Development server configuration
  server: {
    port: 3000,
    host: 'localhost',

    // Proxy API requests to the Python backend during development
    proxy: {
      '/api': {
        target: 'http://localhost:8765',
        changeOrigin: true
      },
      '/socket.io': {
        target: 'http://localhost:8765',
        changeOrigin: true,
        ws: true
      }
    },

    // Enable CORS for development
    cors: true
  },

  // CSS preprocessing
  css: {
    // CSS modules configuration (if needed)
    modules: {
      localsConvention: 'camelCase'
    }
  },

  // Plugin configuration
  plugins: [
    // Add plugins as needed for future enhancements
  ],

  // Resolve configuration
  resolve: {
    // Alias for cleaner imports
    alias: {
      '@': resolve(__dirname, 'src/claude_mpm/dashboard/static'),
      '@components': resolve(__dirname, 'src/claude_mpm/dashboard/static/js/components'),
      '@css': resolve(__dirname, 'src/claude_mpm/dashboard/static/css')
    },

    // File extensions to resolve
    extensions: ['.js', '.mjs', '.json', '.css']
  },

  // Optimization configuration
  optimizeDeps: {
    // Include dependencies that should be pre-bundled
    include: [],

    // Exclude dependencies from pre-bundling
    exclude: []
  },

  // Environment variables
  define: {
    // Define build-time constants
    __DEV__: JSON.stringify(process.env.NODE_ENV === 'development'),
    __VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0')
  }
});
