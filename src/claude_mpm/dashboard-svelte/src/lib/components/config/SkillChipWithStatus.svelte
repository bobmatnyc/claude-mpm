<script lang="ts">
	interface Props {
		name: string;
		isDeployed: boolean;
		onclick?: () => void;
	}

	let { name, isDeployed, onclick }: Props = $props();

	let isClickable = $derived(!!onclick);
</script>

{#if isClickable}
	<button
		onclick={onclick}
		class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full transition-colors
			{isDeployed
				? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 hover:bg-green-100 dark:hover:bg-green-900/40'
				: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/40'}
			cursor-pointer"
		title="{name} - {isDeployed ? 'Deployed' : 'Not deployed'}"
	>
		{#if isDeployed}
			<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
				<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
			</svg>
		{:else}
			<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
				<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
			</svg>
		{/if}
		<span class="truncate max-w-[120px]">{name}</span>
	</button>
{:else}
	<span
		class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full
			{isDeployed
				? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
				: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'}"
		title="{name} - {isDeployed ? 'Deployed' : 'Not deployed'}"
	>
		{#if isDeployed}
			<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
				<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
			</svg>
		{:else}
			<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
				<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
			</svg>
		{/if}
		<span class="truncate max-w-[120px]">{name}</span>
	</span>
{/if}
