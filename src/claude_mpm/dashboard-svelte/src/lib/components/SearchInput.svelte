<script lang="ts">
	interface Props {
		value: string;
		placeholder?: string;
		onInput: (value: string) => void;
	}

	let { value, placeholder = 'Search...', onInput }: Props = $props();

	let debounceTimer: ReturnType<typeof setTimeout>;

	function handleInput(e: Event) {
		const target = e.target as HTMLInputElement;
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			onInput(target.value);
		}, 200);
	}
</script>

<div class="relative">
	<svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
	</svg>
	<input
		type="text"
		{value}
		{placeholder}
		oninput={handleInput}
		class="w-full pl-9 pr-3 py-2 text-sm bg-white dark:bg-slate-800
			border border-slate-200 dark:border-slate-700 rounded-md
			text-slate-900 dark:text-slate-100
			placeholder-slate-400 dark:placeholder-slate-500
			focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
	/>
</div>
