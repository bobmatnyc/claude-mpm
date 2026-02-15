<script lang="ts">
	import { compareVersions } from '$lib/utils/version';

	interface Props {
		deployedVersion: string;
		availableVersion?: string;
	}

	let { deployedVersion, availableVersion }: Props = $props();

	let status = $derived(
		availableVersion
			? compareVersions(deployedVersion, availableVersion)
			: 'unknown'
	);

	let displayVersion = $derived(
		deployedVersion.startsWith('v') ? deployedVersion : `v${deployedVersion}`
	);

	let availableDisplay = $derived(
		availableVersion
			? (availableVersion.startsWith('v') ? availableVersion : `v${availableVersion}`)
			: ''
	);

	let badgeClass = $derived(
		status === 'current'
			? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
			: status === 'outdated'
				? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
				: 'bg-slate-100 text-slate-600 dark:bg-slate-700/50 dark:text-slate-400'
	);

	let titleText = $derived(
		status === 'outdated'
			? `Update available: ${displayVersion} \u2192 ${availableDisplay}`
			: status === 'current'
				? `Version ${displayVersion} is current`
				: `Version ${displayVersion}`
	);

	let ariaLabel = $derived(
		status === 'outdated'
			? `Version ${displayVersion}, update available to ${availableDisplay}`
			: status === 'current'
				? `Version ${displayVersion}, up to date`
				: `Version ${displayVersion}, status unknown`
	);
</script>

<span
	class="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium rounded-full {badgeClass}"
	title={titleText}
	role="status"
	aria-label={ariaLabel}
>
	{displayVersion}
	{#if status === 'outdated'}
		<span class="opacity-70">&rarr;</span>
		<span>{availableDisplay}</span>
	{/if}
</span>
