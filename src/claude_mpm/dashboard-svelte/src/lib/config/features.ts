/**
 * Feature flags for the Claude MPM dashboard.
 *
 * These flags control the rollout of new UI features across sub-phases.
 * Set a flag to `false` to disable a feature without removing code.
 */
export const FEATURES = {
	/** Sub-Phase 3A: Rich detail panels with collapsible sections, metadata grids */
	RICH_DETAIL_PANELS: true,

	/** Sub-Phase 3B: Filter dropdowns in agent and skill list headers */
	FILTER_DROPDOWNS: true,

	/** Sub-Phase 3B: Version mismatch indicators between deployed and available */
	VERSION_MISMATCH: true,

	/** Sub-Phase 3C: Clickable collaboration/handoff agent links in detail panels */
	COLLABORATION_LINKS: true,

	/** Sub-Phase 3C: Skill links merged into detail panels (deprecates Skill Links tab) */
	SKILL_LINKS_MERGE: true,

	/** Sub-Phase 3B: Search text highlighting in list items */
	SEARCH_ENHANCEMENTS: true,
} as const;

export type FeatureFlag = keyof typeof FEATURES;
