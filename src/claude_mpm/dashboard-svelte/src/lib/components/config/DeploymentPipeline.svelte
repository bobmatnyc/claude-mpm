<script lang="ts">
	export interface PipelineStage {
		name: string;
		status: 'pending' | 'active' | 'success' | 'failed';
		detail?: string;
	}

	let { stages, compact = false }: {
		stages: PipelineStage[];
		compact?: boolean;
	} = $props();

	const statusColors: Record<string, { circle: string; connector: string; text: string }> = {
		pending: {
			circle: 'bg-slate-600 border-slate-500',
			connector: 'bg-slate-600',
			text: 'text-slate-400',
		},
		active: {
			circle: 'bg-cyan-500/20 border-cyan-400 animate-pulse',
			connector: 'bg-cyan-500/50',
			text: 'text-cyan-300',
		},
		success: {
			circle: 'bg-emerald-500/20 border-emerald-400',
			connector: 'bg-emerald-500',
			text: 'text-emerald-300',
		},
		failed: {
			circle: 'bg-red-500/20 border-red-400',
			connector: 'bg-red-500',
			text: 'text-red-300',
		},
	};
</script>

<div class="flex items-center gap-0 {compact ? 'py-1' : 'py-3'}">
	{#each stages as stage, i (stage.name)}
		{@const colors = statusColors[stage.status]}

		<!-- Connector (before stage, except first) -->
		{#if i > 0}
			<div class="flex-shrink-0 {compact ? 'w-4 h-0.5' : 'w-8 h-0.5'} {colors.connector} transition-colors duration-300"></div>
		{/if}

		<!-- Stage circle + label -->
		<div class="flex flex-col items-center {compact ? 'gap-0.5' : 'gap-1'}">
			<div
				class="flex items-center justify-center rounded-full border-2 transition-all duration-300
					{compact ? 'w-5 h-5' : 'w-8 h-8'}
					{colors.circle}"
				title={stage.detail || stage.name}
			>
				{#if stage.status === 'success'}
					<svg class="{compact ? 'w-3 h-3' : 'w-4 h-4'} text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
					</svg>
				{:else if stage.status === 'failed'}
					<svg class="{compact ? 'w-3 h-3' : 'w-4 h-4'} text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12" />
					</svg>
				{:else if stage.status === 'active'}
					<svg class="{compact ? 'w-3 h-3' : 'w-4 h-4'} text-cyan-400 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
				{:else}
					<div class="{compact ? 'w-1.5 h-1.5' : 'w-2 h-2'} rounded-full bg-slate-500"></div>
				{/if}
			</div>
			<span class="{compact ? 'text-[10px]' : 'text-xs'} font-medium {colors.text} whitespace-nowrap">
				{stage.name}
			</span>
			{#if !compact && stage.detail}
				<span class="text-[10px] text-slate-500 max-w-[80px] truncate">{stage.detail}</span>
			{/if}
		</div>
	{/each}
</div>
