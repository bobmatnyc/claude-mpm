<script lang="ts">
	import type { SkillLink } from '$lib/stores/config/skillLinks.svelte';

	interface Props {
		skill: SkillLink;
	}

	let { skill }: Props = $props();

	const sourceColors: Record<string, { dot: string; bg: string }> = {
		frontmatter: {
			dot: 'bg-blue-500',
			bg: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
		},
		content_marker: {
			dot: 'bg-purple-500',
			bg: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
		},
		user_defined: {
			dot: 'bg-emerald-500',
			bg: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
		},
		inferred: {
			dot: 'bg-slate-400',
			bg: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
		},
	};

	let colors = $derived(sourceColors[skill.source.type] || sourceColors.inferred);
	let isWarning = $derived(!skill.is_deployed);

	let tooltipText = $derived(
		`Source: ${skill.source.label}` +
		(skill.is_auto_managed ? ' (auto-managed)' : '') +
		(!skill.is_deployed ? ' - Not deployed' : '')
	);
</script>

<span
	class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors
		{isWarning ? 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 ring-1 ring-amber-300 dark:ring-amber-700' : colors.bg}"
	title={tooltipText}
	role="listitem"
>
	<!-- Source indicator dot -->
	<span class="w-1.5 h-1.5 rounded-full flex-shrink-0 {isWarning ? 'bg-amber-500' : colors.dot}"></span>

	<span class="truncate max-w-[160px]">{skill.skill_name}</span>

	{#if skill.is_auto_managed}
		<span class="text-[10px] opacity-70 flex-shrink-0">auto</span>
	{/if}

	{#if isWarning}
		<svg class="w-3 h-3 flex-shrink-0 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
			<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
		</svg>
	{/if}
</span>
