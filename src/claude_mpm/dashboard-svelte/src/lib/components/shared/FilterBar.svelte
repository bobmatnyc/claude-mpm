<script lang="ts">
	import type { Snippet } from 'svelte';
	import SearchInput from '$lib/components/SearchInput.svelte';

	interface Props {
		searchValue: string;
		searchPlaceholder?: string;
		activeFilterCount: number;
		onClear: () => void;
		onSearchInput: (value: string) => void;
		children: Snippet;
	}

	let { searchValue = $bindable(''), searchPlaceholder = 'Search...', activeFilterCount, onClear, onSearchInput, children }: Props = $props();
</script>

<div class="p-3 border-b border-slate-200 dark:border-slate-700 space-y-2">
	<SearchInput
		value={searchValue}
		placeholder={searchPlaceholder}
		onInput={onSearchInput}
	/>
	<div class="flex items-center gap-2 flex-wrap">
		{@render children()}

		{#if activeFilterCount > 0}
			<button
				onclick={onClear}
				class="ml-auto text-xs text-slate-400 hover:text-red-400 dark:text-slate-500 dark:hover:text-red-400 transition-colors flex items-center gap-1"
			>
				<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
				Clear all
			</button>
		{/if}
	</div>
</div>
