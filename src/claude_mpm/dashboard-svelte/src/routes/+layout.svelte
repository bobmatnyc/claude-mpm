<script lang="ts">
	import { onMount } from 'svelte';
	import { socketStore } from '$lib/stores/socket.svelte';
	import '../app.css';

	onMount(() => {
		socketStore.connect();

		return () => {
			socketStore.disconnect();
		};
	});
</script>

<div class="dark min-h-screen bg-slate-900 flex flex-col">
	<main class="flex-1 overflow-hidden">
		<slot />
	</main>
</div>
