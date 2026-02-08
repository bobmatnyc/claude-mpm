<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import EventStream from '$lib/components/EventStream.svelte';
	import ToolsView from '$lib/components/ToolsView.svelte';
	import FilesView from '$lib/components/FilesView.svelte';
	import AgentsView from '$lib/components/AgentsView.svelte';
	import TokensView from '$lib/components/TokensView.svelte';
	import AgentDetail from '$lib/components/AgentDetail.svelte';
	import JSONExplorer from '$lib/components/JSONExplorer.svelte';
	import FileViewer from '$lib/components/FileViewer.svelte';
	import type { ClaudeEvent, Tool } from '$lib/types/events';
	import type { TouchedFile } from '$lib/stores/files.svelte';
	import type { AgentNode } from '$lib/stores/agents.svelte';
	import type { ToolCall } from '$lib/stores/agents.svelte';
	import { socketStore } from '$lib/stores/socket.svelte';
	import { createToolsStore } from '$lib/stores/tools.svelte';
	import { createAgentsStore } from '$lib/stores/agents.svelte';
	import { derived } from 'svelte/store';

	type ViewMode = 'events' | 'tools' | 'files' | 'agents' | 'tokens';

	let selectedEvent = $state<ClaudeEvent | null>(null);
	let selectedTool = $state<Tool | null>(null);
	let selectedFile = $state<TouchedFile | null>(null);
	let selectedAgent = $state<AgentNode | null>(null);
	let fileContent = $state<string>('');
	let contentLoading = $state(false);
	let viewMode = $state<ViewMode>('events');
	let leftWidth = $state(40); // percentage - 40% event stream, 60% data explorer
	let isDragging = $state(false);

	// Use selectedStream from store
	const { selectedStream, events: eventsStore, currentWorkingDirectory, projectFilter } = socketStore;

	// Create filtered events store based on selectedStream
	// This ensures tools store reacts to stream changes
	const filteredEventsStore = derived(
		[eventsStore, selectedStream, currentWorkingDirectory, projectFilter],
		([$events, $selectedStream, $currentWd, $projectFilter]) => {
			// If 'all-streams', show all events matching the current project filter
			if ($selectedStream === 'all-streams') {
				// If project filter is 'current' and we have a working directory, filter by cwd
				if ($projectFilter === 'current' && $currentWd) {
					return $events.filter(event => {
						// Extract cwd from event
						const eventCwd =
							event.cwd ||
							event.working_directory ||
							(event.data as any)?.working_directory ||
							(event.data as any)?.cwd ||
							(event.metadata as any)?.working_directory ||
							(event.metadata as any)?.cwd;
						return eventCwd === $currentWd;
					});
				}
				// Otherwise return all events
				return $events;
			}
			// If empty (no stream selected yet), return all events
			if ($selectedStream === '') {
				return $events;
			}
			// Otherwise filter by selected stream
			return $events.filter(event => {
				const streamId = (
					event.session_id ||
					event.sessionId ||
					(event.data as any)?.session_id ||
					(event.data as any)?.sessionId ||
					event.source ||
					null
				);
				return streamId === $selectedStream;
			});
		}
	);

	// Create tools store from filtered events
	const toolsStore = createToolsStore(filteredEventsStore);

	// Create agents store from filtered events
	const agentsStore = createAgentsStore(filteredEventsStore);

	// Subscribe to tools store - use object wrapper to ensure Svelte 5 reactivity
	let toolsWrapper = $state<{ value: Tool[] }>({ value: [] });

	$effect(() => {
		const unsubscribe = toolsStore.subscribe(value => {
			console.log('[+page] Tools store updated:', value.length);
			toolsWrapper = { value };  // Create new object reference to trigger reactivity
		});
		return unsubscribe;
	});

	// Derive tools from wrapper for use in template
	let tools = $derived(toolsWrapper.value);

	// Subscribe to agents store
	let rootAgent = $state<AgentNode | null>(null);

	$effect(() => {
		const unsubscribe = agentsStore.subscribe((value: unknown) => {
			rootAgent = value as AgentNode;
		});
		return unsubscribe;
	});

	// Clear selections when switching views
	$effect(() => {
		if (viewMode === 'events') {
			selectedTool = null;
			selectedFile = null;
			selectedAgent = null;
		} else if (viewMode === 'tools') {
			selectedEvent = null;
			selectedFile = null;
			selectedAgent = null;
		} else if (viewMode === 'files') {
			selectedEvent = null;
			selectedTool = null;
			selectedAgent = null;
		} else if (viewMode === 'agents' || viewMode === 'tokens') {
			selectedEvent = null;
			selectedTool = null;
			selectedFile = null;
		}
	});

	// Clear selections when stream changes to avoid showing data from wrong stream
	$effect(() => {
		// Subscribe to selectedStream changes
		$selectedStream;
		// Clear all selections when stream changes
		selectedEvent = null;
		selectedTool = null;
		selectedFile = null;
		selectedAgent = null;
		fileContent = '';
	});

	function startDrag(e: MouseEvent) {
		isDragging = true;
		e.preventDefault();
	}

	function onDrag(e: MouseEvent) {
		if (!isDragging) return;
		const container = document.querySelector('.split-container');
		if (!container) return;
		const rect = container.getBoundingClientRect();
		const newWidthPercent = ((e.clientX - rect.left) / rect.width) * 100;

		// Calculate minimum widths as percentages
		const minLeftPercent = (300 / rect.width) * 100;
		const minRightPercent = (200 / rect.width) * 100;
		const maxLeftPercent = 100 - minRightPercent;

		// Clamp between minimum widths
		leftWidth = Math.max(minLeftPercent, Math.min(maxLeftPercent, newWidthPercent));
	}

	function stopDrag() {
		isDragging = false;
	}

	function handleToolClickFromAgent(toolCall: ToolCall) {
		console.log('[AgentToolClick] Clicked tool:', toolCall);
		console.log('[AgentToolClick] Available tools count:', tools.length);
		console.log('[AgentToolClick] Looking for correlation ID:', toolCall.id);

		// Find the corresponding Tool from the tools store by correlation ID
		const tool = tools.find(t => t.id === toolCall.id);
		if (tool) {
			console.log('[AgentToolClick] Found matching tool:', tool);
			// Switch to tools view and select the tool
			viewMode = 'tools';
			selectedTool = tool;
		} else {
			console.warn('[AgentToolClick] Tool not found for correlation ID:', toolCall.id);
			console.warn('[AgentToolClick] Available tool IDs:', tools.map(t => t.id));
		}
	}
</script>

<svelte:head>
	<title>Claude MPM Monitor</title>
</svelte:head>

<svelte:window on:mousemove={onDrag} on:mouseup={stopDrag} />

<div class="flex flex-col h-screen bg-slate-50 dark:bg-slate-900 transition-colors">
	<Header />

	<div class="split-container flex flex-1 min-h-0">
		<!-- Left Panel: View Selector + EventStream or ToolsView or FilesView (resizable) -->
		<div class="left-panel flex flex-col flex-shrink-0 min-w-0" style="width: {leftWidth}%;">
			<!-- View Tabs -->
			<div class="bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
				<div class="flex gap-0 px-2 pt-2">
					<button
						onclick={() => viewMode = 'events'}
						class="tab"
						class:active={viewMode === 'events'}
					>
						Events
					</button>
					<button
						onclick={() => viewMode = 'tools'}
						class="tab"
						class:active={viewMode === 'tools'}
					>
						Tools
					</button>
					<button
						onclick={() => viewMode = 'files'}
						class="tab"
						class:active={viewMode === 'files'}
					>
						Files
					</button>
					<button
						onclick={() => viewMode = 'agents'}
						class="tab"
						class:active={viewMode === 'agents'}
					>
						Agents
					</button>
					<button
						onclick={() => viewMode = 'tokens'}
						class="tab"
						class:active={viewMode === 'tokens'}
					>
						Tokens
					</button>
				</div>
			</div>

			<!-- Conditional View Rendering -->
			<div class="flex-1 min-h-0">
				{#if viewMode === 'events'}
					<EventStream bind:selectedEvent selectedStream={$selectedStream} />
				{:else if viewMode === 'tools'}
					<ToolsView {tools} bind:selectedTool selectedStream={$selectedStream} />
				{:else if viewMode === 'agents'}
					{#if rootAgent}
						<AgentsView {rootAgent} bind:selectedAgent selectedStream={$selectedStream} />
					{:else}
						<div class="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
							<p>Loading agent data...</p>
						</div>
					{/if}
				{:else if viewMode === 'tokens'}
					{#if rootAgent}
						<TokensView {rootAgent} bind:selectedAgent selectedStream={$selectedStream} />
					{:else}
						<div class="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
							<p>Loading agent data...</p>
						</div>
					{/if}
				{:else if viewMode === 'files'}
					<FilesView
						selectedStream={$selectedStream}
						bind:selectedFile
						bind:fileContent
						bind:contentLoading
					/>
				{/if}
			</div>
		</div>

		<!-- Draggable Divider -->
		<div
			class="divider"
			class:dragging={isDragging}
			onmousedown={startDrag}
			role="separator"
			aria-label="Resize panels"
			tabindex="0"
		></div>

		<!-- Right Panel: JSON Explorer, File Viewer, or Agent Detail -->
		<div class="right-panel flex flex-col flex-1 min-w-0 min-h-0" style="width: {100 - leftWidth}%;">
			{#if viewMode === 'files'}
				{#if selectedFile}
					<FileViewer
						file={{
							name: selectedFile.name,
							path: selectedFile.path,
							type: 'file' as const,
							size: fileContent.length,
							modified: typeof selectedFile.timestamp === 'string'
								? new Date(selectedFile.timestamp).getTime() / 1000
								: selectedFile.timestamp / 1000
						}}
						content={fileContent}
						isLoading={contentLoading}
					/>
				{:else}
					<div class="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
						<div class="text-center">
							<svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
							</svg>
							<p class="text-lg">Select a file to view its content</p>
						</div>
					</div>
				{/if}
			{:else if viewMode === 'agents'}
				<AgentDetail agent={selectedAgent} onToolClick={handleToolClickFromAgent} />
			{:else}
				<JSONExplorer event={selectedEvent} tool={selectedTool} />
			{/if}
		</div>
	</div>
</div>

<style>
	.tab {
		padding: 0.5rem 1.5rem;
		font-size: 0.875rem;
		font-weight: 600;
		background-color: #475569; /* slate-600 for light mode */
		color: #94a3b8; /* slate-400 */
		border-top-left-radius: 0.375rem;
		border-top-right-radius: 0.375rem;
		transition: all 0.2s;
		cursor: pointer;
		border: none;
		outline: none;
	}

	:global(.dark) .tab {
		background-color: #475569; /* slate-600 for dark mode */
	}

	.tab:hover:not(.active) {
		background-color: #64748b; /* slate-500 */
		color: #cbd5e1; /* slate-300 */
	}

	.tab.active {
		background-color: #0891b2; /* cyan-600 */
		color: #ffffff;
	}

	.divider {
		width: 6px;
		background: #cbd5e1; /* slate-300 for light */
		cursor: col-resize;
		transition: background 0.2s;
		flex-shrink: 0;
	}

	:global(.dark) .divider {
		background: #334155; /* slate-700 for dark */
	}

	.divider:hover {
		background: #0891b2; /* cyan-600 */
	}

	.divider.dragging {
		background: #0891b2; /* cyan-600 */
	}

	/* Prevent text selection during drag */
	:global(body.dragging) {
		user-select: none;
		cursor: col-resize !important;
	}
</style>
