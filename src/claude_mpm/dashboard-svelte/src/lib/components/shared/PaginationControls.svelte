<script lang="ts">
	import { getPageRange, hasNextPage, hasPreviousPage, type PaginationState } from '$lib/utils/pagination';

	interface Props {
		state: PaginationState;
		onPrevious: () => void;
		onNext: () => void;
		mode?: 'pages' | 'load-more';
		onLoadMore?: () => void;
	}

	let { state, onPrevious, onNext, mode = 'pages', onLoadMore }: Props = $props();

	let range = $derived(getPageRange(state));
	let canPrevious = $derived(hasPreviousPage(state));
	let canNext = $derived(hasNextPage(state));
</script>

{#if mode === 'load-more'}
	{#if canNext}
		<div class="flex justify-center py-3">
			<button
				onclick={onLoadMore}
				class="px-4 py-1.5 text-sm font-medium text-cyan-600 dark:text-cyan-400
					bg-cyan-50 dark:bg-cyan-900/20 hover:bg-cyan-100 dark:hover:bg-cyan-900/30
					rounded-md transition-colors"
			>
				Load More
			</button>
		</div>
	{/if}
{:else}
	<div class="flex items-center justify-between px-4 py-2 border-t border-slate-200 dark:border-slate-700">
		<span class="text-xs text-slate-500 dark:text-slate-400">
			{#if state.total === 0}
				No items
			{:else}
				Showing {range.start}-{range.end} of {state.total}
			{/if}
		</span>

		<div class="flex items-center gap-1">
			<button
				onclick={onPrevious}
				disabled={!canPrevious}
				class="p-1 rounded text-slate-500 dark:text-slate-400
					hover:bg-slate-100 dark:hover:bg-slate-700
					disabled:opacity-30 disabled:cursor-not-allowed
					transition-colors"
				aria-label="Previous page"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</button>
			<button
				onclick={onNext}
				disabled={!canNext}
				class="p-1 rounded text-slate-500 dark:text-slate-400
					hover:bg-slate-100 dark:hover:bg-slate-700
					disabled:opacity-30 disabled:cursor-not-allowed
					transition-colors"
				aria-label="Next page"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</button>
		</div>
	</div>
{/if}
