/** Shared color mapping for agent color dots across components. */
export const colorMap: Record<string, string> = {
	red: 'bg-red-500',
	orange: 'bg-orange-500',
	amber: 'bg-amber-500',
	yellow: 'bg-yellow-500',
	lime: 'bg-lime-500',
	green: 'bg-green-500',
	emerald: 'bg-emerald-500',
	teal: 'bg-teal-500',
	cyan: 'bg-cyan-500',
	sky: 'bg-sky-500',
	blue: 'bg-blue-500',
	indigo: 'bg-indigo-500',
	violet: 'bg-violet-500',
	purple: 'bg-purple-500',
	fuchsia: 'bg-fuchsia-500',
	pink: 'bg-pink-500',
	rose: 'bg-rose-500',
	gray: 'bg-slate-400',
	slate: 'bg-slate-400',
};

/** Returns the Tailwind background class for a given color name, defaulting to slate. */
export function getColorClass(color?: string): string {
	if (!color) return 'bg-slate-400';
	return colorMap[color.toLowerCase()] || 'bg-slate-400';
}
