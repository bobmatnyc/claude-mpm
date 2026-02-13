<script lang="ts">
	let {
		value = 0,
		indeterminate = false,
		label = '',
		size = 'sm' as 'sm' | 'md',
	}: {
		value?: number;
		indeterminate?: boolean;
		label?: string;
		size?: 'sm' | 'md';
	} = $props();

	const sizeClasses: Record<string, string> = {
		sm: 'h-1',
		md: 'h-2',
	};

	let clampedValue = $derived(Math.max(0, Math.min(100, value)));
</script>

<div class="w-full">
	{#if label}
		<div class="flex justify-between items-center mb-1">
			<span class="text-xs text-slate-400">{label}</span>
			{#if !indeterminate}
				<span class="text-xs text-slate-400 font-mono">{clampedValue}%</span>
			{/if}
		</div>
	{/if}
	<div class="bg-slate-700 rounded-full overflow-hidden {sizeClasses[size]}">
		{#if indeterminate}
			<div class="h-full bg-cyan-500 rounded-full indeterminate-bar"></div>
		{:else}
			<div
				class="h-full bg-cyan-500 rounded-full transition-all duration-300"
				style="width: {clampedValue}%"
			></div>
		{/if}
	</div>
</div>

<style>
	.indeterminate-bar {
		width: 40%;
		animation: indeterminate-slide 1.5s ease-in-out infinite;
	}

	@keyframes indeterminate-slide {
		0% {
			transform: translateX(-100%);
		}
		50% {
			transform: translateX(200%);
		}
		100% {
			transform: translateX(-100%);
		}
	}
</style>
