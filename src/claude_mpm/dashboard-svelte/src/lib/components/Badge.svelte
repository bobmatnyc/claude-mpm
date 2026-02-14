<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		text?: string;
		variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'error' | 'info';
		size?: 'sm' | 'md';
		children?: Snippet;
	}

	let { text, variant = 'default', size = 'sm', children }: Props = $props();

	const variantClasses: Record<string, string> = {
		default: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
		primary: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200',
		success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
		warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
		danger: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
		error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
		info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
	};

	const sizeClasses: Record<string, string> = {
		sm: 'px-2 py-0.5 text-xs',
		md: 'px-2.5 py-1 text-sm',
	};
</script>

<span class="inline-flex items-center rounded-full font-medium {variantClasses[variant] || variantClasses.default} {sizeClasses[size]}">
	{#if children}
		{@render children()}
	{:else if text}
		{text}
	{/if}
</span>
