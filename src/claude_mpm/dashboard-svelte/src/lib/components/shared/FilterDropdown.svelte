<script lang="ts">
	export interface FilterOption {
		value: string;
		label: string;
		count?: number;
	}

	interface Props {
		label: string;
		options: FilterOption[];
		selected: string[];
		placeholder?: string;
		multiple?: boolean;
		onchange?: (selected: string[]) => void;
	}

	let { label, options, selected = $bindable([]), placeholder = 'All', multiple = true, onchange }: Props = $props();

	let open = $state(false);
	let focusedIndex = $state(-1);
	let buttonRef = $state<HTMLButtonElement | null>(null);
	let listRef = $state<HTMLDivElement | null>(null);

	let activeCount = $derived(selected.length);

	function toggleOpen() {
		open = !open;
		if (open) {
			focusedIndex = -1;
		}
	}

	function close() {
		open = false;
		focusedIndex = -1;
	}

	function toggleOption(value: string) {
		if (multiple) {
			if (selected.includes(value)) {
				selected = selected.filter(v => v !== value);
			} else {
				selected = [...selected, value];
			}
		} else {
			selected = selected.includes(value) ? [] : [value];
		}
		onchange?.(selected);
	}

	function handleButtonKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			close();
			buttonRef?.focus();
		} else if (e.key === 'ArrowDown' && !open) {
			e.preventDefault();
			open = true;
			focusedIndex = 0;
		} else if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			toggleOpen();
		}
	}

	function handleListKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			close();
			buttonRef?.focus();
		} else if (e.key === 'ArrowDown') {
			e.preventDefault();
			focusedIndex = Math.min(focusedIndex + 1, options.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			focusedIndex = Math.max(focusedIndex - 1, 0);
		} else if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			if (focusedIndex >= 0 && focusedIndex < options.length) {
				toggleOption(options[focusedIndex].value);
			}
		}
	}

	function handleDocumentClick(e: MouseEvent) {
		const target = e.target as HTMLElement;
		if (buttonRef && !buttonRef.contains(target) && listRef && !listRef.contains(target)) {
			close();
		}
	}

	$effect(() => {
		if (open) {
			document.addEventListener('click', handleDocumentClick, true);
			return () => document.removeEventListener('click', handleDocumentClick, true);
		}
	});
</script>

<div class="relative">
	<button
		bind:this={buttonRef}
		onclick={toggleOpen}
		onkeydown={handleButtonKeydown}
		class="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md border transition-colors
			{activeCount > 0
				? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-400'
				: 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600'}"
		aria-haspopup="listbox"
		aria-expanded={open}
	>
		<span>{label}</span>
		{#if activeCount > 0}
			<span class="inline-flex items-center justify-center w-4 h-4 text-[10px] font-bold rounded-full bg-cyan-500 text-white">
				{activeCount}
			</span>
		{/if}
		<svg class="w-3 h-3 ml-0.5 transition-transform {open ? 'rotate-180' : ''}" fill="currentColor" viewBox="0 0 20 20">
			<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
		</svg>
	</button>

	{#if open}
		<div
			bind:this={listRef}
			role="listbox"
			aria-multiselectable={multiple}
			aria-label="{label} filter options"
			onkeydown={handleListKeydown}
			tabindex="-1"
			class="absolute z-50 mt-1 min-w-[180px] max-h-60 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-lg"
		>
			{#if options.length === 0}
				<div class="px-3 py-2 text-xs text-slate-400 dark:text-slate-500">No options</div>
			{:else}
				{#each options as option, i}
					{@const isSelected = selected.includes(option.value)}
					{@const isFocused = focusedIndex === i}
					<div
						role="option"
						aria-selected={isSelected}
						onclick={() => toggleOption(option.value)}
						class="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer transition-colors
							{isFocused ? 'bg-cyan-50 dark:bg-cyan-900/20' : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'}
							{isSelected ? 'text-cyan-700 dark:text-cyan-300' : 'text-slate-700 dark:text-slate-300'}"
					>
						<span class="w-4 h-4 flex items-center justify-center rounded border flex-shrink-0
							{isSelected
								? 'bg-cyan-500 border-cyan-500'
								: 'border-slate-300 dark:border-slate-600'}">
							{#if isSelected}
								<svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
								</svg>
							{/if}
						</span>
						<span class="flex-1 truncate">{option.label}</span>
						{#if option.count !== undefined}
							<span class="text-[10px] text-slate-400 dark:text-slate-500">{option.count}</span>
						{/if}
					</div>
				{/each}
			{/if}
		</div>
	{/if}
</div>
