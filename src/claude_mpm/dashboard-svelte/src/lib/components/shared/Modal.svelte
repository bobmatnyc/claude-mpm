<script lang="ts">
	import { onMount } from 'svelte';

	let {
		open = $bindable(false),
		title = '',
		size = 'md' as 'sm' | 'md' | 'lg',
		closeOnBackdrop = true,
		closeOnEscape = true,
		onclose,
		children,
		footer,
	}: {
		open: boolean;
		title?: string;
		size?: 'sm' | 'md' | 'lg';
		closeOnBackdrop?: boolean;
		closeOnEscape?: boolean;
		onclose?: () => void;
		children?: any;
		footer?: any;
	} = $props();

	const sizeClasses: Record<string, string> = {
		sm: 'max-w-sm',
		md: 'max-w-lg',
		lg: 'max-w-xl',
	};

	let dialogEl: HTMLDivElement | undefined = $state();

	function close() {
		open = false;
		onclose?.();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && closeOnEscape) {
			e.preventDefault();
			close();
		}
		// Focus trap: Tab cycles through focusable elements inside modal
		if (e.key === 'Tab' && dialogEl) {
			const focusable = dialogEl.querySelectorAll<HTMLElement>(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
			);
			if (focusable.length === 0) return;
			const first = focusable[0];
			const last = focusable[focusable.length - 1];

			if (e.shiftKey) {
				if (document.activeElement === first) {
					e.preventDefault();
					last.focus();
				}
			} else {
				if (document.activeElement === last) {
					e.preventDefault();
					first.focus();
				}
			}
		}
	}

	// Auto-focus first focusable element when modal opens
	$effect(() => {
		if (open && dialogEl) {
			const focusable = dialogEl.querySelector<HTMLElement>(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
			);
			if (focusable) {
				// Small delay to ensure rendering is complete
				requestAnimationFrame(() => focusable.focus());
			}
		}
	});
</script>

<svelte:window onkeydown={open ? handleKeydown : undefined} />

{#if open}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<!-- Backdrop -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity duration-200"
			onclick={() => closeOnBackdrop && close()}
		></div>
		<!-- Modal card -->
		<div
			bind:this={dialogEl}
			class="relative {sizeClasses[size]} w-full mx-4 bg-slate-800 border border-slate-700 rounded-lg shadow-xl transition-all duration-200"
			role="dialog"
			aria-modal="true"
			aria-label={title || 'Dialog'}
		>
			{#if title}
				<div class="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
					<h2 class="text-lg font-semibold text-slate-100">{title}</h2>
					<button
						onclick={close}
						class="text-slate-400 hover:text-slate-200 transition-colors p-1 rounded"
						aria-label="Close"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>
			{/if}
			<div class="px-6 py-4">
				{@render children?.()}
			</div>
			{#if footer}
				<div class="px-6 py-4 border-t border-slate-700 flex justify-end gap-3">
					{@render footer()}
				</div>
			{/if}
		</div>
	</div>
{/if}
