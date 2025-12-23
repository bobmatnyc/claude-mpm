<script lang="ts">
	import { onMount } from 'svelte';
	import { socketStore } from '$lib/stores/socket.svelte';
	import { themeStore } from '$lib/stores/theme.svelte';
	import '../app.css';

	onMount(() => {
		socketStore.connect();

		return () => {
			socketStore.disconnect();
		};
	});

	// Reactive theme class
	let themeClass = $derived(themeStore.current === 'dark' ? 'dark' : '');
</script>

<div class="{themeClass} min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col transition-colors">
	<main class="flex-1 overflow-hidden">
		<slot />
	</main>
</div>
