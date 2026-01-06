<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as d3 from 'd3';
  import type { TouchedFile } from '$lib/stores/files.svelte';
  import {
    buildFileTree,
    convertToD3Hierarchy,
    getOperationColor,
    getLighterColor,
    type FileNode
  } from '$lib/utils/file-tree-builder';

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
  let height = $state(800);

  // Update tree when files change
  $effect(() => {
    if (svgElement && files.length > 0) {
      renderTree();
    }
  });

  // Handle window resize
  onMount(() => {
    updateDimensions();
    window.addEventListener('resize', updateDimensions);

    return () => {
      window.removeEventListener('resize', updateDimensions);
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

    // Calculate radius based on container size
    const radius = Math.min(width, height) / 2 - 100;

    // Create tree layout
    const treeLayout = d3.tree<FileNode>()
      .size([2 * Math.PI, radius])
      .separation((a, b) => (a.parent === b.parent ? 1 : 2) / a.depth);

    // Generate tree structure
    const treeData = treeLayout(root);

    // Clear previous render
    const svg = d3.select(svgElement);
    svg.selectAll('*').remove();

    // Create main group with transform to center
    const g = svg
      .append('g')
      .attr('transform', `translate(${width / 2},${height / 2})`);

    // Helper: Convert polar to cartesian coordinates
    const radialPoint = (x: number, y: number): [number, number] => {
      return [y * Math.cos(x - Math.PI / 2), y * Math.sin(x - Math.PI / 2)];
    };

    // Create link generator
    const link = d3.linkRadial<any, any>()
      .angle(d => d.x)
      .radius(d => d.y);

    // Draw links (edges between nodes)
    g.append('g')
      .attr('class', 'links')
      .selectAll('path')
      .data(treeData.links())
      .join('path')
      .attr('d', link as any)
      .attr('fill', 'none')
      .attr('stroke', '#475569') // slate-600
      .attr('stroke-opacity', 0.4)
      .attr('stroke-width', 1.5);

    // Draw nodes
    const nodes = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(treeData.descendants())
      .join('g')
      .attr('transform', d => {
        const [x, y] = radialPoint(d.x, d.y);
        return `translate(${x},${y})`;
      });

    // Node circles
    nodes
      .append('circle')
      .attr('r', d => (d.data.isFile ? 6 : 4))
      .attr('fill', d => {
        const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
        if (isSelected) {
          return '#06b6d4'; // cyan-500
        }
        return d.data.isFile ? getLighterColor(d.data.operation) : '#475569';
      })
      .attr('stroke', d => {
        const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
        if (isSelected) {
          return '#06b6d4'; // cyan-500
        }
        return getOperationColor(d.data.operation);
      })
      .attr('stroke-width', d => {
        const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
        return isSelected ? 3 : 2;
      })
      .attr('cursor', d => (d.data.isFile ? 'pointer' : 'default'))
      .on('click', (event, d) => {
        if (d.data.isFile && d.data.file && onFileSelect) {
          onFileSelect(d.data.file);
        }
      })
      .on('mouseenter', function (event, d) {
        if (d.data.isFile) {
          d3.select(this).attr('r', 8).attr('stroke-width', 3);
          showTooltip(event, d.data.path);
        }
      })
      .on('mouseleave', function (event, d) {
        if (d.data.isFile) {
          const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
          d3.select(this)
            .attr('r', 6)
            .attr('stroke-width', isSelected ? 3 : 2);
          hideTooltip();
        }
      });

    // Node labels - MUST be horizontal (not following radial lines)
    // Create labels as separate group to ensure horizontal orientation
    const labels = g
      .append('g')
      .attr('class', 'labels')
      .selectAll('text')
      .data(treeData.descendants())
      .join('text')
      .attr('transform', d => {
        // Position at node location but with NO rotation - ensures horizontal text
        const [x, y] = radialPoint(d.x, d.y);
        return `translate(${x},${y})`;
      })
      .attr('dy', '0.31em')
      .attr('x', d => {
        // Offset from node based on position (left vs right side of tree)
        return d.x < Math.PI ? 10 : -10;
      })
      .attr('text-anchor', d => {
        // Right side of tree: left-aligned, Left side: right-aligned
        return d.x < Math.PI ? 'start' : 'end';
      })
      .text(d => (d.depth === 0 ? '' : d.data.name)) // Don't show root label
      .attr('fill', d => {
        const isSelected = selectedFile && d.data.file?.path === selectedFile.path;
        return isSelected ? '#06b6d4' : '#e2e8f0'; // cyan-500 if selected, slate-200 otherwise
      })
      .attr('font-size', d => (d.data.isFile ? '11px' : '10px'))
      .attr('font-family', 'ui-monospace, monospace')
      .attr('opacity', d => (d.depth === 0 ? 0 : 0.8))
      .attr('cursor', d => (d.data.isFile ? 'pointer' : 'default'))
      .attr('class', 'file-label')
      .on('click', (event, d) => {
        if (d.data.isFile && d.data.file && onFileSelect) {
          onFileSelect(d.data.file);
        }
      })
      .on('mouseenter', function (event, d) {
        if (d.data.isFile) {
          d3.select(this).attr('opacity', 1).style('text-decoration', 'underline');
          showTooltip(event, d.data.path);
        }
      })
      .on('mouseleave', function (event, d) {
        if (d.data.isFile) {
          d3.select(this).attr('opacity', 0.8).style('text-decoration', 'none');
          hideTooltip();
        }
      });
  }

  // Tooltip management
  let tooltipElement: HTMLDivElement;
  let tooltipVisible = $state(false);
  let tooltipText = $state('');
  let tooltipX = $state(0);
  let tooltipY = $state(0);

  function showTooltip(event: MouseEvent, path: string) {
    tooltipText = path;
    tooltipX = event.clientX + 10;
    tooltipY = event.clientY + 10;
    tooltipVisible = true;
  }

  function hideTooltip() {
    tooltipVisible = false;
  }
</script>

<div bind:this={containerElement} class="relative w-full h-full bg-slate-900">
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

    <!-- Legend -->
    <div class="absolute bottom-4 left-4 bg-slate-800/90 rounded-lg p-3 text-xs text-slate-300 border border-slate-700">
      <div class="font-semibold mb-2">Operations</div>
      <div class="flex flex-col gap-1.5">
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
          <div class="w-2 h-2 rounded-full bg-slate-600 border-2 border-slate-500"></div>
          <span>Directory</span>
        </div>
      </div>
    </div>

    <!-- Tooltip -->
    {#if tooltipVisible}
      <div
        bind:this={tooltipElement}
        class="fixed z-50 px-3 py-2 bg-slate-800 text-slate-100 text-xs rounded-lg shadow-lg border border-slate-600 pointer-events-none font-mono max-w-md truncate"
        style="left: {tooltipX}px; top: {tooltipY}px;"
      >
        {tooltipText}
      </div>
    {/if}
  {/if}
</div>

<style>
  /* Smooth transitions for interactions */
  :global(.nodes circle) {
    transition: r 0.2s ease, stroke-width 0.2s ease;
  }

  :global(.file-label) {
    transition: opacity 0.2s ease;
  }
</style>
