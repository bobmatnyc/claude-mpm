import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),

	kit: {
		paths: {
			base: ''
		},
		adapter: adapter({
			pages: '../dashboard/static/svelte-build',
			assets: '../dashboard/static/svelte-build',
			fallback: 'index.html',
			precompress: false,
			strict: false
		})
	}
};

export default config;
