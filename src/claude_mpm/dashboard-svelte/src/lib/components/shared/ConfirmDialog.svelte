<script lang="ts">
	import Modal from './Modal.svelte';

	let {
		open = $bindable(false),
		title = 'Confirm Action',
		description = '',
		confirmText = '',
		confirmLabel = 'Confirm',
		onConfirm,
		onCancel,
		destructive = true,
	}: {
		open: boolean;
		title?: string;
		description?: string;
		confirmText?: string;
		confirmLabel?: string;
		onConfirm: () => void;
		onCancel: () => void;
		destructive?: boolean;
	} = $props();

	let typedText = $state('');

	let canConfirm = $derived(
		confirmText ? typedText.toLowerCase() === confirmText.toLowerCase() : true
	);

	function handleConfirm() {
		if (!canConfirm) return;
		onConfirm();
		typedText = '';
	}

	function handleCancel() {
		typedText = '';
		onCancel();
	}

	// Reset typed text when dialog closes
	$effect(() => {
		if (!open) typedText = '';
	});
</script>

<Modal bind:open size="sm" {title} closeOnBackdrop={true} closeOnEscape={true} onclose={handleCancel}>
	{#snippet children()}
		<!-- Warning icon + description -->
		{#if destructive}
			<div class="flex items-start gap-3 mb-4">
				<div class="flex-shrink-0 w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center">
					<svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
					</svg>
				</div>
				<p class="text-sm text-slate-300">{description}</p>
			</div>
		{:else}
			{#if description}
				<p class="text-sm text-slate-300 mb-4">{description}</p>
			{/if}
		{/if}

		<!-- Type-to-confirm input -->
		{#if confirmText}
			<div class="mt-3">
				<label class="block text-xs text-slate-400 mb-1.5">
					Type <span class="font-mono font-semibold text-slate-200">{confirmText}</span> to confirm
				</label>
				<input
					type="text"
					bind:value={typedText}
					placeholder={confirmText}
					class="w-full px-3 py-2 text-sm bg-slate-900 border border-slate-600 rounded-md
						text-slate-100 placeholder-slate-500
						focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
				/>
			</div>
		{/if}
	{/snippet}

	{#snippet footer()}
		<button
			onclick={handleCancel}
			class="px-4 py-2 text-sm font-medium text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
		>
			Cancel
		</button>
		<button
			onclick={handleConfirm}
			disabled={!canConfirm}
			class="px-4 py-2 text-sm font-medium rounded-lg transition-colors
				disabled:opacity-50 disabled:cursor-not-allowed
				{destructive
					? 'text-white bg-red-600 hover:bg-red-700'
					: 'text-white bg-cyan-600 hover:bg-cyan-700'}"
		>
			{confirmLabel}
		</button>
	{/snippet}
</Modal>
