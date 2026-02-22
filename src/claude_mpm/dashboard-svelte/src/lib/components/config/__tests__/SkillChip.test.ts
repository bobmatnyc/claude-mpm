import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import SkillChip from '../SkillChip.svelte';
import type { SkillLink } from '$lib/stores/config/skillLinks.svelte';

function makeSkill(overrides: Partial<SkillLink> = {}): SkillLink {
	return {
		skill_name: 'test-skill',
		source: { type: 'frontmatter', label: 'Frontmatter' },
		is_deployed: true,
		is_auto_managed: false,
		...overrides,
	};
}

describe('SkillChip', () => {
	it('renders skill name', () => {
		render(SkillChip, { props: { skill: makeSkill({ skill_name: 'my-skill' }) } });
		expect(screen.getByText('my-skill')).toBeInTheDocument();
	});

	it('shows auto badge for auto-managed skills', () => {
		render(SkillChip, { props: { skill: makeSkill({ is_auto_managed: true }) } });
		expect(screen.getByText('auto')).toBeInTheDocument();
	});

	it('does not show auto badge for non-auto-managed skills', () => {
		render(SkillChip, { props: { skill: makeSkill({ is_auto_managed: false }) } });
		expect(screen.queryByText('auto')).not.toBeInTheDocument();
	});

	it('shows warning icon for undeployed skills', () => {
		const { container } = render(SkillChip, {
			props: { skill: makeSkill({ is_deployed: false }) },
		});
		// Undeployed skills get amber/warning styling
		const chip = container.querySelector('span');
		expect(chip?.className).toContain('amber');
	});

	it('renders frontmatter source with blue dot', () => {
		const { container } = render(SkillChip, {
			props: { skill: makeSkill({ source: { type: 'frontmatter', label: 'Frontmatter' } }) },
		});
		const dot = container.querySelector('.bg-blue-500');
		expect(dot).toBeInTheDocument();
	});

	it('renders content_marker source with purple dot', () => {
		const { container } = render(SkillChip, {
			props: { skill: makeSkill({ source: { type: 'content_marker', label: 'Content Marker' } }) },
		});
		const dot = container.querySelector('.bg-purple-500');
		expect(dot).toBeInTheDocument();
	});

	it('renders user_defined source with green dot', () => {
		const { container } = render(SkillChip, {
			props: { skill: makeSkill({ source: { type: 'user_defined', label: 'User Defined' } }) },
		});
		const dot = container.querySelector('.bg-emerald-500');
		expect(dot).toBeInTheDocument();
	});

	it('renders inferred source with gray dot', () => {
		const { container } = render(SkillChip, {
			props: { skill: makeSkill({ source: { type: 'inferred', label: 'Inferred' } }) },
		});
		const dot = container.querySelector('.bg-slate-400');
		expect(dot).toBeInTheDocument();
	});

	it('has tooltip with source info', () => {
		const { container } = render(SkillChip, {
			props: { skill: makeSkill({ source: { type: 'frontmatter', label: 'Frontmatter' } }) },
		});
		const chip = container.querySelector('[title]');
		expect(chip?.getAttribute('title')).toContain('Source: Frontmatter');
	});
});
