<script lang="ts">
	interface Props {
		value: string;
		placeholder?: string;
		delay?: number;
		onInput: (value: string) => void;
	}

	let { value = $bindable(''), placeholder = 'Search...', delay = 300, onInput }: Props = $props();

	let debounceTimer: ReturnType<typeof setTimeout>;
	let inputValue = $state(value);

	function handleInput(e: Event) {
		const target = e.target as HTMLInputElement;
		inputValue = target.value;
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			value = inputValue;
			onInput(inputValue);
		}, delay);
	}

	function clear() {
		inputValue = '';
		value = '';
		onInput('');
		clearTimeout(debounceTimer);
	}
</script>

<div class="relative">
	<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
	</svg>
	<input
		type="text"
		value={inputValue}
		{placeholder}
		oninput={handleInput}
		class="w-full pl-9 pr-8 py-2 text-sm bg-white dark:bg-slate-800
			border border-slate-200 dark:border-slate-700 rounded-md
			text-slate-900 dark:text-slate-100
			placeholder-slate-400 dark:placeholder-slate-500
			focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
	/>
	{#if inputValue}
		<button
			type="button"
			onclick={clear}
			class="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded-full
				text-slate-400 hover:text-slate-600 dark:hover:text-slate-300
				transition-colors"
			aria-label="Clear search"
		>
			<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	{/if}
</div>
