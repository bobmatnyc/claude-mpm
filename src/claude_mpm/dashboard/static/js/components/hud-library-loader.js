/**
 * HUD Library Loader
 * Handles lazy loading of Cytoscape.js and its dependencies with proper loading order
 */

class HUDLibraryLoader {
    constructor() {
        this.loadedLibraries = new Set();
        this.loadingPromises = new Map();
        this.loadingCallbacks = new Map();

        // Define library configurations with proper loading order
        this.libraries = [
            {
                name: 'cytoscape',
                url: 'https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js',
                globalCheck: () => typeof window.cytoscape !== 'undefined',
                dependencies: []
            },
            {
                name: 'dagre',
                url: 'https://unpkg.com/dagre@0.8.5/dist/dagre.min.js',
                globalCheck: () => typeof window.dagre !== 'undefined',
                dependencies: []
            },
            {
                name: 'cytoscape-dagre',
                url: 'https://unpkg.com/cytoscape-dagre@2.5.0/cytoscape-dagre.js',
                globalCheck: () => typeof window.cytoscapeDagre !== 'undefined',
                dependencies: ['cytoscape', 'dagre']
            }
        ];
    }

    /**
     * Load a single library via script tag
     * @param {Object} library - Library configuration object
     * @returns {Promise} - Promise that resolves when library is loaded
     */
    loadLibrary(library) {
        // Check if already loaded
        if (library.globalCheck()) {
            this.loadedLibraries.add(library.name);
            return Promise.resolve();
        }

        // Check if already loading
        if (this.loadingPromises.has(library.name)) {
            return this.loadingPromises.get(library.name);
        }

        console.log(`Loading library: ${library.name} from ${library.url}`);

        const promise = new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = library.url;
            script.async = true;

            script.onload = () => {
                if (library.globalCheck()) {
                    console.log(`Successfully loaded library: ${library.name}`);
                    this.loadedLibraries.add(library.name);
                    this.loadingPromises.delete(library.name);
                    resolve();
                } else {
                    const error = new Error(`Library ${library.name} failed global check after loading`);
                    console.error(error);
                    this.loadingPromises.delete(library.name);
                    reject(error);
                }
            };

            script.onerror = () => {
                const error = new Error(`Failed to load library: ${library.name} from ${library.url}`);
                console.error(error);
                this.loadingPromises.delete(library.name);
                reject(error);
            };

            document.head.appendChild(script);
        });

        this.loadingPromises.set(library.name, promise);
        return promise;
    }

    /**
     * Load dependencies for a library
     * @param {Array} dependencies - Array of dependency names
     * @returns {Promise} - Promise that resolves when all dependencies are loaded
     */
    async loadDependencies(dependencies) {
        const dependencyPromises = dependencies.map(depName => {
            const depLibrary = this.libraries.find(lib => lib.name === depName);
            if (!depLibrary) {
                throw new Error(`Dependency ${depName} not found in library configuration`);
            }
            return this.loadLibraryWithDependencies(depLibrary);
        });

        return Promise.all(dependencyPromises);
    }

    /**
     * Load a library and all its dependencies
     * @param {Object} library - Library configuration object
     * @returns {Promise} - Promise that resolves when library and dependencies are loaded
     */
    async loadLibraryWithDependencies(library) {
        // Load dependencies first
        if (library.dependencies.length > 0) {
            await this.loadDependencies(library.dependencies);
        }

        // Then load the library itself
        return this.loadLibrary(library);
    }

    /**
     * Load all HUD visualization libraries in correct order
     * @param {Function} onProgress - Optional progress callback
     * @returns {Promise} - Promise that resolves when all libraries are loaded
     */
    async loadHUDLibraries(onProgress = null) {
        console.log('Starting HUD libraries loading...');

        try {
            // Load libraries in dependency order
            for (let i = 0; i < this.libraries.length; i++) {
                const library = this.libraries[i];

                if (onProgress) {
                    onProgress({
                        library: library.name,
                        current: i + 1,
                        total: this.libraries.length,
                        message: `Loading ${library.name}...`
                    });
                }

                await this.loadLibraryWithDependencies(library);
            }

            // Verify all libraries are loaded
            const missingLibraries = this.libraries.filter(lib => !lib.globalCheck());
            if (missingLibraries.length > 0) {
                throw new Error(`Failed to load libraries: ${missingLibraries.map(lib => lib.name).join(', ')}`);
            }

            console.log('All HUD libraries loaded successfully');

            if (onProgress) {
                onProgress({
                    library: 'complete',
                    current: this.libraries.length,
                    total: this.libraries.length,
                    message: 'All libraries loaded successfully'
                });
            }

            return true;
        } catch (error) {
            console.error('Failed to load HUD libraries:', error);

            if (onProgress) {
                onProgress({
                    library: 'error',
                    current: 0,
                    total: this.libraries.length,
                    message: `Error: ${error.message}`,
                    error: error
                });
            }

            throw error;
        }
    }

    /**
     * Check if all HUD libraries are loaded
     * @returns {boolean} - True if all libraries are loaded
     */
    areLibrariesLoaded() {
        return this.libraries.every(lib => lib.globalCheck());
    }

    /**
     * Get loading status for all libraries
     * @returns {Object} - Status object with library loading states
     */
    getLoadingStatus() {
        return {
            loaded: Array.from(this.loadedLibraries),
            loading: Array.from(this.loadingPromises.keys()),
            total: this.libraries.length,
            allLoaded: this.areLibrariesLoaded()
        };
    }

    /**
     * Reset loader state (for testing purposes)
     */
    reset() {
        this.loadedLibraries.clear();
        this.loadingPromises.clear();
        this.loadingCallbacks.clear();
    }
}

// Create singleton instance
window.HUDLibraryLoader = new HUDLibraryLoader();
