import { writable } from 'svelte/store';

export interface SkillSource {
	type: 'frontmatter' | 'content_marker' | 'user_defined' | 'inferred';
	label: string;
}

export interface SkillLink {
	skill_name: string;
	source: SkillSource;
	is_deployed: boolean;
	is_auto_managed: boolean;
}

export interface AgentSkillLinks {
	agent_name: string;
	is_deployed: boolean;
	skills: SkillLink[];
	skill_count: number;
}

export interface SkillLinksData {
	agents: AgentSkillLinks[];
	total_agents: number;
	total_skills: number;
}

interface SkillLinksState {
	data: SkillLinksData | null;
	loading: boolean;
	error: string | null;
	loaded: boolean;
}

const initialState: SkillLinksState = {
	data: null,
	loading: false,
	error: null,
	loaded: false,
};

export const skillLinksStore = writable<SkillLinksState>(initialState);

let currentState = initialState;
skillLinksStore.subscribe(s => { currentState = s; });

export async function loadSkillLinks(): Promise<void> {
	if (currentState.loaded && currentState.data) return;

	skillLinksStore.update(s => ({ ...s, loading: true, error: null }));

	try {
		const response = await fetch('/api/config/skill-links/');
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		}
		const result = await response.json();
		if (!result.success) {
			throw new Error(result.error || 'Failed to load skill links');
		}

		// Transform backend flat response into frontend SkillLinksData shape.
		// Backend returns: { by_agent: [...], by_skill: {...}, stats: {...}, total_agents }
		// Frontend expects: { agents: AgentSkillLinks[], total_agents, total_skills }
		const byAgent: Array<{
			agent_name: string;
			frontmatter_skills: string[];
			content_marker_skills: string[];
			total: number;
		}> = result.by_agent || [];

		// Build deployment status lookup from by_skill data.
		// Backend provides is_deployed per skill via the by_skill mapping.
		const bySkill: Record<string, { is_deployed?: boolean }> = result.by_skill || {};
		function isSkillDeployed(skillName: string): boolean {
			// Exact match first
			if (skillName in bySkill) {
				return bySkill[skillName].is_deployed ?? false;
			}
			// Suffix match (e.g., "toolchains-javascript-testing-playwright" matches "testing-playwright")
			for (const [key, val] of Object.entries(bySkill)) {
				if (key.endsWith(`-${skillName}`) || skillName.endsWith(`-${key}`)) {
					return val.is_deployed ?? false;
				}
			}
			// Not found in by_skill — assume not deployed
			return false;
		}

		// Determine agent deployment status from deployed agents list in by_skill data.
		// An agent referenced in by_agent is "deployed" if its agent file exists on disk.
		// Since by_agent comes from scanning deployed agent files, agents listed are deployed.
		const deployedAgentNames = new Set(byAgent.map(a => a.agent_name));

		const agents: AgentSkillLinks[] = byAgent.map((item) => {
			const fmSet = new Set(item.frontmatter_skills || []);
			const cmSet = new Set(item.content_marker_skills || []);

			const skills: SkillLink[] = [];

			// Add frontmatter skills
			for (const name of fmSet) {
				const inContent = cmSet.has(name);
				skills.push({
					skill_name: name,
					source: { type: 'frontmatter', label: 'Frontmatter' },
					is_deployed: isSkillDeployed(name),
					is_auto_managed: inContent,
				});
			}

			// Add content marker skills (only those not already in frontmatter)
			for (const name of cmSet) {
				if (!fmSet.has(name)) {
					skills.push({
						skill_name: name,
						source: { type: 'content_marker', label: 'Content Marker' },
						is_deployed: isSkillDeployed(name),
						is_auto_managed: false,
					});
				}
			}

			return {
				agent_name: item.agent_name,
				is_deployed: deployedAgentNames.has(item.agent_name),
				skills,
				skill_count: skills.length,
			};
		});

		const stats = result.stats || {};

		const data: SkillLinksData = {
			agents,
			total_agents: stats.total_agents ?? result.total_agents ?? agents.length,
			total_skills: stats.total_skills ?? 0,
		};

		skillLinksStore.set({
			data,
			loading: false,
			error: null,
			loaded: true,
		});
	} catch (e: any) {
		skillLinksStore.update(s => ({
			...s,
			loading: false,
			error: e.message || 'Failed to load skill links',
		}));
	}
}

export function invalidateSkillLinks(): void {
	skillLinksStore.set(initialState);
}
