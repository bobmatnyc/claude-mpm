import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173,
		strictPort: false,
		proxy: {
			// Proxy API calls to the Python backend during development
			'/api': {
				target: 'http://localhost:8765',
				changeOrigin: true
			},
			// Proxy Socket.IO connections to the Python backend
			'/socket.io': {
				target: 'http://localhost:8765',
				changeOrigin: true,
				ws: true
			}
		}
	}
});
