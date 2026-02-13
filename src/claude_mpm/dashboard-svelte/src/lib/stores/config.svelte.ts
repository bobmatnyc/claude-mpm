import { writable } from 'svelte/store';

// --- Types ---

export interface ProjectSummary {
	agents: { deployed: number; available: number };
	skills: { deployed: number; available: number };
	sources: { agent_sources: number; skill_sources: number };
	deployment_mode: string;
}

export interface DeployedAgent {
	name: string;
	location: string;
	path: string;
	version: string;
	type: string;
	specializations?: string[];
	is_core: boolean;
}

export interface AvailableAgent {
	agent_id: string;
	name: string;
	description: string;
	version: string;
	source: string;
	source_url: string;
	priority: number;
	category: string;
	tags: string[];
	is_deployed: boolean;
}

export interface DeployedSkill {
	name: string;
	path: string;
	description: string;
	category: string;
	collection: string;
	is_user_requested: boolean;
	deploy_mode: 'agent_referenced' | 'user_defined';
	deploy_date: string;
}

export interface AvailableSkill {
	name: string;
	description: string;
	category: string;
	collection: string;
	is_deployed: boolean;
}

export interface ConfigSource {
	id: string;
	type: 'agent' | 'skill';
	url: string;
	subdirectory?: string;
	branch?: string;
	enabled: boolean;
	priority: number;
}

export interface LoadingState {
	summary: boolean;
	deployedAgents: boolean;
	availableAgents: boolean;
	deployedSkills: boolean;
	availableSkills: boolean;
	sources: boolean;
}

export interface ConfigError {
	resource: string;
	message: string;
	timestamp: number;
}

// --- Stores ---

export const projectSummary = writable<ProjectSummary | null>(null);
export const deployedAgents = writable<DeployedAgent[]>([]);
export const availableAgents = writable<AvailableAgent[]>([]);
export const deployedSkills = writable<DeployedSkill[]>([]);
export const availableSkills = writable<AvailableSkill[]>([]);
export const configSources = writable<ConfigSource[]>([]);
export const configLoading = writable<LoadingState>({
	summary: false,
	deployedAgents: false,
	availableAgents: false,
	deployedSkills: false,
	availableSkills: false,
	sources: false,
});
export const configErrors = writable<ConfigError[]>([]);

// --- Fetch Functions ---

const API_BASE = '/api/config';

async function fetchJSON(url: string): Promise<any> {
	const response = await fetch(url);
	if (!response.ok) {
		throw new Error(`HTTP ${response.status}: ${response.statusText}`);
	}
	const data = await response.json();
	if (!data.success) {
		throw new Error(data.error || 'Unknown error');
	}
	return data;
}

function addError(resource: string, message: string) {
	configErrors.update(errs => [
		...errs.slice(-4), // Keep last 5 errors max
		{ resource, message, timestamp: Date.now() },
	]);
}

export async function fetchProjectSummary() {
	configLoading.update(l => ({ ...l, summary: true }));
	try {
		const data = await fetchJSON(`${API_BASE}/project/summary`);
		projectSummary.set(data.data);
	} catch (e: any) {
		addError('summary', e.message);
	} finally {
		configLoading.update(l => ({ ...l, summary: false }));
	}
}

export async function fetchDeployedAgents() {
	configLoading.update(l => ({ ...l, deployedAgents: true }));
	try {
		const data = await fetchJSON(`${API_BASE}/agents/deployed`);
		deployedAgents.set(data.agents);
	} catch (e: any) {
		addError('deployedAgents', e.message);
	} finally {
		configLoading.update(l => ({ ...l, deployedAgents: false }));
	}
}

export async function fetchAvailableAgents(search?: string) {
	configLoading.update(l => ({ ...l, availableAgents: true }));
	try {
		const url = search
			? `${API_BASE}/agents/available?search=${encodeURIComponent(search)}`
			: `${API_BASE}/agents/available`;
		const data = await fetchJSON(url);
		availableAgents.set(data.agents);
	} catch (e: any) {
		addError('availableAgents', e.message);
	} finally {
		configLoading.update(l => ({ ...l, availableAgents: false }));
	}
}

export async function fetchDeployedSkills() {
	configLoading.update(l => ({ ...l, deployedSkills: true }));
	try {
		const data = await fetchJSON(`${API_BASE}/skills/deployed`);
		deployedSkills.set(data.skills);
	} catch (e: any) {
		addError('deployedSkills', e.message);
	} finally {
		configLoading.update(l => ({ ...l, deployedSkills: false }));
	}
}

export async function fetchAvailableSkills(collection?: string) {
	configLoading.update(l => ({ ...l, availableSkills: true }));
	try {
		const url = collection
			? `${API_BASE}/skills/available?collection=${encodeURIComponent(collection)}`
			: `${API_BASE}/skills/available`;
		const data = await fetchJSON(url);
		availableSkills.set(data.skills);
	} catch (e: any) {
		addError('availableSkills', e.message);
	} finally {
		configLoading.update(l => ({ ...l, availableSkills: false }));
	}
}

export async function fetchSources() {
	configLoading.update(l => ({ ...l, sources: true }));
	try {
		const data = await fetchJSON(`${API_BASE}/sources`);
		configSources.set(data.sources);
	} catch (e: any) {
		addError('sources', e.message);
	} finally {
		configLoading.update(l => ({ ...l, sources: false }));
	}
}

/** Fetch all config data. Called when config tab is first opened. */
export async function fetchAllConfig() {
	await Promise.all([
		fetchProjectSummary(),
		fetchDeployedAgents(),
		fetchSources(),
	]);
	// Defer heavier fetches (these may take 2-5 seconds)
	fetchAvailableAgents();
	fetchDeployedSkills();
	fetchAvailableSkills();
}
