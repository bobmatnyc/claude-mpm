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

		skillLinksStore.set({
			data: result.data,
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
