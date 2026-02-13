<script lang="ts">
	import type { AgentSkillLinks } from '$lib/stores/config/skillLinks.svelte';
	import SkillChip from './SkillChip.svelte';
	import EmptyState from '$lib/components/shared/EmptyState.svelte';

	interface Props {
		agent: AgentSkillLinks | null;
	}

	let { agent }: Props = $props();

	interface GroupedSkills {
		label: string;
		key: string;
		skills: AgentSkillLinks['skills'];
	}

	let grouped = $derived.by(() => {
		if (!agent || agent.skills.length === 0) return [];

		const groups: Record<string, GroupedSkills> = {};
		const order = ['user_defined', 'frontmatter', 'content_marker', 'inferred'];
		const labels: Record<string, string> = {
			user_defined: 'User Defined',
			frontmatter: 'Required (Frontmatter)',
			content_marker: 'Content Markers',
			inferred: 'Inferred',
		};

		for (const skill of agent.skills) {
			const key = skill.source.type;
			if (!groups[key]) {
				groups[key] = {
					label: labels[key] || key,
					key,
					skills: [],
				};
			}
			groups[key].skills.push(skill);
		}

		return order
			.filter(k => groups[k])
			.map(k => groups[k]);
	});
</script>

<div class="flex flex-col h-full">
	{#if !agent}
		<EmptyState message="Select an agent to view its skill links" />
	{:else if agent.skills.length === 0}
		<EmptyState message="This agent has no linked skills" />
	{:else}
		<div class="p-4 border-b border-slate-200 dark:border-slate-700">
			<h3 class="text-sm font-semibold text-slate-900 dark:text-slate-100">
				{agent.agent_name}
			</h3>
			<p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
				{agent.skill_count} skill{agent.skill_count !== 1 ? 's' : ''} linked
				{#if !agent.is_deployed}
					<span class="text-amber-500 dark:text-amber-400 ml-1">(not deployed)</span>
				{/if}
			</p>
		</div>

		<div class="flex-1 overflow-y-auto p-4 space-y-4" role="list" aria-label="Skills for {agent.agent_name}">
			{#each grouped as group (group.key)}
				<div>
					<h4 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
						{group.label}
					</h4>
					<div class="flex flex-wrap gap-1.5">
						{#each group.skills as skill (skill.skill_name)}
							<SkillChip {skill} />
						{/each}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
