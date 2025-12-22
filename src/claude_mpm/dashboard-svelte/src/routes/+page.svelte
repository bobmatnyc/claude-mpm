<script lang="ts">
	import Header from '$lib/components/Header.svelte';
	import EventStream from '$lib/components/EventStream.svelte';
	import ToolsView from '$lib/components/ToolsView.svelte';
	import FilesView from '$lib/components/FilesView.svelte';
	import FileViewer from '$lib/components/FileViewer.svelte';
	import JSONExplorer from '$lib/components/JSONExplorer.svelte';
	import type { ClaudeEvent, Tool } from '$lib/types/events';
	import type { FileEntry } from '$lib/stores/files.svelte';
	import { socketStore } from '$lib/stores/socket.svelte';
	import { createToolsStore } from '$lib/stores/tools.svelte';
	import { createFilesStore } from '$lib/stores/files.svelte';
	import { get } from 'svelte/store';

	type ViewMode = 'events' | 'tools' | 'files';

	let selectedEvent = $state<ClaudeEvent | null>(null);
	let selectedTool = $state<Tool | null>(null);
	let selectedFile = $state<FileEntry | null>(null);
	let viewMode = $state<ViewMode>('events');
	let leftWidth = $state(40); // percentage - 40% event stream, 60% data explorer
	let isDragging = $state(false);

	// Use selectedStream from store
	const { selectedStream, events: eventsStore } = socketStore;

	// Create tools and files stores
	const toolsStore = createToolsStore(eventsStore);
	const filesStore = createFilesStore(eventsStore);

	// Subscribe to tools store
	let tools = $state<Tool[]>([]);

	$effect(() => {
		const unsubscribe = toolsStore.subscribe(value => {
			tools = value;
		});
		return unsubscribe;
	});

	// Subscribe to files store
	let files = $state<FileEntry[]>([]);

	$effect(() => {
		const unsubscribe = filesStore.subscribe(value => {
			files = value;
		});
		return unsubscribe;
	});

	// Log selectedFile changes
	$effect(() => {
		console.log('[+page] selectedFile changed:', {
			hasFile: !!selectedFile,
			filename: selectedFile?.filename,
			operations: selectedFile?.operations.length,
			viewMode
		});
	});

	// Clear selections when switching views
	$effect(() => {
		if (viewMode === 'events') {
			selectedTool = null;
			selectedFile = null;
		} else if (viewMode === 'tools') {
			selectedEvent = null;
			selectedFile = null;
		} else if (viewMode === 'files') {
			selectedEvent = null;
			selectedTool = null;
		}
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
				</div>
			</div>

			<!-- Conditional View Rendering -->
			<div class="flex-1 min-h-0">
				{#if viewMode === 'events'}
					<EventStream bind:selectedEvent selectedStream={$selectedStream} />
				{:else if viewMode === 'tools'}
					<ToolsView {tools} bind:selectedTool selectedStream={$selectedStream} />
				{:else if viewMode === 'files'}
					<FilesView {files} bind:selectedFile selectedStream={$selectedStream} />
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

		<!-- Right Panel: JSON Explorer or FileViewer (resizable) -->
		<div class="right-panel flex-1 min-w-0" style="width: {100 - leftWidth}%;">
			{#if viewMode === 'files'}
				<FileViewer file={selectedFile} />
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
