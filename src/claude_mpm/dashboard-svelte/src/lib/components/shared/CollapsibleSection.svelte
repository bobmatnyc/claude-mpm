<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title: string;
		count?: number;
		defaultExpanded?: boolean;
		children: Snippet;
	}

	let { title, count, defaultExpanded = false, children }: Props = $props();

	let expanded = $state(defaultExpanded);

	// Generate a unique ID for aria attributes
	const sectionId = crypto.randomUUID().slice(0, 8);

	function toggle() {
		expanded = !expanded;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			toggle();
		}
	}
</script>

<div class="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
	<button
		id="heading-{sectionId}"
		onclick={toggle}
		onkeydown={handleKeydown}
		class="w-full flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors cursor-pointer select-none"
		aria-expanded={expanded}
		aria-controls="section-{sectionId}"
	>
		<span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
			{title}
			{#if count !== undefined}
				<span class="ml-1 text-slate-400 dark:text-slate-500">({count})</span>
			{/if}
		</span>
		<svg
			class="w-4 h-4 text-slate-400 transition-transform duration-200 {expanded ? 'rotate-90' : 'rotate-0'}"
			fill="currentColor"
			viewBox="0 0 20 20"
		>
			<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
		</svg>
	</button>

	{#if expanded}
		<div
			id="section-{sectionId}"
			role="region"
			aria-labelledby="heading-{sectionId}"
			class="px-3 py-2 border-t border-slate-200 dark:border-slate-700"
		>
			{@render children()}
		</div>
	{/if}
</div>
