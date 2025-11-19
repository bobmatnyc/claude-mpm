"""Tests for PR strategy question templates."""

import pytest

from claude_mpm.templates.questions.pr_strategy import (
    PRReviewTemplate,
    PRSizeTemplate,
    PRWorkflowTemplate,
)
from claude_mpm.utils.structured_questions import ResponseParser


class TestPRWorkflowTemplate:
    """Tests for PRWorkflowTemplate."""

    def test_single_ticket_skips_workflow_question(self):
        """Test that single ticket only asks draft preference."""
        template = PRWorkflowTemplate(num_tickets=1, has_ci=False)
        question_set = template.build()

        # Should only have draft question for single ticket
        assert len(question_set.questions) == 1
        assert question_set.questions[0].header == "Draft PRs"

    def test_multiple_tickets_includes_workflow_question(self):
        """Test that multiple tickets include workflow question."""
        template = PRWorkflowTemplate(num_tickets=3, has_ci=False)
        question_set = template.build()

        # Should have workflow and draft questions
        assert len(question_set.questions) == 2
        headers = [q.header for q in question_set.questions]
        assert "PR Strategy" in headers
        assert "Draft PRs" in headers

    def test_ci_enabled_includes_automerge(self):
        """Test that CI configured includes auto-merge question."""
        template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
        question_set = template.build()

        # Should have all three questions
        assert len(question_set.questions) == 3
        headers = [q.header for q in question_set.questions]
        assert "PR Strategy" in headers
        assert "Draft PRs" in headers
        assert "Auto-merge" in headers

    def test_workflow_question_options(self):
        """Test workflow question has correct options."""
        template = PRWorkflowTemplate(num_tickets=3, has_ci=False)
        question_set = template.build()

        workflow_q = next(
            q for q in question_set.questions if q.header == "PR Strategy"
        )
        option_labels = [opt.label for opt in workflow_q.options]

        assert "Main-based PRs" in option_labels
        assert "Stacked PRs" in option_labels

    def test_draft_question_always_present(self):
        """Test draft question is always included."""
        # Single ticket, no CI
        template1 = PRWorkflowTemplate(num_tickets=1, has_ci=False)
        qs1 = template1.build()
        assert any(q.header == "Draft PRs" for q in qs1.questions)

        # Multiple tickets, with CI
        template2 = PRWorkflowTemplate(num_tickets=5, has_ci=True)
        qs2 = template2.build()
        assert any(q.header == "Draft PRs" for q in qs2.questions)

    def test_to_params_returns_valid_structure(self):
        """Test to_params returns AskUserQuestion-compatible structure."""
        template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
        params = template.to_params()

        assert "questions" in params
        assert isinstance(params["questions"], list)
        assert len(params["questions"]) == 3

        # Validate structure of first question
        first_q = params["questions"][0]
        assert "question" in first_q
        assert "header" in first_q
        assert "options" in first_q
        assert "multiSelect" in first_q


class TestPRSizeTemplate:
    """Tests for PRSizeTemplate."""

    def test_large_changes_asks_split_strategy(self):
        """Test that large changes ask about splitting."""
        template = PRSizeTemplate(estimated_changes=500)
        question_set = template.build()

        assert len(question_set.questions) >= 1
        # Should ask about PR size when changes > 300
        assert question_set.questions[0].header == "PR Size"

    def test_small_changes_asks_commit_strategy(self):
        """Test that small changes ask about commits instead."""
        template = PRSizeTemplate(estimated_changes=100)
        question_set = template.build()

        assert len(question_set.questions) >= 1
        # Should ask about commits for smaller changes
        assert question_set.questions[0].header == "Commits"

    def test_split_options(self):
        """Test split strategy options."""
        template = PRSizeTemplate(estimated_changes=500)
        question_set = template.build()

        size_q = question_set.questions[0]
        option_labels = [opt.label for opt in size_q.options]

        assert "Single large PR" in option_labels
        assert "Split by component" in option_labels
        assert "Split by feature" in option_labels


class TestPRReviewTemplate:
    """Tests for PRReviewTemplate."""

    def test_single_person_team_skips_approvals(self):
        """Test that single person team doesn't ask about approvals."""
        template = PRReviewTemplate(team_size=1, is_critical=False)
        question_set = template.build()

        headers = [q.header for q in question_set.questions]
        # Should not ask about approvals with team_size=1
        assert "Approvals" not in headers
        # But should still ask about timing
        assert "Review When" in headers

    def test_multi_person_team_asks_approvals(self):
        """Test that multi-person team asks about approvals."""
        template = PRReviewTemplate(team_size=3, is_critical=False)
        question_set = template.build()

        headers = [q.header for q in question_set.questions]
        assert "Approvals" in headers
        assert "Review When" in headers

    def test_approval_options(self):
        """Test approval question options."""
        template = PRReviewTemplate(team_size=3, is_critical=False)
        question_set = template.build()

        approval_q = next(q for q in question_set.questions if q.header == "Approvals")
        option_labels = [opt.label for opt in approval_q.options]

        assert "1 approval" in option_labels
        assert "2 approvals" in option_labels


class TestTemplateIntegration:
    """Integration tests for PR strategy templates."""

    def test_complete_pr_workflow(self):
        """Test complete workflow with template and parser."""
        # User has 3 tickets, CI configured
        template = PRWorkflowTemplate(num_tickets=3, has_ci=True)
        question_set = template.build()
        params = template.to_params()

        # Simulate user response
        user_response = {
            "answers": {
                "PR Strategy": "Main-based PRs",
                "Draft PRs": "Yes, as drafts",
                "Auto-merge": "Enable auto-merge",
            }
        }

        # Parse response
        parser = ResponseParser(question_set)
        answers = parser.parse(user_response)

        # Verify answers can be used for delegation
        assert answers["PR Strategy"] == "Main-based PRs"
        assert answers["Draft PRs"] == "Yes, as drafts"
        assert answers["Auto-merge"] == "Enable auto-merge"

        # Convert to delegation parameters
        use_stacked = answers["PR Strategy"] == "Stacked PRs"
        use_draft = answers["Draft PRs"] == "Yes, as drafts"
        auto_merge = answers["Auto-merge"] == "Enable auto-merge"

        assert use_stacked is False
        assert use_draft is True
        assert auto_merge is True
