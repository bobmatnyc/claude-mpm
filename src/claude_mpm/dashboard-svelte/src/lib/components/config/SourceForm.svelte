<script lang="ts">
	import type { ConfigSource } from '$lib/stores/config.svelte';

	interface Props {
		mode: 'add' | 'edit';
		sourceType: 'agent' | 'skill';
		initialData?: Partial<ConfigSource> | null;
		onsubmit: (data: Record<string, any>) => Promise<void>;
		oncancel: () => void;
	}

	let { mode, sourceType, initialData = null, onsubmit, oncancel }: Props = $props();

	// --- Form state ---
	let url = $state(initialData?.url ?? '');
	let subdirectory = $state(initialData?.subdirectory ?? '');
	let branch = $state(initialData?.branch ?? 'main');
	let priority = $state(initialData?.priority ?? (sourceType === 'agent' ? 500 : 100));
	let enabled = $state(initialData?.enabled ?? true);
	let sourceId = $state(initialData?.id ?? '');
	let token = $state('');

	// --- Touched state (validate on blur) ---
	let touched = $state<Record<string, boolean>>({
		url: false,
		subdirectory: false,
		branch: false,
		priority: false,
		sourceId: false,
		token: false,
	});

	let submitting = $state(false);

	// --- Validation regexes ---
	const GITHUB_URL_REGEX = /^https:\/\/github\.com\/.+\/.+$/;
	const SKILL_ID_REGEX = /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/;

	// --- Validation errors ---
	let urlError = $derived.by(() => {
		if (!touched.url) return null;
		if (!url.trim()) return 'URL is required';
		if (!GITHUB_URL_REGEX.test(url.trim())) return 'Must be a valid GitHub URL (https://github.com/owner/repo)';
		return null;
	});

	let subdirectoryError = $derived.by(() => {
		if (!touched.subdirectory || !subdirectory.trim()) return null;
		if (subdirectory.startsWith('/')) return 'Must be a relative path (no leading /)';
		if (subdirectory.includes('..')) return 'Path traversal (..) is not allowed';
		return null;
	});

	let branchError = $derived.by(() => {
		if (!touched.branch) return null;
		if (sourceType === 'skill' && !branch.trim()) return 'Branch is required';
		return null;
	});

	let priorityError = $derived.by(() => {
		if (!touched.priority) return null;
		const p = Number(priority);
		if (isNaN(p) || p < 0 || p > 1000) return 'Priority must be between 0 and 1000';
		return null;
	});

	let sourceIdError = $derived.by(() => {
		if (sourceType !== 'skill') return null;
		if (!touched.sourceId) return null;
		if (mode === 'add' && !sourceId.trim()) return 'Source ID is required';
		if (sourceId.trim() && !SKILL_ID_REGEX.test(sourceId.trim())) {
			return 'Must start with alphanumeric, only letters, numbers, hyphens, underscores';
		}
		return null;
	});

	// --- Form validity ---
	let isValid = $derived.by(() => {
		// URL required and valid for both types
		if (!url.trim() || !GITHUB_URL_REGEX.test(url.trim())) return false;
		// Subdirectory optional but must be valid if provided
		if (subdirectory.trim() && (subdirectory.startsWith('/') || subdirectory.includes('..'))) return false;
		// Priority range
		const p = Number(priority);
		if (isNaN(p) || p < 0 || p > 1000) return false;
		// Skill-specific validations
		if (sourceType === 'skill') {
			if (mode === 'add' && !sourceId.trim()) return false;
			if (sourceId.trim() && !SKILL_ID_REGEX.test(sourceId.trim())) return false;
			if (!branch.trim()) return false;
		}
		return true;
	});

	// --- Submit handler ---
	async function handleSubmit() {
		if (!isValid || submitting) return;
		submitting = true;

		const data: Record<string, any> = {
			url: url.trim(),
			priority: Number(priority),
			enabled,
		};

		if (sourceType === 'agent') {
			if (subdirectory.trim()) data.subdirectory = subdirectory.trim();
		} else {
			if (mode === 'add') data.id = sourceId.trim();
			data.branch = branch.trim();
			if (token.trim()) data.token = token.trim();
		}

		try {
			await onsubmit(data);
		} catch {
			// Error handling done by caller via toastStore
		} finally {
			submitting = false;
		}
	}

	function markTouched(field: string) {
		touched = { ...touched, [field]: true };
	}
</script>

<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-4">
	{#if sourceType === 'skill'}
		<!-- Source ID (skill only) -->
		<div>
			<label for="source-id" class="block text-sm font-medium text-slate-300 mb-1">Source ID</label>
			<input
				id="source-id"
				type="text"
				bind:value={sourceId}
				onblur={() => markTouched('sourceId')}
				disabled={mode === 'edit'}
				placeholder="my-custom-skills"
				class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-100
					placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500
					disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
			/>
			{#if sourceIdError}
				<p class="text-red-400 text-xs mt-1">{sourceIdError}</p>
			{/if}
		</div>
	{/if}

	<!-- Repository URL -->
	<div>
		<label for="source-url" class="block text-sm font-medium text-slate-300 mb-1">Repository URL</label>
		<input
			id="source-url"
			type="text"
			bind:value={url}
			onblur={() => markTouched('url')}
			placeholder="https://github.com/owner/repo"
			class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-100
				placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500
				transition-colors"
		/>
		{#if urlError}
			<p class="text-red-400 text-xs mt-1">{urlError}</p>
		{/if}
	</div>

	{#if sourceType === 'agent'}
		<!-- Subdirectory (agent only) -->
		<div>
			<label for="source-subdir" class="block text-sm font-medium text-slate-300 mb-1">Subdirectory <span class="text-slate-500 font-normal">(optional)</span></label>
			<input
				id="source-subdir"
				type="text"
				bind:value={subdirectory}
				onblur={() => markTouched('subdirectory')}
				placeholder="agents"
				class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-100
					placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500
					transition-colors"
			/>
			{#if subdirectoryError}
				<p class="text-red-400 text-xs mt-1">{subdirectoryError}</p>
			{/if}
		</div>
	{/if}

	{#if sourceType === 'skill'}
		<!-- Branch (skill only) -->
		<div>
			<label for="source-branch" class="block text-sm font-medium text-slate-300 mb-1">Branch</label>
			<input
				id="source-branch"
				type="text"
				bind:value={branch}
				onblur={() => markTouched('branch')}
				placeholder="main"
				class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-100
					placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500
					transition-colors"
			/>
			{#if branchError}
				<p class="text-red-400 text-xs mt-1">{branchError}</p>
			{/if}
		</div>
	{/if}

	<!-- Priority -->
	<div>
		<label for="source-priority" class="block text-sm font-medium text-slate-300 mb-1">Priority <span class="text-slate-500 font-normal">(0-1000, lower = higher priority)</span></label>
		<input
			id="source-priority"
			type="number"
			bind:value={priority}
			onblur={() => markTouched('priority')}
			min="0"
			max="1000"
			placeholder={sourceType === 'agent' ? '500' : '100'}
			class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-100
				placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500
				transition-colors"
		/>
		{#if priorityError}
			<p class="text-red-400 text-xs mt-1">{priorityError}</p>
		{/if}
	</div>

	{#if sourceType === 'skill'}
		<!-- Token (skill only, write-only) -->
		<div>
			<label for="source-token" class="block text-sm font-medium text-slate-300 mb-1">GitHub Token <span class="text-slate-500 font-normal">(optional)</span></label>
			<input
				id="source-token"
				type="password"
				bind:value={token}
				placeholder="$GITHUB_TOKEN or token value"
				class="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-sm text-slate-100
					placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500
					transition-colors"
			/>
			<p class="text-slate-500 text-xs mt-1">Prefix with $ to reference an environment variable. Never displayed after save.</p>
		</div>
	{/if}

	<!-- Enabled toggle -->
	<div class="flex items-center gap-3">
		<label class="relative inline-flex items-center cursor-pointer">
			<input type="checkbox" bind:checked={enabled} class="sr-only peer" />
			<div class="w-9 h-5 bg-slate-600 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-cyan-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-600"></div>
		</label>
		<span class="text-sm text-slate-300">Enabled</span>
	</div>

	<!-- Action buttons -->
	<div class="flex justify-end gap-3 pt-2">
		<button
			type="button"
			onclick={oncancel}
			class="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
		>
			Cancel
		</button>
		<button
			type="submit"
			disabled={!isValid || submitting}
			class="px-4 py-2 text-sm font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg
				disabled:opacity-50 disabled:cursor-not-allowed transition-colors
				flex items-center gap-2"
		>
			{#if submitting}
				<svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
			{/if}
			{mode === 'add' ? 'Add Source' : 'Save Changes'}
		</button>
	</div>
</form>
