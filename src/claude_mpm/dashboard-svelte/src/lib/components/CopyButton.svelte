<script lang="ts">
	/**
	 * Reusable copy button component with visual feedback
	 *
	 * Usage:
	 * <CopyButton text="content to copy" />
	 * <CopyButton text="content" label="Copy Path" />
	 * <CopyButton text="content" size="sm" />
	 */

	let {
		text,
		label = '',
		size = 'md',
		className = ''
	}: {
		text: string;
		label?: string;
		size?: 'sm' | 'md' | 'lg';
		className?: string;
	} = $props();

	let copied = $state(false);
	let copyTimeout: ReturnType<typeof setTimeout> | null = null;

	async function copyToClipboard() {
		try {
			await navigator.clipboard.writeText(text);
			copied = true;

			// Reset after 2 seconds
			if (copyTimeout) clearTimeout(copyTimeout);
			copyTimeout = setTimeout(() => {
				copied = false;
			}, 2000);
		} catch (error) {
			console.error('Failed to copy to clipboard:', error);
		}
	}

	// Size mappings
	const sizeClasses = {
		sm: 'text-xs px-1.5 py-0.5',
		md: 'text-sm px-2 py-1',
		lg: 'text-base px-2.5 py-1.5'
	};

	const iconSizes = {
		sm: 'w-3 h-3',
		md: 'w-4 h-4',
		lg: 'w-5 h-5'
	};
</script>

<button
	onclick={copyToClipboard}
	class="inline-flex items-center gap-1.5 rounded transition-colors font-medium
		{sizeClasses[size]}
		{copied
			? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
			: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'}
		{className}"
	title={copied ? 'Copied!' : 'Copy to clipboard'}
	type="button"
>
	{#if copied}
		<!-- Checkmark icon -->
		<svg class="{iconSizes[size]}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
		</svg>
		{#if label}
			<span>Copied!</span>
		{/if}
	{:else}
		<!-- Copy icon -->
		<svg class="{iconSizes[size]}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
		</svg>
		{#if label}
			<span>{label}</span>
		{/if}
	{/if}
</button>
