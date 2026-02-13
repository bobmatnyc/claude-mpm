<script lang="ts">
	import { toastStore, type Toast } from '$lib/stores/toast.svelte';

	const typeClasses: Record<string, string> = {
		success: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
		error: 'bg-red-500/10 border-red-500/30 text-red-400',
		warning: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
		info: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400',
	};

	const typeIcons: Record<string, string> = {
		success: 'M5 13l4 4L19 7',
		error: 'M6 18L18 6M6 6l12 12',
		warning: 'M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
		info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
	};
</script>

{#if toastStore.toasts.length > 0}
	<div class="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 max-w-sm">
		{#each toastStore.toasts as toast (toast.id)}
			<div
				class="flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg transition-all duration-200 {typeClasses[
					toast.type
				]}"
				role="alert"
			>
				<svg
					class="w-5 h-5 flex-shrink-0 mt-0.5"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d={typeIcons[toast.type]}
					/>
				</svg>
				<p class="text-sm flex-1">{toast.message}</p>
				<button
					onclick={() => toastStore.remove(toast.id)}
					class="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity"
					aria-label="Dismiss"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>
		{/each}
	</div>
{/if}
