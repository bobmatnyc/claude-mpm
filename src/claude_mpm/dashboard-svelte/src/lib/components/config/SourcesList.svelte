<script lang="ts">
	import type { ConfigSource, SyncState } from '$lib/stores/config.svelte';
	import {
		addSource,
		updateSource,
		removeSource,
		syncSource,
		syncAllSources,
	} from '$lib/stores/config.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import Modal from '$lib/components/shared/Modal.svelte';
	import SourceForm from './SourceForm.svelte';
	import SyncProgress from './SyncProgress.svelte';

	interface Props {
		sources: ConfigSource[];
		loading: boolean;
		onSelect: (source: ConfigSource) => void;
		selectedSource: ConfigSource | null;
		syncStatus: Record<string, SyncState>;
	}

	let { sources, loading, onSelect, selectedSource, syncStatus = {} }: Props = $props();

	// --- System source detection (BR-11) ---
	const SYSTEM_AGENT_SOURCES = ['bobmatnyc/claude-mpm-agents/agents'];
	const SYSTEM_SKILL_SOURCES = ['system', 'anthropic-official'];

	function isSystemSource(source: ConfigSource): boolean {
		if (source.type === 'agent') {
			return SYSTEM_AGENT_SOURCES.includes(source.id);
		}
		return SYSTEM_SKILL_SOURCES.includes(source.id);
	}

	// --- Modal state ---
	let showAddModal = $state(false);
	let addSourceType = $state<'agent' | 'skill'>('agent');
	let showEditModal = $state(false);
	let editSource = $state<ConfigSource | null>(null);
	let showRemoveModal = $state(false);
	let removeTarget = $state<ConfigSource | null>(null);
	let removing = $state(false);
	let showAddDropdown = $state(false);
	let showSyncPanel = $state(false);

	// --- Helpers ---
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

	function getPriorityVariant(priority: number): 'danger' | 'warning' | 'default' {
		if (priority <= 0) return 'danger';
		if (priority <= 50) return 'warning';
		return 'default';
	}

	// --- Actions ---
	function openAddModal(type: 'agent' | 'skill') {
		addSourceType = type;
		showAddModal = true;
		showAddDropdown = false;
	}

	function openEditModal(source: ConfigSource) {
		editSource = source;
		showEditModal = true;
	}

	function openRemoveModal(source: ConfigSource) {
		removeTarget = source;
		showRemoveModal = true;
	}

	async function handleAddSubmit(data: Record<string, any>) {
		await addSource(addSourceType, data);
		showAddModal = false;
	}

	async function handleEditSubmit(data: Record<string, any>) {
		if (!editSource) return;
		await updateSource(editSource.type, editSource.id, data);
		showEditModal = false;
		editSource = null;
	}

	async function handleToggleEnabled(source: ConfigSource) {
		await updateSource(source.type, source.id, { enabled: !source.enabled });
	}

	async function handleRemoveConfirm() {
		if (!removeTarget) return;
		removing = true;
		try {
			await removeSource(removeTarget.type, removeTarget.id);
			showRemoveModal = false;
			removeTarget = null;
		} catch {
			// Error handled by store/toast
		} finally {
			removing = false;
		}
	}

	async function handleSync(source: ConfigSource) {
		await syncSource(source.type, source.id);
	}

	async function handleSyncAll() {
		await syncAllSources();
	}
</script>

<div class="flex flex-col h-full">
	<!-- Header with Add Source button -->
	<div class="flex items-center justify-between px-4 py-2 border-b border-slate-200 dark:border-slate-700">
		<div class="flex items-center gap-2">
			<span class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Sources</span>
			<button
				onclick={() => showSyncPanel = !showSyncPanel}
				class="text-xs text-cyan-500 hover:text-cyan-400 transition-colors"
				title="Toggle sync panel"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
				</svg>
			</button>
		</div>
		<div class="relative">
			<button
				onclick={() => showAddDropdown = !showAddDropdown}
				class="px-3 py-1.5 text-xs font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors flex items-center gap-1"
			>
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
				</svg>
				Add Source
			</button>
			{#if showAddDropdown}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="absolute right-0 mt-1 w-44 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-10 py-1"
				>
					<button
						onclick={() => openAddModal('agent')}
						class="w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors"
					>
						Agent Source
					</button>
					<button
						onclick={() => openAddModal('skill')}
						class="w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors"
					>
						Skill Source
					</button>
				</div>
			{/if}
		</div>
	</div>

	<!-- Sync Progress Panel (collapsible) -->
	{#if showSyncPanel}
		<div class="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40">
			<SyncProgress
				{sources}
				{syncStatus}
				onSyncSource={(type, id) => syncSource(type, id)}
				onSyncAll={handleSyncAll}
			/>
		</div>
	{/if}

	<!-- Sources list -->
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
					{@const isSystem = isSystemSource(source)}
					<div
						class="w-full text-left px-4 py-3 text-sm transition-colors
							{selectedSource?.id === source.id && selectedSource?.type === source.type
								? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500'
								: 'hover:bg-slate-50 dark:hover:bg-slate-700/30 border-l-2 border-l-transparent'}
							{!source.enabled ? 'opacity-50' : ''}"
					>
						<!-- Clickable area for selection -->
						<button
							onclick={() => onSelect(source)}
							class="w-full text-left"
						>
							<div class="flex items-center gap-2">
								{#if isSystem}
									<span title="System source (protected)">
										<svg class="w-3.5 h-3.5 text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
										</svg>
									</span>
								{/if}
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
						</button>

						<!-- Action buttons row -->
						<div class="mt-2 flex items-center justify-between">
							<div class="flex items-center gap-2">
								<Badge text={getPriorityLabel(source.priority)} variant={getPriorityVariant(source.priority)} />
								<span class="text-xs text-slate-400 font-mono">P{source.priority}</span>
							</div>
							<div class="flex items-center gap-1">
								<!-- Edit button -->
								<button
									onclick={(e) => { e.stopPropagation(); openEditModal(source); }}
									class="p-1.5 text-slate-400 hover:text-cyan-400 rounded transition-colors"
									title="Edit source"
								>
									<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
									</svg>
								</button>

								<!-- Enable/Disable toggle -->
								{#if isSystem}
									<span class="p-1.5 text-slate-600 cursor-not-allowed" title="System source cannot be disabled">
										<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
										</svg>
									</span>
								{:else}
									<button
										onclick={(e) => { e.stopPropagation(); handleToggleEnabled(source); }}
										class="p-1.5 rounded transition-colors
											{source.enabled ? 'text-emerald-400 hover:text-emerald-300' : 'text-slate-500 hover:text-slate-400'}"
										title={source.enabled ? 'Disable source' : 'Enable source'}
									>
										{#if source.enabled}
											<svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
												<path d="M17 3H7a5 5 0 000 10h10a5 5 0 000-10zm0 8a3 3 0 110-6 3 3 0 010 6z" />
											</svg>
										{:else}
											<svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
												<path d="M7 3h10a5 5 0 010 10H7A5 5 0 017 3zm0 8a3 3 0 100-6 3 3 0 000 6z" />
											</svg>
										{/if}
									</button>
								{/if}

								<!-- Sync button -->
								{#if source.enabled}
									<button
										onclick={(e) => { e.stopPropagation(); handleSync(source); }}
										class="p-1.5 text-slate-400 hover:text-cyan-400 rounded transition-colors"
										title="Sync source"
									>
										<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
										</svg>
									</button>
								{/if}

								<!-- Remove button -->
								{#if isSystem}
									<span class="p-1.5 text-slate-600 cursor-not-allowed" title="System source cannot be removed">
										<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
										</svg>
									</span>
								{:else}
									<button
										onclick={(e) => { e.stopPropagation(); openRemoveModal(source); }}
										class="p-1.5 text-slate-400 hover:text-red-400 rounded transition-colors"
										title="Remove source"
									>
										<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
										</svg>
									</button>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

<!-- Close dropdown on outside click -->
{#if showAddDropdown}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="fixed inset-0 z-[5]" onclick={() => showAddDropdown = false}></div>
{/if}

<!-- Add Source Modal -->
<Modal bind:open={showAddModal} title="Add {addSourceType === 'agent' ? 'Agent' : 'Skill'} Source" size="md">
	<SourceForm
		mode="add"
		sourceType={addSourceType}
		onsubmit={handleAddSubmit}
		oncancel={() => showAddModal = false}
	/>
</Modal>

<!-- Edit Source Modal -->
<Modal bind:open={showEditModal} title="Edit Source" size="md" onclose={() => { editSource = null; }}>
	{#if editSource}
		<SourceForm
			mode="edit"
			sourceType={editSource.type}
			initialData={editSource}
			onsubmit={handleEditSubmit}
			oncancel={() => { showEditModal = false; editSource = null; }}
		/>
	{/if}
</Modal>

<!-- Remove Confirmation Modal -->
<Modal bind:open={showRemoveModal} title="Remove Source" size="sm" onclose={() => { removeTarget = null; }}>
	{#if removeTarget}
		<div class="text-sm text-slate-300">
			<p>Are you sure you want to remove this source?</p>
			<div class="mt-3 p-3 bg-slate-900 rounded-lg">
				<p class="font-medium text-slate-100">{removeTarget.id}</p>
				<p class="text-xs text-slate-400 mt-1">{removeTarget.url}</p>
			</div>
			<p class="mt-3 text-amber-400 text-xs">This action cannot be undone. Deployed agents/skills from this source may become orphaned.</p>
		</div>
	{/if}
	{#snippet footer()}
		<button
			onclick={() => { showRemoveModal = false; removeTarget = null; }}
			class="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
		>
			Cancel
		</button>
		<button
			onclick={handleRemoveConfirm}
			disabled={removing}
			class="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700
				disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors
				flex items-center gap-2"
		>
			{#if removing}
				<svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
			{/if}
			Remove
		</button>
	{/snippet}
</Modal>
