<script lang="ts">
  import { onMount } from 'svelte';
  import * as d3 from 'd3';
  import type { TouchedFile } from '$lib/stores/files.svelte';
  import {
    buildFileTree,
    convertToD3Hierarchy,
    getOperationColor,
    getLighterColor,
    type FileNode
  } from '$lib/utils/file-tree-builder';
  import { generateDiff, type DiffLine } from '$lib/stores/files.svelte';

  interface Props {
    files?: TouchedFile[];
    selectedFile?: TouchedFile | null;
    onFileSelect?: (file: TouchedFile) => void;
  }

  let {
    files = [],
    selectedFile = null,
    onFileSelect
  }: Props = $props();

  let svgElement: SVGSVGElement;
  let containerElement: HTMLDivElement;
  let width = $state(800);
  let height = $state(600);

  // Zoom state
  let zoomTransform = $state<d3.ZoomTransform | null>(null);
  let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;

  // Track recently added files for radar animation
  let recentlyAddedFiles = $state<Set<string>>(new Set());
  let highlightTimeouts = new Map<string, number>();

  // Track which files we've already processed to avoid duplicates
  let processedEventIds = new Set<string>();

  // Update tree when files change
  $effect(() => {
    if (svgElement && files.length > 0) {
      // Check for newly added files (radar feature)
      const currentPaths = new Set(files.map(f => f.path));
      const newFiles = files.filter(f => !processedEventIds.has(f.eventId));

      // Add new files to radar tracking
      newFiles.forEach(file => {
        processedEventIds.add(file.eventId);

        // Add to recently added set for highlight
        recentlyAddedFiles.add(file.path);

        // Clear existing timeout if any
        const existingTimeout = highlightTimeouts.get(file.path);
        if (existingTimeout) {
          clearTimeout(existingTimeout);
        }

        // Remove highlight after 3 seconds
        const timeout = setTimeout(() => {
          recentlyAddedFiles.delete(file.path);
          recentlyAddedFiles = recentlyAddedFiles; // Trigger reactivity
          highlightTimeouts.delete(file.path);
        }, 3000);

        highlightTimeouts.set(file.path, timeout);
      });

      renderTree();
    }
  });

  // Handle window resize
  onMount(() => {
    updateDimensions();
    window.addEventListener('resize', updateDimensions);

    return () => {
      window.removeEventListener('resize', updateDimensions);
      // Clean up timeouts
      highlightTimeouts.forEach(timeout => clearTimeout(timeout));
      highlightTimeouts.clear();
    };
  });

  function updateDimensions() {
    if (containerElement) {
      const rect = containerElement.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      if (files.length > 0) {
        renderTree();
      }
    }
  }

  function renderTree() {
    if (!svgElement || files.length === 0) return;

    // Build tree data
    const fileTree = buildFileTree(files);
    const root = convertToD3Hierarchy(fileTree);

    // Calculate dimensions - root at center, tree radiates outward
    const radius = Math.min(width, height) / 2 - 120;

    // Create radial tree layout
    const treeLayout = d3.tree<FileNode>()
      .size([2 * Math.PI, radius])
      .separation((a, b) => (a.parent === b.parent ? 1 : 2) / a.depth);

    // Generate tree structure
    const treeData = treeLayout(root);

    // Clear previous render
    const svg = d3.select(svgElement);
    svg.selectAll('*').remove();

    // Setup zoom behavior
    if (!zoomBehavior) {
      zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.5, 3])
        .on('zoom', (event) => {
          zoomTransform = event.transform;
          g.attr('transform', `translate(${width / 2},${height / 2}) ${event.transform}`);
        });

      svg.call(zoomBehavior);
    }

    // Create main group centered in SVG
    const g = svg
      .append('g')
      .attr('transform', `translate(${width / 2},${height / 2})`);

    // Radial link generator
    const linkGenerator = d3.linkRadial<any, any>()
      .angle((d: any) => d.x)
      .radius((d: any) => d.y);

    // Draw links
    g.append('g')
      .attr('class', 'links')
      .attr('fill', 'none')
      .attr('stroke', '#64748b')
      .attr('stroke-opacity', 0.8)
      .attr('stroke-width', 2)
      .selectAll('path')
      .data(treeData.links())
      .join('path')
      .attr('d', linkGenerator);

    // FEATURE A: Collision Detection Data Structure
    interface LabelBounds {
      node: d3.HierarchyPointNode<FileNode>;
      x: number;
      y: number;
      width: number;
      height: number;
      isRightSide: boolean;
    }

    const labelBounds: LabelBounds[] = [];

    // Calculate label positions and detect collisions
    treeData.descendants().forEach(d => {
      const angle = d.x - Math.PI / 2;
      const nodeX = d.y * Math.cos(angle);
      const nodeY = d.y * Math.sin(angle);
      const isRightSide = d.x < Math.PI;

      // Estimate text width (rough approximation)
      const text = d.depth === 0 ? '📁 root' : d.data.name;
      const fontSize = d.depth === 0 ? 12 : (d.data.isFile ? 10 : 9);
      const charWidth = fontSize * 0.6;
      const textWidth = text.length * charWidth;
      const textHeight = fontSize * 1.5;

      const labelOffset = isRightSide ? 10 : -10 - textWidth;

      labelBounds.push({
        node: d,
        x: nodeX + labelOffset,
        y: nodeY - textHeight / 2,
        width: textWidth,
        height: textHeight,
        isRightSide
      });
    });

    // Simple collision resolution: adjust y position if overlapping
    for (let i = 0; i < labelBounds.length; i++) {
      for (let j = i + 1; j < labelBounds.length; j++) {
        const a = labelBounds[i];
        const b = labelBounds[j];

        // Check if same side and overlapping
        if (a.isRightSide === b.isRightSide) {
          const xOverlap = Math.abs(a.x - b.x) < Math.max(a.width, b.width);
          const yOverlap = Math.abs(a.y - b.y) < (a.height + b.height) / 2;

          if (xOverlap && yOverlap) {
            // Push the second label down slightly
            b.y += a.height * 0.7;
          }
        }
      }
    }

    // Draw nodes
    const nodes = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(treeData.descendants())
      .join('g')
      .attr('transform', d => {
        const angle = d.x - Math.PI / 2;
        const x = d.y * Math.cos(angle);
        const y = d.y * Math.sin(angle);
        return `translate(${x},${y})`;
      });

    // Node circles with radar animation
    nodes
      .append('circle')
      .attr('r', d => {
        if (d.depth === 0) return 8;
        return d.data.isFile ? 5 : 4;
      })
      .attr('fill', d => {
        if (d.depth === 0) return '#8b5cf6';
        const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
        const isRecent = d.data.file && recentlyAddedFiles.has(d.data.file.path);

        if (isSelected) return '#06b6d4';
        if (isRecent) return '#f59e0b'; // Amber for recently added
        return d.data.isFile ? getLighterColor(d.data.operation) : '#475569';
      })
      .attr('stroke', d => {
        if (d.depth === 0) return '#a78bfa';
        const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
        const isRecent = d.data.file && recentlyAddedFiles.has(d.data.file.path);

        if (isSelected) return '#06b6d4';
        if (isRecent) return '#f59e0b';
        return getOperationColor(d.data.operation);
      })
      .attr('stroke-width', d => {
        const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
        const isRecent = d.data.file && recentlyAddedFiles.has(d.data.file.path);
        return isSelected || isRecent ? 3 : 2;
      })
      .attr('cursor', d => (d.data.isFile ? 'pointer' : 'default'))
      .attr('class', d => {
        const isRecent = d.data.file && recentlyAddedFiles.has(d.data.file.path);
        return isRecent ? 'radar-pulse' : '';
      })
      .on('click', (event, d) => {
        if (d.data.isFile && d.data.file && onFileSelect) {
          onFileSelect(d.data.file);
        }
      })
      .on('mouseenter', function (event, d) {
        if (d.data.isFile && d.data.file) {
          d3.select(this).attr('r', 7).attr('stroke-width', 3);
          showDiffCard(event, d.data.file);
        }
      })
      .on('mouseleave', function (event, d) {
        if (d.data.isFile) {
          const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
          const isRecent = d.data.file && recentlyAddedFiles.has(d.data.file.path);
          d3.select(this).attr('r', 5).attr('stroke-width', isSelected || isRecent ? 3 : 2);
          hideDiffCard();
        }
      });

    // Labels with collision-adjusted positions
    const labelsGroup = g.append('g').attr('class', 'labels');

    labelBounds.forEach((bounds, i) => {
      const d = bounds.node;
      const text = d.depth === 0 ? '📁 root' : d.data.name;
      const fontSize = d.depth === 0 ? 12 : (d.data.isFile ? 10 : 9);

      labelsGroup
        .append('text')
        .attr('x', bounds.x + (bounds.isRightSide ? 0 : bounds.width))
        .attr('y', bounds.y + bounds.height / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', bounds.isRightSide ? 'start' : 'end')
        .text(text)
        .attr('fill', () => {
          if (d.depth === 0) return '#a78bfa';
          const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
          const isRecent = d.data.file && recentlyAddedFiles.has(d.data.file.path);
          if (isSelected) return '#06b6d4';
          if (isRecent) return '#f59e0b';
          return '#e2e8f0';
        })
        .attr('font-size', `${fontSize}px`)
        .attr('font-family', 'ui-monospace, monospace')
        .attr('font-weight', d.depth === 0 ? '600' : '400')
        .attr('cursor', d.data.isFile ? 'pointer' : 'default')
        .style('dominant-baseline', 'middle')
        .on('click', () => {
          if (d.data.isFile && d.data.file && onFileSelect) {
            onFileSelect(d.data.file);
          }
        })
        .on('mouseenter', function (event) {
          if (d.data.isFile && d.data.file) {
            d3.select(this).attr('fill', '#06b6d4').style('text-decoration', 'underline');
            showDiffCard(event, d.data.file);
          }
        })
        .on('mouseleave', function () {
          if (d.data.isFile) {
            const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
            const isRecent = d.data.file && recentlyAddedFiles.has(d.data.file.path);
            d3.select(this)
              .attr('fill', isSelected ? '#06b6d4' : (isRecent ? '#f59e0b' : '#e2e8f0'))
              .style('text-decoration', 'none');
            hideDiffCard();
          }
        });
    });
  }

  // FEATURE C: Diff Hover Card
  let diffCardVisible = $state(false);
  let diffCardData = $state<{
    path: string;
    additions: number;
    deletions: number;
    operation: string;
    hasContent: boolean;
  } | null>(null);
  let diffCardX = $state(0);
  let diffCardY = $state(0);

  function showDiffCard(event: MouseEvent, file: TouchedFile) {
    // Calculate diff statistics
    let additions = 0;
    let deletions = 0;
    let hasContent = false;

    if (file.oldContent && file.newContent) {
      const diff = generateDiff(file.oldContent, file.newContent);
      additions = diff.filter(line => line.type === 'add').length;
      deletions = diff.filter(line => line.type === 'remove').length;
      hasContent = true;
    } else if (file.operation === 'write' && file.newContent) {
      // New file - count all lines as additions
      additions = file.newContent.split('\n').length;
      hasContent = true;
    } else if (file.operation === 'read') {
      // Read operation - no diff
      hasContent = false;
    }

    diffCardData = {
      path: file.path,
      additions,
      deletions,
      operation: file.operation,
      hasContent
    };

    diffCardX = event.clientX + 15;
    diffCardY = event.clientY + 15;
    diffCardVisible = true;
  }

  function hideDiffCard() {
    diffCardVisible = false;
  }

  // Reset zoom function
  function resetZoom() {
    if (zoomBehavior && svgElement) {
      d3.select(svgElement)
        .transition()
        .duration(750)
        .call(zoomBehavior.transform, d3.zoomIdentity);
    }
  }
</script>

<div bind:this={containerElement} class="relative w-full h-full bg-slate-900 min-h-[400px]">
  {#if files.length === 0}
    <div class="absolute inset-0 flex items-center justify-center text-slate-400">
      <div class="text-center">
        <svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p class="text-lg mb-2 font-medium">No files to visualize</p>
        <p class="text-sm text-slate-500">Files that Claude touches will appear in the tree</p>
      </div>
    </div>
  {:else}
    <svg
      bind:this={svgElement}
      {width}
      {height}
      class="w-full h-full"
    ></svg>

    <!-- Zoom Controls -->
    <div class="absolute top-4 right-4 flex flex-col gap-2">
      <button
        onclick={resetZoom}
        class="px-3 py-2 bg-slate-800/90 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-600 text-xs font-medium transition-colors"
        title="Reset Zoom"
      >
        Reset Zoom
      </button>
    </div>

    <!-- Legend -->
    <div class="absolute bottom-4 left-4 bg-slate-800/90 rounded-lg p-3 text-xs text-slate-300 border border-slate-700">
      <div class="font-semibold mb-2">Operations</div>
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-violet-500 border-2 border-violet-400"></div>
          <span>Root</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full" style="background: {getLighterColor('read')}; border: 2px solid {getOperationColor('read')}"></div>
          <span>Read</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full" style="background: {getLighterColor('write')}; border: 2px solid {getOperationColor('write')}"></div>
          <span>Write</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full" style="background: {getLighterColor('edit')}; border: 2px solid {getOperationColor('edit')}"></div>
          <span>Edit</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-amber-500 border-2 border-amber-400 radar-pulse"></div>
          <span>Recent (3s)</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-2 h-2 rounded-full bg-slate-600 border-2 border-slate-500"></div>
          <span>Directory</span>
        </div>
      </div>
    </div>

    <!-- FEATURE C: Diff Hover Card -->
    {#if diffCardVisible && diffCardData}
      <div
        class="fixed z-50 px-4 py-3 bg-slate-800/95 text-slate-100 text-xs rounded-lg shadow-xl border border-slate-600 pointer-events-none backdrop-blur-sm"
        style="left: {diffCardX}px; top: {diffCardY}px; min-width: 250px;"
      >
        <div class="font-mono text-[10px] text-slate-400 mb-2 truncate max-w-xs">
          {diffCardData.path}
        </div>

        <div class="flex items-center gap-3 mb-2">
          <span class="px-2 py-0.5 rounded text-[10px] font-medium uppercase
            {diffCardData.operation === 'read' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : ''}
            {diffCardData.operation === 'write' ? 'bg-green-500/20 text-green-300 border border-green-500/30' : ''}
            {diffCardData.operation === 'edit' ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30' : ''}">
            {diffCardData.operation}
          </span>
        </div>

        {#if diffCardData.hasContent}
          <div class="flex items-center gap-4 text-sm">
            <div class="flex items-center gap-1">
              <span class="text-green-400">+{diffCardData.additions}</span>
              <span class="text-slate-500">additions</span>
            </div>
            {#if diffCardData.deletions > 0}
              <div class="flex items-center gap-1">
                <span class="text-red-400">-{diffCardData.deletions}</span>
                <span class="text-slate-500">deletions</span>
              </div>
            {/if}
          </div>
        {:else}
          <div class="text-slate-400 text-xs italic">
            {diffCardData.operation === 'read' ? 'Read-only operation' : 'No diff available'}
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>

<style>
  /* Smooth transitions */
  :global(.nodes circle) {
    transition: r 0.15s ease, stroke-width 0.15s ease;
  }
  :global(.nodes text) {
    transition: fill 0.15s ease;
  }

  /* Radar pulse animation for recently added files */
  :global(.radar-pulse) {
    animation: pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  @keyframes pulse-ring {
    0% {
      filter: drop-shadow(0 0 0 rgba(245, 158, 11, 0.7));
    }
    50% {
      filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.4));
    }
    100% {
      filter: drop-shadow(0 0 0 rgba(245, 158, 11, 0));
    }
  }
</style>
