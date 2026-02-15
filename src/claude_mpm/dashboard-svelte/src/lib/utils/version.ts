/** Shared version comparison utility used across agent/skill lists and version badges. */

export type VersionStatus = 'current' | 'outdated' | 'unknown';

/**
 * Compare deployed vs available version strings.
 * Returns 'current' if they match, 'outdated' if deployed < available,
 * or 'unknown' if either is missing or not valid semver.
 */
export function compareVersions(deployed: string, available: string): VersionStatus {
	if (!deployed || !available) return 'unknown';
	const parts = (v: string) => v.replace(/^v/, '').split('.').map(Number);
	const [dM, dm, dp] = parts(deployed);
	const [aM, am, ap] = parts(available);
	if ([dM, dm, dp, aM, am, ap].some(isNaN)) return 'unknown';
	if (dM === aM && dm === am && dp === ap) return 'current';
	if (dM < aM || (dM === aM && dm < am) || (dM === aM && dm === am && dp < ap)) return 'outdated';
	return 'current';
}
