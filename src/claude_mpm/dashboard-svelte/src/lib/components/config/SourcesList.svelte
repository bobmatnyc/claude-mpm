<script lang="ts">
	import type { ConfigSource } from '$lib/stores/config.svelte';
	import Badge from '$lib/components/Badge.svelte';

	interface Props {
		sources: ConfigSource[];
		loading: boolean;
		onSelect: (source: ConfigSource) => void;
		selectedSource: ConfigSource | null;
	}

	let { sources, loading, onSelect, selectedSource }: Props = $props();

	function extractRepoName(url: string): string {
		if (!url) return 'Unknown';
		try {
			const parts = url.replace(/\.git$/, '').split('/');
			const repo = parts.pop() || '';
			const owner = parts.pop() || '';
			return owner ? `${owner}/${repo}` : repo;
		} catch {
			return url;
		}
	}

	function getTypeVariant(type: string): 'info' | 'primary' {
		return type === 'agent' ? 'info' : 'primary';
	}

	function getPriorityLabel(priority: number): string {
		if (priority <= 0) return 'System';
		if (priority <= 50) return 'High';
		if (priority <= 100) return 'Normal';
		return 'Low';
	}

	function getPriorityVariant(priority: number): 'danger' | 'warning' | 'default' | 'default' {
		if (priority <= 0) return 'danger';
		if (priority <= 50) return 'warning';
		return 'default';
	}
</script>

<div class="flex flex-col h-full">
	<div class="flex-1 overflow-y-auto">
		{#if loading}
			<div class="flex items-center justify-center py-8 text-slate-500 dark:text-slate-400">
				<svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<span class="text-sm">Loading sources...</span>
			</div>
		{:else if sources.length === 0}
			<div class="py-6 text-center text-sm text-slate-500 dark:text-slate-400">
				No sources configured
			</div>
		{:else}
			<div class="divide-y divide-slate-100 dark:divide-slate-700/50">
				{#each sources as source (source.id + '-' + source.type)}
					<button
						onclick={() => onSelect(source)}
						class="w-full text-left px-4 py-3 flex items-center gap-3 text-sm transition-colors
							{selectedSource?.id === source.id && selectedSource?.type === source.type
								? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
								: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}
							{!source.enabled ? 'opacity-50' : ''}"
					>
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<Badge text={source.type === 'agent' ? 'Agent' : 'Skill'} variant={getTypeVariant(source.type)} />
								<span class="font-medium text-slate-900 dark:text-slate-100 truncate">
									{extractRepoName(source.url)}
								</span>
								{#if !source.enabled}
									<Badge text="Disabled" variant="danger" />
								{/if}
							</div>
							<div class="mt-1 flex items-center gap-3">
								<span class="text-xs text-slate-500 dark:text-slate-400 truncate">{source.url}</span>
							</div>
						</div>
						<div class="flex-shrink-0 flex items-center gap-2">
							<Badge text={getPriorityLabel(source.priority)} variant={getPriorityVariant(source.priority)} />
							<span class="text-xs text-slate-400 font-mono">P{source.priority}</span>
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>
