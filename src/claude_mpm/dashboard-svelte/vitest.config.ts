import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
	plugins: [svelte({ hot: !process.env.VITEST })],
	test: {
		globals: true,
		environment: 'jsdom',
		setupFiles: ['./src/lib/test-utils/setup.ts'],
		include: ['src/**/*.{test,spec}.{js,ts}'],
		alias: {
			$lib: '/src/lib',
		},
	},
});
