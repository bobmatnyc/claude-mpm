<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import EventStream from '$lib/components/EventStream.svelte';
	import JSONExplorer from '$lib/components/JSONExplorer.svelte';
	import type { ClaudeEvent } from '$lib/types/events';

	let selectedEvent = $state<ClaudeEvent | null>(null);
	let selectedStream = $state<string>('all');
</script>

<svelte:head>
	<title>Claude MPM Monitor</title>
</svelte:head>

<div class="flex flex-col h-screen bg-slate-900">
	<Header bind:selectedStream />

	<div class="flex flex-1 min-h-0">
		<!-- Left Panel: JSON Explorer -->
		<div class="w-80 flex-shrink-0">
			<JSONExplorer event={selectedEvent} />
		</div>

		<!-- Right Panel: Event Stream -->
		<div class="flex-1 min-w-0">
			<EventStream bind:selectedEvent {selectedStream} />
		</div>
	</div>
</div>
