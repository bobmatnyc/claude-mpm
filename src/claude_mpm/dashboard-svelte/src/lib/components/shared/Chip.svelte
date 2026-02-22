<script lang="ts">
	interface Props {
		label: string;
		variant?: 'default' | 'warning' | 'info' | 'success';
		size?: 'sm' | 'md';
		removable?: boolean;
		onRemove?: () => void;
	}

	let { label, variant = 'default', size = 'sm', removable = false, onRemove }: Props = $props();

	const variantClasses: Record<string, string> = {
		default: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
		warning: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
		info: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
		success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
	};

	const sizeClasses: Record<string, string> = {
		sm: 'text-xs px-2 py-0.5 gap-1',
		md: 'text-sm px-2.5 py-1 gap-1.5',
	};
</script>

<span
	class="inline-flex items-center rounded-full font-medium {variantClasses[variant]} {sizeClasses[size]}"
>
	{label}
	{#if removable}
		<button
			type="button"
			onclick={(e) => { e.stopPropagation(); onRemove?.(); }}
			class="ml-0.5 -mr-0.5 p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
			aria-label="Remove {label}"
		>
			<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	{/if}
</span>
