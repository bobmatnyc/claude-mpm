<script lang="ts">
	import type { ConfigSource } from '$lib/stores/config.svelte';
	import ProgressBar from '$lib/components/shared/ProgressBar.svelte';
	import SharedBadge from '$lib/components/shared/Badge.svelte';

	interface SyncState {
		status: 'idle' | 'syncing' | 'completed' | 'failed';
		progress: number;
		lastSync: string | null;
		error: string | null;
		jobId: string | null;
	}

	interface Props {
		sources: ConfigSource[];
		syncStatus: Record<string, SyncState>;
		onSyncSource: (type: 'agent' | 'skill', id: string) => void;
		onSyncAll: () => void;
	}

	let { sources, syncStatus, onSyncSource, onSyncAll }: Props = $props();

	let isSyncing = $derived(
		Object.values(syncStatus).some((s) => s.status === 'syncing')
	);

	function getStatusForSource(source: ConfigSource): SyncState {
		return (
			syncStatus[source.id] ?? {
				status: 'idle',
				progress: 0,
				lastSync: null,
				error: null,
				jobId: null,
			}
		);
	}

	function getStatusVariant(
		status: string
	): 'default' | 'info' | 'success' | 'error' {
		switch (status) {
			case 'syncing':
				return 'info';
			case 'completed':
				return 'success';
			case 'failed':
				return 'error';
			default:
				return 'default';
		}
	}

	function formatRelativeTime(isoString: string | null): string {
		if (!isoString) return 'Never';
		try {
			const date = new Date(isoString);
			const now = new Date();
			const diffMs = now.getTime() - date.getTime();
			const diffSec = Math.floor(diffMs / 1000);
			const diffMin = Math.floor(diffSec / 60);
			const diffHour = Math.floor(diffMin / 60);
			const diffDay = Math.floor(diffHour / 24);

			if (diffSec < 60) return 'Just now';
			if (diffMin < 60) return `${diffMin} minute${diffMin === 1 ? '' : 's'} ago`;
			if (diffHour < 24) return `${diffHour} hour${diffHour === 1 ? '' : 's'} ago`;
			return `${diffDay} day${diffDay === 1 ? '' : 's'} ago`;
		} catch {
			return 'Unknown';
		}
	}
</script>

<div class="space-y-3">
	<!-- Sync All button -->
	<div class="flex items-center justify-between">
		<h3 class="text-sm font-semibold text-slate-300">Sync Status</h3>
		<button
			onclick={onSyncAll}
			disabled={isSyncing}
			class="px-3 py-1.5 text-xs font-medium text-white bg-cyan-600 hover:bg-cyan-700
				disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors
				flex items-center gap-1.5"
		>
			{#if isSyncing}
				<svg class="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
					<circle
						class="opacity-25"
						cx="12"
						cy="12"
						r="10"
						stroke="currentColor"
						stroke-width="4"
					></circle>
					<path
						class="opacity-75"
						fill="currentColor"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
					></path>
				</svg>
				Syncing...
			{:else}
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
					/>
				</svg>
				Sync All
			{/if}
		</button>
	</div>

	<!-- Per-source status rows -->
	<div class="space-y-2">
		{#each sources.filter((s) => s.enabled) as source (source.id + '-' + source.type)}
			{@const status = getStatusForSource(source)}
			<div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3">
				<div class="flex items-center justify-between mb-1">
					<div class="flex items-center gap-2 min-w-0">
						<span class="text-sm text-slate-200 truncate">{source.id}</span>
						<SharedBadge variant={getStatusVariant(status.status)} size="sm">
							{status.status}
						</SharedBadge>
					</div>
					<div class="flex items-center gap-2 flex-shrink-0">
						{#if status.status === 'failed'}
							<button
								onclick={() => onSyncSource(source.type, source.id)}
								class="px-2 py-1 text-xs font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20
									border border-red-500/30 rounded transition-colors"
							>
								Retry
							</button>
						{/if}
						<span class="text-xs text-slate-500">
							{formatRelativeTime(status.lastSync)}
						</span>
					</div>
				</div>

				{#if status.status === 'syncing'}
					<ProgressBar
						value={status.progress}
						indeterminate={status.progress === 0}
						size="sm"
					/>
				{/if}

				{#if status.status === 'failed' && status.error}
					<p class="text-xs text-red-400 mt-1">{status.error}</p>
				{/if}
			</div>
		{/each}

		{#if sources.filter((s) => s.enabled).length === 0}
			<p class="text-sm text-slate-500 text-center py-4">No enabled sources to sync</p>
		{/if}
	</div>
</div>
