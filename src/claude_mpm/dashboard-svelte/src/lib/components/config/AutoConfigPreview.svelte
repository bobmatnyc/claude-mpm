<script lang="ts">
	import {
		detectToolchain,
		previewAutoConfig,
		applyAutoConfig,
		type ToolchainResult,
		type AutoConfigPreview as AutoConfigPreviewType,
	} from '$lib/stores/config.svelte';
	import { toastStore } from '$lib/stores/toast.svelte';
	import Modal from '$lib/components/shared/Modal.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import DeploymentPipeline from './DeploymentPipeline.svelte';
	import type { PipelineStage } from './DeploymentPipeline.svelte';

	let { onClose }: { onClose: () => void } = $props();

	let open = $state(true);
	let step = $state<1 | 2>(1);

	// Step 1 state
	let detecting = $state(false);
	let toolchain = $state<ToolchainResult | null>(null);
	let previewData = $state<AutoConfigPreviewType | null>(null);
	let detectError = $state<string | null>(null);

	// Step 2 state
	let applying = $state(false);
	let applyError = $state<string | null>(null);
	let applyResult = $state<any>(null);
	let confirmTyped = $state('');
	let pipelineStages = $state<PipelineStage[]>([]);

	let canApply = $derived(confirmTyped.toLowerCase() === 'apply');

	const confidenceColors: Record<string, string> = {
		HIGH: 'success',
		MEDIUM: 'warning',
		LOW: 'danger',
	};

	async function analyzeProject() {
		detecting = true;
		detectError = null;
		try {
			toolchain = await detectToolchain();
			previewData = await previewAutoConfig();
		} catch (e: any) {
			detectError = e.message || 'Failed to analyze project';
		} finally {
			detecting = false;
		}
	}

	async function handleApply() {
		if (!canApply) return;
		applying = true;
		applyError = null;
		pipelineStages = [
			{ name: 'Backup', status: 'active' },
			{ name: 'Agents', status: 'pending' },
			{ name: 'Skills', status: 'pending' },
			{ name: 'Verify', status: 'pending' },
		];
		try {
			// Progress simulation (real progress would come from Socket.IO)
			pipelineStages = [
				{ name: 'Backup', status: 'success' },
				{ name: 'Agents', status: 'active' },
				{ name: 'Skills', status: 'pending' },
				{ name: 'Verify', status: 'pending' },
			];
			const result = await applyAutoConfig();
			pipelineStages = [
				{ name: 'Backup', status: 'success' },
				{ name: 'Agents', status: 'success' },
				{ name: 'Skills', status: 'success' },
				{ name: 'Verify', status: 'success' },
			];
			applyResult = result;
		} catch (e: any) {
			applyError = e.message || 'Auto-configuration failed';
			pipelineStages = pipelineStages.map(s =>
				s.status === 'active' ? { ...s, status: 'failed' as const } : s
			);
		} finally {
			applying = false;
		}
	}

	function handleClose() {
		open = false;
		onClose();
	}
</script>

<Modal bind:open title="Auto-Configure Project" size="lg" onclose={handleClose}>
	{#snippet children()}
		<!-- Step indicator -->
		<div class="flex items-center gap-2 mb-4">
			<div class="flex items-center gap-1">
				<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
					{step === 1 ? 'bg-cyan-500 text-white' : 'bg-slate-700 text-slate-400'}">1</div>
				<span class="text-xs {step === 1 ? 'text-cyan-300' : 'text-slate-500'}">Detect & Recommend</span>
			</div>
			<div class="w-8 h-0.5 bg-slate-700"></div>
			<div class="flex items-center gap-1">
				<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
					{step === 2 ? 'bg-cyan-500 text-white' : 'bg-slate-700 text-slate-400'}">2</div>
				<span class="text-xs {step === 2 ? 'text-cyan-300' : 'text-slate-500'}">Review & Apply</span>
			</div>
		</div>

		{#if step === 1}
			<!-- Step 1: Detect + Recommend -->
			{#if !toolchain && !detecting}
				<div class="text-center py-8">
					<svg class="w-12 h-12 mx-auto mb-3 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
					</svg>
					<p class="text-sm text-slate-300 mb-4">Analyze your project to detect the toolchain and recommend agents & skills.</p>
					<button
						onclick={analyzeProject}
						class="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors"
					>
						Analyze Project
					</button>
				</div>
			{:else if detecting}
				<div class="flex items-center justify-center py-8 text-slate-400">
					<svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					<span class="text-sm">Analyzing project toolchain...</span>
				</div>
			{:else if detectError}
				<div class="text-center py-6">
					<div class="mb-3 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
						{detectError}
					</div>
					<button
						onclick={analyzeProject}
						class="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
					>
						Retry
					</button>
				</div>
			{:else if toolchain}
				<!-- Toolchain info -->
				<div class="mb-4 p-3 bg-slate-900 rounded-lg">
					<h4 class="text-xs font-semibold text-slate-400 uppercase mb-2">Detected Toolchain</h4>
					<div class="flex flex-wrap gap-2">
						<Badge text={toolchain.primary_language} variant="info" />
						{#each toolchain.frameworks as fw}
							<Badge text={fw.name} variant={confidenceColors[fw.confidence] || 'default'} />
						{/each}
						{#each toolchain.build_tools as bt}
							<Badge text={bt.name} variant="default" />
						{/each}
					</div>
					<div class="mt-2 text-xs text-slate-500">
						Overall confidence: <Badge text={toolchain.overall_confidence} variant={confidenceColors[toolchain.overall_confidence] || 'default'} size="sm" />
					</div>
				</div>

				{#if previewData}
					<!-- Recommended agents -->
					<div class="mb-3">
						<h4 class="text-xs font-semibold text-slate-400 uppercase mb-2">
							Recommended Agents ({previewData.recommendations.length})
						</h4>
						<div class="space-y-1 max-h-32 overflow-y-auto">
							{#each previewData.recommendations as rec}
								<div class="flex items-center justify-between px-2 py-1.5 bg-slate-900/50 rounded text-sm">
									<div class="flex flex-col min-w-0">
										<span class="text-slate-200">{rec.agent_name}</span>
										{#if rec.rationale}
											<span class="text-xs text-slate-500 truncate max-w-xs">{rec.rationale}</span>
										{/if}
									</div>
									<div class="flex items-center gap-2">
										<Badge
											text={rec.confidence_score >= 0.8 ? 'HIGH' : rec.confidence_score >= 0.5 ? 'MEDIUM' : 'LOW'}
											variant={rec.confidence_score >= 0.8 ? 'success' : rec.confidence_score >= 0.5 ? 'warning' : 'danger'}
											size="sm"
										/>
									</div>
								</div>
							{/each}
						</div>
						{#if previewData.recommendations.length === 0}
							<p class="text-sm text-slate-500 py-4 text-center">No agent recommendations for this project. Try adjusting the confidence threshold.</p>
						{/if}
					</div>

					{#if previewData.validation}
						<div class="mb-3 flex items-center gap-2 text-xs text-slate-500">
							<span>Validation:</span>
							{#if previewData.validation.is_valid}
								<Badge text="Passed" variant="success" size="sm" />
							{:else}
								<Badge text="{previewData.validation.error_count} errors" variant="danger" size="sm" />
							{/if}
							{#if previewData.validation.warning_count > 0}
								<Badge text="{previewData.validation.warning_count} warnings" variant="warning" size="sm" />
							{/if}
						</div>
					{/if}
				{/if}
			{/if}

		{:else}
			<!-- Step 2: Review + Apply -->
			{#if applyResult}
				<!-- Success state -->
				<div class="text-center py-4">
					<DeploymentPipeline stages={pipelineStages} />
					<div class="mt-4 px-3 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-sm text-emerald-300">
						Auto-configuration applied successfully.
						{#if applyResult.backup_id}
							<span class="block text-xs text-slate-400 mt-1">Backup ID: {applyResult.backup_id}</span>
						{/if}
					</div>
				</div>
			{:else}
				<!-- Diff view -->
				{#if previewData}
					<div class="space-y-3 max-h-48 overflow-y-auto mb-4">
						{#if previewData.would_deploy.length > 0}
							<div>
								<h4 class="text-xs font-semibold text-emerald-400 uppercase mb-1">
									Agents to Deploy ({previewData.would_deploy.length})
								</h4>
								<div class="flex flex-wrap gap-1">
									{#each previewData.would_deploy as name}
										<span class="px-2 py-0.5 text-xs rounded-full bg-emerald-500/10 text-emerald-300">+ {name}</span>
									{/each}
								</div>
							</div>
						{/if}
						{#if previewData.would_skip.length > 0}
							<div>
								<h4 class="text-xs font-semibold text-amber-400 uppercase mb-1">
									Agents Skipped — Low Confidence ({previewData.would_skip.length})
								</h4>
								<div class="flex flex-wrap gap-1">
									{#each previewData.would_skip as name}
										<span class="px-2 py-0.5 text-xs rounded-full bg-amber-500/10 text-amber-300">~ {name}</span>
									{/each}
								</div>
							</div>
						{/if}
						{#if previewData.would_deploy.length === 0 && previewData.would_skip.length === 0}
							<p class="text-sm text-slate-500 py-4 text-center">No agents matched the current configuration criteria.</p>
						{/if}
					</div>

					{#if previewData.estimated_deployment_time > 0}
						<div class="text-xs text-slate-500 mb-2">
							Estimated time: ~{Math.round(previewData.estimated_deployment_time)}s
						</div>
					{/if}
				{/if}

				<!-- Pipeline progress during apply -->
				{#if applying}
					<DeploymentPipeline stages={pipelineStages} />
				{/if}

				{#if applyError}
					<div class="mb-3 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-300">
						{applyError}
					</div>
				{/if}

				<!-- Confirm to apply -->
				{#if !applying}
					<div class="mt-3">
						<label class="block text-xs text-slate-400 mb-1.5">
							Type <span class="font-mono font-semibold text-slate-200">apply</span> to confirm
						</label>
						<input
							type="text"
							bind:value={confirmTyped}
							placeholder="apply"
							class="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-600 rounded-md
								text-slate-100 placeholder-slate-500
								focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
						/>
					</div>
				{/if}
			{/if}
		{/if}
	{/snippet}

	{#snippet footer()}
		{#if applyResult}
			<button
				onclick={handleClose}
				class="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors"
			>
				Done
			</button>
		{:else}
			<button
				onclick={step === 2 ? () => { step = 1; } : handleClose}
				class="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
			>
				{step === 2 ? 'Back' : 'Cancel'}
			</button>
			{#if step === 1}
				<button
					onclick={() => step = 2}
					disabled={!toolchain || !previewData}
					class="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700
						disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
				>
					Next: Review Changes
				</button>
			{:else}
				<button
					onclick={handleApply}
					disabled={!canApply || applying}
					class="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700
						disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors
						flex items-center gap-2"
				>
					{#if applying}
						<svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
					{/if}
					Apply Auto-Configuration
				</button>
			{/if}
		{/if}
	{/snippet}
</Modal>
