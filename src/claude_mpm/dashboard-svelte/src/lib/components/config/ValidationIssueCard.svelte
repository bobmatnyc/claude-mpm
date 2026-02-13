<script lang="ts">
	interface ValidationIssue {
		severity: 'error' | 'warning' | 'info';
		message: string;
		path?: string;
		suggestion?: string;
	}

	interface Props {
		issue: ValidationIssue;
	}

	let { issue }: Props = $props();

	let expanded = $state(false);

	const severityConfig: Record<string, { icon: string; textClass: string; bgClass: string; borderClass: string }> = {
		error: {
			icon: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
			textClass: 'text-red-600 dark:text-red-400',
			bgClass: 'bg-red-50 dark:bg-red-900/20',
			borderClass: 'border-red-200 dark:border-red-800',
		},
		warning: {
			icon: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z',
			textClass: 'text-amber-600 dark:text-amber-400',
			bgClass: 'bg-amber-50 dark:bg-amber-900/20',
			borderClass: 'border-amber-200 dark:border-amber-800',
		},
		info: {
			icon: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
			textClass: 'text-blue-600 dark:text-blue-400',
			bgClass: 'bg-blue-50 dark:bg-blue-900/20',
			borderClass: 'border-blue-200 dark:border-blue-800',
		},
	};

	let config = $derived(severityConfig[issue.severity] || severityConfig.info);
</script>

<div class="rounded-lg border {config.borderClass} {config.bgClass} p-3">
	<div class="flex items-start gap-2.5">
		<!-- Severity icon -->
		<svg class="w-4 h-4 mt-0.5 flex-shrink-0 {config.textClass}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={config.icon} />
		</svg>

		<div class="flex-1 min-w-0">
			<!-- Message -->
			<p class="text-sm {config.textClass}">{issue.message}</p>

			<!-- Config path -->
			{#if issue.path}
				<p class="mt-1 text-xs font-mono text-slate-500 dark:text-slate-400 break-all">{issue.path}</p>
			{/if}

			<!-- Expandable suggestion -->
			{#if issue.suggestion}
				<button
					onclick={() => expanded = !expanded}
					class="mt-1.5 flex items-center gap-1 text-xs font-medium text-slate-500 dark:text-slate-400
						hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
					aria-expanded={expanded}
				>
					<svg class="w-3 h-3 transition-transform {expanded ? 'rotate-90' : ''}" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
					</svg>
					Suggestion
				</button>

				{#if expanded}
					<div class="mt-1.5 pl-4 text-xs text-slate-600 dark:text-slate-300 border-l-2 border-slate-300 dark:border-slate-600">
						{issue.suggestion}
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>
