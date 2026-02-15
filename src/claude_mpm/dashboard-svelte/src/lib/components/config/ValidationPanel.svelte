<script lang="ts">
	import { onMount } from 'svelte';
	import ValidationIssueCard from './ValidationIssueCard.svelte';

	interface ValidationIssue {
		severity: 'error' | 'warning' | 'info';
		message: string;
		path?: string;
		suggestion?: string;
	}

	interface ValidationResult {
		valid: boolean;
		issues: ValidationIssue[];
	}

	let expanded = $state(false);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let result = $state<ValidationResult | null>(null);

	let issues = $derived(result?.issues ?? []);
	let errorCount = $derived(issues.filter(i => i.severity === 'error').length);
	let warningCount = $derived(issues.filter(i => i.severity === 'warning').length);
	let infoCount = $derived(issues.filter(i => i.severity === 'info').length);

	let sortedIssues = $derived.by(() => {
		if (issues.length === 0) return [];
		const order: Record<string, number> = { error: 0, warning: 1, info: 2 };
		return [...issues].sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3));
	});

	let summaryText = $derived.by(() => {
		const parts: string[] = [];
		if (errorCount > 0) parts.push(`${errorCount} error${errorCount !== 1 ? 's' : ''}`);
		if (warningCount > 0) parts.push(`${warningCount} warning${warningCount !== 1 ? 's' : ''}`);
		if (infoCount > 0) parts.push(`${infoCount} info`);
		return parts.length > 0 ? parts.join(', ') : '';
	});

	async function fetchValidation() {
		loading = true;
		error = null;
		try {
			const response = await fetch('/api/config/validate');
			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}
			const data = await response.json();
			if (!data.success) {
				throw new Error(data.error || 'Validation failed');
			}
			// Backend returns flat: { success, valid, issues, summary }
			result = { valid: data.valid, issues: data.issues || [] };
		} catch (e: any) {
			error = e.message || 'Failed to validate configuration';
		} finally {
			loading = false;
		}
	}

	onMount(fetchValidation);

	function toggleExpanded() {
		expanded = !expanded;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && expanded) {
			expanded = false;
		}
	}
</script>

<div class="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden" role="region" aria-label="Configuration validation">
	{#if loading}
		<div class="flex items-center gap-2 px-4 py-3">
			<svg class="animate-spin w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
			</svg>
			<span class="text-sm text-slate-500 dark:text-slate-400">Validating configuration...</span>
		</div>
	{:else if error}
		<div class="flex items-center gap-2 px-4 py-3 bg-red-50 dark:bg-red-900/20">
			<svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
			<span class="text-sm text-red-600 dark:text-red-400">{error}</span>
			<button
				onclick={fetchValidation}
				class="ml-auto text-xs text-cyan-500 hover:text-cyan-400 transition-colors"
			>
				Retry
			</button>
		</div>
	{:else if result?.valid && issues.length === 0}
		<!-- All valid -->
		<div class="flex items-center gap-2 px-4 py-3 bg-emerald-50 dark:bg-emerald-900/20">
			<svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
			<span class="text-sm font-medium text-emerald-700 dark:text-emerald-300">Configuration is healthy</span>
		</div>
	{:else}
		<!-- Collapsible header -->
		<button
			onclick={toggleExpanded}
			onkeydown={handleKeydown}
			class="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
			aria-expanded={expanded}
			aria-controls="validation-issues"
		>
			<div class="flex items-center gap-2">
				{#if errorCount > 0}
					<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300">
						{errorCount} error{errorCount !== 1 ? 's' : ''}
					</span>
				{/if}
				{#if warningCount > 0}
					<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
						{warningCount} warning{warningCount !== 1 ? 's' : ''}
					</span>
				{/if}
				{#if infoCount > 0}
					<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
						{infoCount} info
					</span>
				{/if}
			</div>

			<svg
				class="w-4 h-4 text-slate-400 transition-transform {expanded ? 'rotate-180' : ''}"
				fill="currentColor" viewBox="0 0 20 20"
			>
				<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
			</svg>
		</button>

		<!-- Expanded issue list -->
		{#if expanded}
			<div id="validation-issues" class="px-4 pb-4 space-y-2 border-t border-slate-200 dark:border-slate-700 pt-3 max-h-[40vh] overflow-y-auto" role="list">
				{#each sortedIssues as issue, i (i)}
					<ValidationIssueCard {issue} />
				{/each}
			</div>
		{/if}
	{/if}
</div>
