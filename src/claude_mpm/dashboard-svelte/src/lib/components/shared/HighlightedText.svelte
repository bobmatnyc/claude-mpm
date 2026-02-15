<script lang="ts">
	interface Props {
		text: string;
		query: string;
		maxLength?: number;
	}

	let { text, query, maxLength }: Props = $props();

	interface Segment {
		text: string;
		highlight: boolean;
	}

	let displayText = $derived(
		maxLength && text.length > maxLength
			? text.slice(0, maxLength - 3) + '...'
			: text
	);

	let segments = $derived.by<Segment[]>(() => {
		if (!query || !displayText) {
			return [{ text: displayText || '', highlight: false }];
		}
		const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
		const regex = new RegExp(`(${escaped})`, 'gi');
		const parts = displayText.split(regex);
		return parts
			.filter(p => p !== '')
			.map(part => ({
				text: part,
				highlight: regex.test(part) && (regex.lastIndex = 0, true)
			}))
			.map(part => ({
				text: part.text,
				highlight: part.text.toLowerCase() === query.toLowerCase()
			}));
	});
</script>

{#if !query || !displayText}
	<span>{displayText || ''}</span>
{:else}
	{#each segments as segment}
		{#if segment.highlight}
			<mark class="bg-yellow-200 dark:bg-yellow-500/30 text-inherit rounded px-0.5">{segment.text}</mark>
		{:else}
			<span>{segment.text}</span>
		{/if}
	{/each}
{/if}
