<script lang="ts">
	interface MetadataItem {
		label: string;
		value: string;
		icon?: string;
	}

	interface Props {
		items: MetadataItem[];
	}

	let { items }: Props = $props();

	let visibleItems = $derived(items.filter(item => item.value || item.value === ''));
</script>

<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
	{#each visibleItems as item}
		<div class="bg-slate-50 dark:bg-slate-800/50 rounded-lg px-3 py-2">
			<p class="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
				{#if item.icon}
					<span class="text-xs">{item.icon}</span>
				{/if}
				{item.label}
			</p>
			<p class="text-sm font-medium text-slate-700 dark:text-slate-300">
				{item.value || '\u2014'}
			</p>
		</div>
	{/each}
</div>
