<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		variant = 'default' as 'default' | 'success' | 'warning' | 'error' | 'info',
		size = 'sm' as 'sm' | 'md',
		children,
	}: {
		variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
		size?: 'sm' | 'md';
		children?: Snippet;
	} = $props();

	const variantClasses: Record<string, string> = {
		default: 'bg-slate-700 text-slate-300',
		success: 'bg-emerald-500/10 text-emerald-400',
		warning: 'bg-amber-500/10 text-amber-400',
		error: 'bg-red-500/10 text-red-400',
		info: 'bg-cyan-500/10 text-cyan-400',
	};

	const sizeClasses: Record<string, string> = {
		sm: 'text-xs px-2 py-0.5',
		md: 'text-sm px-2.5 py-1',
	};
</script>

<span
	class="inline-flex items-center rounded-full font-medium {variantClasses[variant]} {sizeClasses[size]}"
>
	{#if children}
		{@render children()}
	{/if}
</span>
