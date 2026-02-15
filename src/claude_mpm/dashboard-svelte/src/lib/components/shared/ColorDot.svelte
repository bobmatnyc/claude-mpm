<script lang="ts">
	import { getColorClass } from '$lib/utils/colors';

	interface Props {
		color?: string;
		size?: 'sm' | 'md';
	}

	let { color = 'gray', size = 'sm' }: Props = $props();

	let sizeClass = $derived(size === 'md' ? 'w-3.5 h-3.5' : 'w-2 h-2');
	let bgClass = $derived(getColorClass(color));
	let displayColor = $derived(color || 'gray');
</script>

<span
	class="inline-block rounded-full flex-shrink-0 {sizeClass} {bgClass}"
	title={displayColor}
	role="img"
	aria-label="Color: {displayColor}"
></span>
