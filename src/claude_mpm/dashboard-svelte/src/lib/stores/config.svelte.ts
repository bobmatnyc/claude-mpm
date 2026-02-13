import { writable, get } from 'svelte/store';
import { toastStore } from './toast.svelte';

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

export interface SyncState {
	status: 'idle' | 'syncing' | 'completed' | 'failed';
	progress: number;
	lastSync: string | null;
	error: string | null;
	jobId: string | null;
}

export interface ConfigEvent {
	type: string;
	operation: string;
	entity_type: string;
	entity_id: string | null;
	status: string;
	data: Record<string, any>;
	timestamp: string;
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

// --- Phase 2: Mutation state ---
export const syncStatus = writable<Record<string, SyncState>>({});
export const mutating = writable(false);

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

// --- Phase 2: Mutation Functions ---

/**
 * Add a new source (agent or skill).
 * POST /api/config/sources/{type}
 */
export async function addSource(type: 'agent' | 'skill', data: Record<string, any>): Promise<void> {
	mutating.set(true);
	try {
		const response = await fetch(`${API_BASE}/sources/${type}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(data),
		});
		const result = await response.json();
		if (!result.success) {
			throw new Error(result.error || 'Failed to add source');
		}
		await fetchSources();
		toastStore.success(result.message || `Source added successfully`);
	} catch (e: any) {
		toastStore.error(e.message || 'Failed to add source');
		throw e;
	} finally {
		mutating.set(false);
	}
}

/**
 * Update an existing source.
 * PATCH /api/config/sources/{type}?id={encodedId}
 */
export async function updateSource(type: 'agent' | 'skill', id: string, updates: Record<string, any>): Promise<void> {
	mutating.set(true);
	const encodedId = encodeURIComponent(id);
	try {
		const response = await fetch(`${API_BASE}/sources/${type}?id=${encodedId}`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(updates),
		});
		const result = await response.json();
		if (!result.success) {
			throw new Error(result.error || 'Failed to update source');
		}
		await fetchSources();
		toastStore.success(result.message || 'Source updated');
	} catch (e: any) {
		toastStore.error(e.message || 'Failed to update source');
		throw e;
	} finally {
		mutating.set(false);
	}
}

/**
 * Remove a source.
 * DELETE /api/config/sources/{type}?id={encodedId}
 */
export async function removeSource(type: 'agent' | 'skill', id: string): Promise<void> {
	mutating.set(true);
	const encodedId = encodeURIComponent(id);
	try {
		const response = await fetch(`${API_BASE}/sources/${type}?id=${encodedId}`, {
			method: 'DELETE',
		});
		const result = await response.json();
		if (!result.success) {
			throw new Error(result.error || 'Failed to remove source');
		}
		await fetchSources();
		toastStore.success(result.message || 'Source removed');
	} catch (e: any) {
		toastStore.error(e.message || 'Failed to remove source');
		throw e;
	} finally {
		mutating.set(false);
	}
}

/**
 * Sync a single source.
 * POST /api/config/sources/{type}/sync?id={encodedId}
 * Returns immediately (202). Progress via Socket.IO.
 */
export async function syncSource(type: 'agent' | 'skill', id: string, force: boolean = false): Promise<void> {
	const encodedId = encodeURIComponent(id);
	const forceParam = force ? '&force=true' : '';
	try {
		const response = await fetch(
			`${API_BASE}/sources/${type}/sync?id=${encodedId}${forceParam}`,
			{ method: 'POST' }
		);
		const result = await response.json();
		if (!result.success) {
			throw new Error(result.error || 'Failed to start sync');
		}
		// Update local sync state -- progress will come via Socket.IO
		syncStatus.update((s) => ({
			...s,
			[id]: {
				status: 'syncing',
				progress: 0,
				lastSync: null,
				error: null,
				jobId: result.job_id,
			},
		}));
	} catch (e: any) {
		toastStore.error(e.message || 'Failed to start sync');
	}
}

/**
 * Sync all enabled sources.
 * POST /api/config/sources/sync-all
 */
export async function syncAllSources(force: boolean = false): Promise<void> {
	try {
		const forceParam = force ? '?force=true' : '';
		const response = await fetch(`${API_BASE}/sources/sync-all${forceParam}`, {
			method: 'POST',
		});
		const result = await response.json();
		if (!result.success) {
			throw new Error(result.error || 'Failed to start sync');
		}
		toastStore.info(result.message || 'Sync started for all sources');
	} catch (e: any) {
		toastStore.error(e.message || 'Failed to start sync');
	}
}

// --- Phase 3: Deployment Types ---

export interface DeployResult {
	success: boolean;
	message: string;
	agent_name?: string;
	skill_name?: string;
	verification?: Record<string, any>;
	backup_id?: string;
	active_sessions_warning?: boolean;
}

export interface ModeImpactPreview {
	skills_added: string[];
	skills_removed: string[];
	skills_unchanged: string[];
	total_after_switch: number;
	warning?: string;
}

export interface ToolchainResult {
	primary_language: string;
	frameworks: { name: string; confidence: string }[];
	build_tools: { name: string; confidence: string }[];
	overall_confidence: string;
}

export interface AutoConfigPreview {
	recommended_agents: { name: string; confidence: string; rationale: string; selected?: boolean }[];
	recommended_skills: { name: string; confidence: string; rationale: string; selected?: boolean }[];
	changes: { agents_to_add: string[]; agents_to_remove: string[]; skills_to_add: string[]; skills_to_remove: string[] };
	rationale: Record<string, string>;
}

export interface ActiveSessionInfo {
	active: boolean;
	sessions: { pid: number; started: string }[];
	warning?: string;
}

// --- Phase 3: Deployment Mutation Functions ---

async function mutateJSON(url: string, method: string, body?: any): Promise<any> {
	const options: RequestInit = { method, headers: { 'Content-Type': 'application/json' } };
	if (body !== undefined) options.body = JSON.stringify(body);
	const response = await fetch(url, options);
	const result = await response.json();
	if (!response.ok && !result.success) {
		const err = new Error(result.error || `HTTP ${response.status}`);
		(err as any).status = response.status;
		(err as any).data = result;
		throw err;
	}
	return result;
}

/** Deploy a single agent. POST /api/config/agents/deploy */
export async function deployAgent(agent_name: string, source_id?: string, force?: boolean): Promise<DeployResult> {
	mutating.set(true);
	try {
		const body: Record<string, any> = { agent_name };
		if (source_id) body.source_id = source_id;
		if (force) body.force = true;
		const result = await mutateJSON(`${API_BASE}/agents/deploy`, 'POST', body);
		await Promise.all([fetchDeployedAgents(), fetchAvailableAgents()]);
		toastStore.success(result.message || `Agent ${agent_name} deployed`);
		return result;
	} catch (e: any) {
		toastStore.error(e.message || `Failed to deploy ${agent_name}`);
		throw e;
	} finally {
		mutating.set(false);
	}
}

/** Undeploy a single agent. DELETE /api/config/agents/{name} */
export async function undeployAgent(agent_name: string): Promise<DeployResult> {
	mutating.set(true);
	try {
		const result = await mutateJSON(`${API_BASE}/agents/${encodeURIComponent(agent_name)}`, 'DELETE');
		await Promise.all([fetchDeployedAgents(), fetchAvailableAgents()]);
		toastStore.success(result.message || `Agent ${agent_name} undeployed`);
		return result;
	} catch (e: any) {
		toastStore.error(e.message || `Failed to undeploy ${agent_name}`);
		throw e;
	} finally {
		mutating.set(false);
	}
}

/** Batch deploy agents. POST /api/config/agents/deploy-collection */
export async function batchDeployAgents(agents: string[], source_id?: string, force?: boolean): Promise<any> {
	mutating.set(true);
	try {
		const body: Record<string, any> = { agents };
		if (source_id) body.source_id = source_id;
		if (force) body.force = true;
		const result = await mutateJSON(`${API_BASE}/agents/deploy-collection`, 'POST', body);
		await Promise.all([fetchDeployedAgents(), fetchAvailableAgents()]);
		toastStore.success(result.message || `${agents.length} agents deployed`);
		return result;
	} catch (e: any) {
		toastStore.error(e.message || 'Failed to deploy agents');
		throw e;
	} finally {
		mutating.set(false);
	}
}

/** Deploy a single skill. POST /api/config/skills/deploy */
export async function deploySkill(skill_name: string, mark_user_requested?: boolean, force?: boolean): Promise<DeployResult> {
	mutating.set(true);
	try {
		const body: Record<string, any> = { skill_name };
		if (mark_user_requested) body.mark_user_requested = true;
		if (force) body.force = true;
		const result = await mutateJSON(`${API_BASE}/skills/deploy`, 'POST', body);
		await Promise.all([fetchDeployedSkills(), fetchAvailableSkills()]);
		toastStore.success(result.message || `Skill ${skill_name} deployed`);
		return result;
	} catch (e: any) {
		toastStore.error(e.message || `Failed to deploy ${skill_name}`);
		throw e;
	} finally {
		mutating.set(false);
	}
}

/** Undeploy a single skill. DELETE /api/config/skills/{name} */
export async function undeploySkill(skill_name: string): Promise<DeployResult> {
	mutating.set(true);
	try {
		const result = await mutateJSON(`${API_BASE}/skills/${encodeURIComponent(skill_name)}`, 'DELETE');
		await Promise.all([fetchDeployedSkills(), fetchAvailableSkills()]);
		toastStore.success(result.message || `Skill ${skill_name} undeployed`);
		return result;
	} catch (e: any) {
		toastStore.error(e.message || `Failed to undeploy ${skill_name}`);
		throw e;
	} finally {
		mutating.set(false);
	}
}

/** Get current deployment mode. GET /api/config/skills/deployment-mode */
export async function getDeploymentMode(): Promise<any> {
	const result = await fetchJSON(`${API_BASE}/skills/deployment-mode`);
	return result;
}

/** Switch deployment mode. PUT /api/config/skills/deployment-mode */
export async function switchDeploymentMode(
	mode: string,
	options: { preview?: boolean; confirm?: boolean; skills?: string[] } = {}
): Promise<any> {
	const body: Record<string, any> = { mode, ...options };
	const result = await mutateJSON(`${API_BASE}/skills/deployment-mode`, 'PUT', body);
	if (!options.preview) {
		await Promise.all([fetchDeployedSkills(), fetchAvailableSkills(), fetchProjectSummary()]);
	}
	return result;
}

/** Detect project toolchain. POST /api/config/auto-configure/detect */
export async function detectToolchain(project_path?: string): Promise<ToolchainResult> {
	const body: Record<string, any> = {};
	if (project_path) body.project_path = project_path;
	const result = await mutateJSON(`${API_BASE}/auto-configure/detect`, 'POST', body);
	return result.data || result;
}

/** Preview auto-configuration. POST /api/config/auto-configure/preview */
export async function previewAutoConfig(project_path?: string, min_confidence?: number): Promise<AutoConfigPreview> {
	const body: Record<string, any> = {};
	if (project_path) body.project_path = project_path;
	if (min_confidence !== undefined) body.min_confidence = min_confidence;
	const result = await mutateJSON(`${API_BASE}/auto-configure/preview`, 'POST', body);
	return result.data || result;
}

/** Apply auto-configuration. POST /api/config/auto-configure/apply */
export async function applyAutoConfig(options: Record<string, any> = {}): Promise<any> {
	mutating.set(true);
	try {
		const result = await mutateJSON(`${API_BASE}/auto-configure/apply`, 'POST', options);
		await Promise.all([fetchDeployedAgents(), fetchAvailableAgents(), fetchDeployedSkills(), fetchAvailableSkills(), fetchProjectSummary()]);
		toastStore.success(result.message || 'Auto-configuration applied');
		return result;
	} catch (e: any) {
		toastStore.error(e.message || 'Auto-configuration failed');
		throw e;
	} finally {
		mutating.set(false);
	}
}

/** Check for active Claude Code sessions. GET /api/config/active-sessions */
export async function checkActiveSessions(): Promise<ActiveSessionInfo> {
	try {
		const result = await fetchJSON(`${API_BASE}/active-sessions`);
		return result.data || result;
	} catch {
		return { active: false, sessions: [] };
	}
}

// --- Phase 2 & 3: Socket.IO Config Event Handler ---

/**
 * Handle a config_event from Socket.IO.
 * Called from +page.svelte or +layout.svelte when socket receives 'config_event'.
 */
export function handleConfigEvent(event: ConfigEvent): void {
	switch (event.operation) {
		case 'source_added':
		case 'source_removed':
		case 'source_updated':
			fetchSources();
			break;

		case 'sync_progress':
		case 'sync_completed':
		case 'sync_failed':
			updateSyncStatusFromEvent(event);
			break;

		case 'agent_deployed':
		case 'agent_undeployed':
			fetchDeployedAgents();
			fetchAvailableAgents();
			fetchProjectSummary();
			break;

		case 'skill_deployed':
		case 'skill_undeployed':
			fetchDeployedSkills();
			fetchAvailableSkills();
			fetchProjectSummary();
			break;

		case 'autoconfig_progress':
		case 'autoconfig_completed':
		case 'autoconfig_failed':
			// These are handled by component-level listeners
			break;

		case 'external_change':
			toastStore.warning('Configuration changed externally. Refreshing...');
			fetchSources();
			break;
	}
}

function updateSyncStatusFromEvent(event: ConfigEvent): void {
	const id = event.entity_id;
	if (!id) return;

	syncStatus.update((s) => {
		const current = s[id];

		if (event.operation === 'sync_completed') {
			return {
				...s,
				[id]: {
					status: 'completed',
					progress: 100,
					lastSync: event.timestamp,
					error: null,
					jobId: event.data?.job_id ?? null,
				},
			};
		} else if (event.operation === 'sync_failed') {
			return {
				...s,
				[id]: {
					status: 'failed',
					progress: 0,
					lastSync: current?.lastSync ?? null,
					error: event.data?.error ?? 'Sync failed',
					jobId: event.data?.job_id ?? null,
				},
			};
		} else if (event.operation === 'sync_progress') {
			return {
				...s,
				[id]: {
					status: 'syncing',
					progress: event.data?.progress_pct ?? event.data?.progress ?? 0,
					lastSync: current?.lastSync ?? null,
					error: null,
					jobId: event.data?.job_id ?? null,
				},
			};
		}

		return s;
	});

	// Refetch sources after sync completes (may have new items)
	if (event.operation === 'sync_completed') {
		fetchSources();
	}
}
