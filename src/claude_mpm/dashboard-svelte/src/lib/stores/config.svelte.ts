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

// --- Phase 2: Socket.IO Config Event Handler ---

/**
 * Handle a config_event from Socket.IO.
 * Called from +page.svelte or +layout.svelte when socket receives 'config_event'.
 */
export function handleConfigEvent(event: ConfigEvent): void {
	switch (event.operation) {
		case 'source_added':
		case 'source_removed':
		case 'source_updated':
			// Refetch sources to ensure consistency
			fetchSources();
			break;

		case 'sync_progress':
		case 'sync_completed':
		case 'sync_failed':
			updateSyncStatusFromEvent(event);
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
