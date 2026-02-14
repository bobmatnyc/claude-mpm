<script lang="ts">
	import { switchDeploymentMode, type ModeImpactPreview } from '$lib/stores/config.svelte';
	import { toastStore } from '$lib/stores/toast.svelte';
	import Modal from '$lib/components/shared/Modal.svelte';
	import Badge from '$lib/components/Badge.svelte';

	let {
		currentMode,
		onClose,
		onModeChanged,
	}: {
		currentMode: string;
		onClose: () => void;
		onModeChanged: (newMode: string) => void;
	} = $props();

	let open = $state(true);
	let step = $state<1 | 2>(1);
	let loading = $state(false);
	let switching = $state(false);
	let preview = $state<ModeImpactPreview | null>(null);
	let error = $state<string | null>(null);

	// Step 2 state
	let confirmChecked = $state(false);
	let confirmTyped = $state('');

	let targetMode = $derived(currentMode === 'selective' ? 'full' : 'selective');
	let targetModeLabel = $derived(targetMode === 'full' ? 'Full' : 'Selective');
	let currentModeLabel = $derived(currentMode === 'full' ? 'Full' : 'Selective');
	let canConfirm = $derived(confirmChecked && confirmTyped.toLowerCase() === 'switch');

	async function loadPreview() {
		loading = true;
		error = null;
		try {
			const result = await switchDeploymentMode(targetMode, { preview: true });
			preview = result.impact || result.data?.impact || null;
		} catch (e: any) {
			error = e.message || 'Failed to load preview';
		} finally {
			loading = false;
		}
	}

	async function handleConfirmSwitch() {
		if (!canConfirm) return;
		switching = true;
		error = null;
		try {
			await switchDeploymentMode(targetMode, { confirm: true });
			toastStore.success(`Deployment mode switched to ${targetModeLabel}`);
			onModeChanged(targetMode);
			handleClose();
		} catch (e: any) {
			error = e.message || 'Failed to switch mode';
		} finally {
			switching = false;
		}
	}

	function handleClose() {
		open = false;
		onClose();
	}

	function goToStep2() {
		step = 2;
		confirmChecked = false;
		confirmTyped = '';
	}

	function goBackToStep1() {
		step = 1;
	}

	// Load preview on mount
	$effect(() => {
		loadPreview();
	});
</script>

<Modal bind:open title="Switch Deployment Mode" size="md" onclose={handleClose}>
	{#snippet children()}
		<!-- Step indicator -->
		<div class="flex items-center gap-2 mb-4">
			<div class="flex items-center gap-1">
				<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
					{step === 1 ? 'bg-cyan-500 text-white' : 'bg-slate-700 text-slate-400'}">1</div>
				<span class="text-xs {step === 1 ? 'text-cyan-300' : 'text-slate-500'}">Preview</span>
			</div>
			<div class="w-8 h-0.5 bg-slate-700"></div>
			<div class="flex items-center gap-1">
				<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
					{step === 2 ? 'bg-cyan-500 text-white' : 'bg-slate-700 text-slate-400'}">2</div>
				<span class="text-xs {step === 2 ? 'text-cyan-300' : 'text-slate-500'}">Confirm</span>
			</div>
		</div>

		<!-- Mode switch header -->
		<div class="flex items-center gap-2 mb-4 p-3 bg-slate-900 rounded-lg">
			<Badge text={currentModeLabel} variant={currentMode === 'full' ? 'success' : 'info'} />
			<svg class="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
			</svg>
			<Badge text={targetModeLabel} variant={targetMode === 'full' ? 'success' : 'info'} />
		</div>

		{#if error}
			<div class="mb-4 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
				{error}
			</div>
		{/if}

		{#if step === 1}
			<!-- Step 1: Preview -->
			{#if loading}
				<div class="flex items-center justify-center py-8 text-slate-400">
					<svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					<span class="text-sm">Loading impact preview...</span>
				</div>
			{:else if preview}
				<!-- Note callout (e.g. switching to full mode info) -->
				{#if preview.note}
					<div class="mb-4 px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg">
						<div class="flex items-start gap-2">
							<svg class="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<p class="text-xs text-amber-300">{preview.note}</p>
						</div>
					</div>
				{/if}

				<div class="space-y-3 max-h-60 overflow-y-auto">
					{#if (preview.would_remove ?? []).length > 0}
						<div>
							<h4 class="text-xs font-semibold text-red-400 uppercase mb-1">Would be removed ({(preview.would_remove ?? []).length})</h4>
							<div class="flex flex-wrap gap-1">
								{#each preview.would_remove ?? [] as skill}
									<span class="px-2 py-0.5 text-xs rounded-full bg-red-500/10 text-red-300">{skill}</span>
								{/each}
							</div>
						</div>
					{/if}
					{#if (preview.would_keep ?? []).length > 0}
						<div>
							<h4 class="text-xs font-semibold text-slate-400 uppercase mb-1">Would be kept ({(preview.would_keep ?? []).length})</h4>
							<div class="flex flex-wrap gap-1">
								{#each preview.would_keep ?? [] as skill}
									<span class="px-2 py-0.5 text-xs rounded-full bg-slate-700 text-slate-400">{skill}</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>

				<div class="mt-3 text-xs text-slate-500">
					Total skills after switch: <span class="font-semibold text-slate-300">{preview.keep_count ?? 0}</span>
				</div>
			{/if}
		{:else}
			<!-- Step 2: Confirm -->
			<div class="space-y-4">
				<label class="flex items-start gap-2 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={confirmChecked}
						class="mt-1 rounded border-slate-600 bg-slate-900 text-cyan-500 focus:ring-cyan-500"
					/>
					<span class="text-sm text-slate-300">
						I understand this will change the skill deployment mode from
						<span class="font-semibold">{currentModeLabel}</span> to
						<span class="font-semibold">{targetModeLabel}</span>
						{#if preview}
							, affecting {(preview.would_remove ?? []).length} skill{(preview.would_remove ?? []).length === 1 ? '' : 's'}
						{/if}
					</span>
				</label>

				<div>
					<label class="block text-xs text-slate-400 mb-1.5">
						Type <span class="font-mono font-semibold text-slate-200">switch</span> to confirm
					</label>
					<input
						type="text"
						bind:value={confirmTyped}
						placeholder="switch"
						class="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-600 rounded-md
							text-slate-100 placeholder-slate-500
							focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
					/>
				</div>
			</div>
		{/if}
	{/snippet}

	{#snippet footer()}
		<button
			onclick={step === 2 ? goBackToStep1 : handleClose}
			class="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
		>
			{step === 2 ? 'Back' : 'Cancel'}
		</button>
		{#if step === 1}
			<button
				onclick={goToStep2}
				disabled={loading || !preview}
				class="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
			>
				Next: Confirm
			</button>
		{:else}
			<button
				onclick={handleConfirmSwitch}
				disabled={!canConfirm || switching}
				class="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700
					disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors
					flex items-center gap-2"
			>
				{#if switching}
					<svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
				{/if}
				Confirm Switch
			</button>
		{/if}
	{/snippet}
</Modal>
