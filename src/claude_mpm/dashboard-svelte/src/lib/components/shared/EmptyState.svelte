<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		message: string;
		icon?: Snippet;
		action?: Snippet;
	}

	let { message, icon, action }: Props = $props();
</script>

<div class="flex flex-col items-center justify-center py-12 px-4 text-center">
	{#if icon}
		<div class="mb-3 text-slate-400 dark:text-slate-500">
			{@render icon()}
		</div>
	{:else}
		<svg class="w-12 h-12 mb-3 text-slate-300 dark:text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
		</svg>
	{/if}

	<p class="text-sm text-slate-500 dark:text-slate-400">{message}</p>

	{#if action}
		<div class="mt-4">
			{@render action()}
		</div>
	{/if}
</div>
