"""Tests for structured questions framework.

Tests cover:
- QuestionOption validation and serialization
- StructuredQuestion validation and constraints
- QuestionBuilder fluent API
- QuestionSet validation and serialization
- ResponseParser answer parsing and validation
"""

import pytest

from claude_mpm.utils.structured_questions import (
    ParsedResponse,
    QuestionBuilder,
    QuestionOption,
    QuestionSet,
    QuestionValidationError,
    ResponseParser,
    StructuredQuestion,
)


class TestQuestionOption:
    """Tests for QuestionOption class."""

    def test_valid_option(self):
        """Test creating a valid option."""
        option = QuestionOption(
            label="PostgreSQL", description="Robust relational database"
        )
        assert option.label == "PostgreSQL"
        assert option.description == "Robust relational database"

    def test_empty_label_fails(self):
        """Test that empty label raises validation error."""
        with pytest.raises(QuestionValidationError, match="label cannot be empty"):
            QuestionOption(label="", description="Test description")

    def test_whitespace_label_fails(self):
        """Test that whitespace-only label raises validation error."""
        with pytest.raises(QuestionValidationError, match="label cannot be empty"):
            QuestionOption(label="   ", description="Test description")

    def test_empty_description_fails(self):
        """Test that empty description raises validation error."""
        with pytest.raises(
            QuestionValidationError, match="description cannot be empty"
        ):
            QuestionOption(label="Test", description="")

    def test_long_label_fails(self):
        """Test that overly long label raises validation error."""
        long_label = "A" * 51  # Max is 50
        with pytest.raises(QuestionValidationError, match="label too long"):
            QuestionOption(label=long_label, description="Test description")

    def test_to_dict(self):
        """Test serialization to dictionary."""
        option = QuestionOption(label="Redis", description="In-memory data store")
        result = option.to_dict()
        assert result == {"label": "Redis", "description": "In-memory data store"}


class TestStructuredQuestion:
    """Tests for StructuredQuestion class."""

    def test_valid_question(self):
        """Test creating a valid question."""
        options = [
            QuestionOption("Option 1", "First option"),
            QuestionOption("Option 2", "Second option"),
        ]
        question = StructuredQuestion(
            question="Which option?", header="Choice", options=options
        )
        assert question.question == "Which option?"
        assert question.header == "Choice"
        assert len(question.options) == 2
        assert question.multi_select is False

    def test_multi_select_question(self):
        """Test creating a multi-select question."""
        options = [
            QuestionOption("A", "First"),
            QuestionOption("B", "Second"),
        ]
        question = StructuredQuestion(
            question="Select multiple?",
            header="Multi",
            options=options,
            multi_select=True,
        )
        assert question.multi_select is True

    def test_question_without_question_mark_fails(self):
        """Test that question without '?' fails validation."""
        options = [
            QuestionOption("A", "First"),
            QuestionOption("B", "Second"),
        ]
        with pytest.raises(QuestionValidationError, match="should end with"):
            StructuredQuestion(
                question="This is not a question", header="Test", options=options
            )

    def test_empty_question_text_fails(self):
        """Test that empty question text fails validation."""
        options = [
            QuestionOption("A", "First"),
            QuestionOption("B", "Second"),
        ]
        with pytest.raises(QuestionValidationError, match="cannot be empty"):
            StructuredQuestion(question="", header="Test", options=options)

    def test_empty_header_fails(self):
        """Test that empty header fails validation."""
        options = [
            QuestionOption("A", "First"),
            QuestionOption("B", "Second"),
        ]
        with pytest.raises(QuestionValidationError, match="Header cannot be empty"):
            StructuredQuestion(question="Test?", header="", options=options)

    def test_long_header_fails(self):
        """Test that header > 12 chars fails validation."""
        options = [
            QuestionOption("A", "First"),
            QuestionOption("B", "Second"),
        ]
        with pytest.raises(QuestionValidationError, match="Header too long"):
            StructuredQuestion(
                question="Test?", header="VeryLongHeader", options=options
            )

    def test_too_few_options_fails(self):
        """Test that < 2 options fails validation."""
        options = [QuestionOption("A", "Only one")]
        with pytest.raises(QuestionValidationError, match="at least 2 options"):
            StructuredQuestion(question="Test?", header="Test", options=options)

    def test_too_many_options_fails(self):
        """Test that > 4 options fails validation."""
        options = [
            QuestionOption("A", "First"),
            QuestionOption("B", "Second"),
            QuestionOption("C", "Third"),
            QuestionOption("D", "Fourth"),
            QuestionOption("E", "Fifth"),
        ]
        with pytest.raises(QuestionValidationError, match="at most 4 options"):
            StructuredQuestion(question="Test?", header="Test", options=options)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        options = [
            QuestionOption("pytest", "Modern testing"),
            QuestionOption("unittest", "Built-in testing"),
        ]
        question = StructuredQuestion(
            question="Which testing framework?",
            header="Testing",
            options=options,
            multi_select=False,
        )
        result = question.to_dict()
        assert result == {
            "question": "Which testing framework?",
            "header": "Testing",
            "options": [
                {"label": "pytest", "description": "Modern testing"},
                {"label": "unittest", "description": "Built-in testing"},
            ],
            "multiSelect": False,
        }


class TestQuestionBuilder:
    """Tests for QuestionBuilder fluent API."""

    def test_build_simple_question(self):
        """Test building a simple question."""
        question = (
            QuestionBuilder()
            .ask("What is your choice?")
            .header("Choice")
            .add_option("A", "First option")
            .add_option("B", "Second option")
            .build()
        )
        assert question.question == "What is your choice?"
        assert question.header == "Choice"
        assert len(question.options) == 2

    def test_build_multi_select_question(self):
        """Test building a multi-select question."""
        question = (
            QuestionBuilder()
            .ask("Select features?")
            .header("Features")
            .add_option("Auth", "Authentication")
            .add_option("Search", "Search functionality")
            .multi_select()
            .build()
        )
        assert question.multi_select is True

    def test_with_options_method(self):
        """Test using with_options to set all options at once."""
        options = [
            QuestionOption("A", "First"),
            QuestionOption("B", "Second"),
        ]
        question = (
            QuestionBuilder().ask("Test?").header("Test").with_options(options).build()
        )
        assert len(question.options) == 2

    def test_build_without_question_fails(self):
        """Test that building without question text fails."""
        with pytest.raises(QuestionValidationError, match="Question text is required"):
            QuestionBuilder().header("Test").add_option("A", "First").build()

    def test_build_without_header_fails(self):
        """Test that building without header fails."""
        with pytest.raises(QuestionValidationError, match="Header is required"):
            QuestionBuilder().ask("Test?").add_option("A", "First").build()

    def test_method_chaining(self):
        """Test that all methods support chaining."""
        builder = QuestionBuilder()
        result = builder.ask("Test?")
        assert result is builder

        result = builder.header("Test")
        assert result is builder

        result = builder.add_option("A", "First")
        assert result is builder

        result = builder.multi_select(True)
        assert result is builder


class TestQuestionSet:
    """Tests for QuestionSet class."""

    def test_create_with_single_question(self):
        """Test creating a question set with one question."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])
        assert len(question_set.questions) == 1

    def test_create_with_multiple_questions(self):
        """Test creating a question set with multiple questions."""
        q1 = (
            QuestionBuilder()
            .ask("Question 1?")
            .header("Q1")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        q2 = (
            QuestionBuilder()
            .ask("Question 2?")
            .header("Q2")
            .add_option("X", "Third")
            .add_option("Y", "Fourth")
            .build()
        )
        question_set = QuestionSet([q1, q2])
        assert len(question_set.questions) == 2

    def test_empty_question_set_fails(self):
        """Test that empty question set fails validation."""
        with pytest.raises(QuestionValidationError, match="at least 1 question"):
            QuestionSet([])

    def test_too_many_questions_fails(self):
        """Test that > 4 questions fails validation."""
        questions = []
        for i in range(5):
            q = (
                QuestionBuilder()
                .ask(f"Question {i}?")
                .header(f"Q{i}")
                .add_option("A", "First")
                .add_option("B", "Second")
                .build()
            )
            questions.append(q)

        with pytest.raises(QuestionValidationError, match="at most 4 questions"):
            QuestionSet(questions)

    def test_add_question(self):
        """Test adding a question to existing set."""
        q1 = (
            QuestionBuilder()
            .ask("Q1?")
            .header("Q1")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([q1])

        q2 = (
            QuestionBuilder()
            .ask("Q2?")
            .header("Q2")
            .add_option("X", "Third")
            .add_option("Y", "Fourth")
            .build()
        )
        result = question_set.add(q2)

        assert result is question_set  # Test chaining
        assert len(question_set.questions) == 2

    def test_add_too_many_fails(self):
        """Test that adding beyond 4 questions fails."""
        questions = []
        for i in range(4):
            q = (
                QuestionBuilder()
                .ask(f"Q{i}?")
                .header(f"Q{i}")
                .add_option("A", "First")
                .add_option("B", "Second")
                .build()
            )
            questions.append(q)

        question_set = QuestionSet(questions)

        extra_q = (
            QuestionBuilder()
            .ask("Extra?")
            .header("Extra")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )

        with pytest.raises(QuestionValidationError, match="Cannot add more than 4"):
            question_set.add(extra_q)

    def test_to_ask_user_question_params(self):
        """Test conversion to AskUserQuestion parameters."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])
        params = question_set.to_ask_user_question_params()

        assert "questions" in params
        assert len(params["questions"]) == 1
        assert params["questions"][0]["question"] == "Test?"
        assert params["questions"][0]["header"] == "Test"


class TestResponseParser:
    """Tests for ResponseParser class."""

    def test_parse_single_select_response(self):
        """Test parsing a single-select response."""
        question = (
            QuestionBuilder()
            .ask("Which database?")
            .header("Database")
            .add_option("PostgreSQL", "Relational database")
            .add_option("MongoDB", "NoSQL database")
            .build()
        )
        question_set = QuestionSet([question])
        parser = ResponseParser(question_set)

        response = {"answers": {"Database": "PostgreSQL"}}
        answers = parser.parse(response)

        assert answers["Database"] == "PostgreSQL"

    def test_parse_multi_select_response_list(self):
        """Test parsing a multi-select response (list format)."""
        question = (
            QuestionBuilder()
            .ask("Which features?")
            .header("Features")
            .add_option("Auth", "Authentication")
            .add_option("Search", "Search")
            .multi_select()
            .build()
        )
        question_set = QuestionSet([question])
        parser = ResponseParser(question_set)

        response = {"answers": {"Features": ["Auth", "Search"]}}
        answers = parser.parse(response)

        assert answers["Features"] == ["Auth", "Search"]

    def test_parse_multi_select_response_string(self):
        """Test parsing a multi-select response (comma-separated string)."""
        question = (
            QuestionBuilder()
            .ask("Which features?")
            .header("Features")
            .add_option("Auth", "Authentication")
            .add_option("Search", "Search")
            .multi_select()
            .build()
        )
        question_set = QuestionSet([question])
        parser = ResponseParser(question_set)

        response = {"answers": {"Features": "Auth, Search"}}
        answers = parser.parse(response)

        assert answers["Features"] == ["Auth", "Search"]

    def test_parse_multiple_questions(self):
        """Test parsing response with multiple questions."""
        q1 = (
            QuestionBuilder()
            .ask("Database?")
            .header("DB")
            .add_option("PostgreSQL", "SQL")
            .add_option("MongoDB", "NoSQL")
            .build()
        )
        q2 = (
            QuestionBuilder()
            .ask("Testing?")
            .header("Test")
            .add_option("pytest", "Modern")
            .add_option("unittest", "Built-in")
            .build()
        )
        question_set = QuestionSet([q1, q2])
        parser = ResponseParser(question_set)

        response = {"answers": {"DB": "PostgreSQL", "Test": "pytest"}}
        answers = parser.parse(response)

        assert answers["DB"] == "PostgreSQL"
        assert answers["Test"] == "pytest"

    def test_parse_optional_question(self):
        """Test parsing when some questions are not answered."""
        q1 = (
            QuestionBuilder()
            .ask("Required?")
            .header("Req")
            .add_option("Yes", "Required")
            .add_option("No", "Optional")
            .build()
        )
        q2 = (
            QuestionBuilder()
            .ask("Optional?")
            .header("Opt")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([q1, q2])
        parser = ResponseParser(question_set)

        # Only answer first question
        response = {"answers": {"Req": "Yes"}}
        answers = parser.parse(response)

        assert answers["Req"] == "Yes"
        assert "Opt" not in answers

    def test_get_answer(self):
        """Test get_answer helper method."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])
        parser = ResponseParser(question_set)

        response = {"answers": {"Test": "A"}}
        answers = parser.parse(response)

        assert parser.get_answer(answers, "Test") == "A"
        assert parser.get_answer(answers, "NonExistent") is None

    def test_was_answered(self):
        """Test was_answered helper method."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])
        parser = ResponseParser(question_set)

        response = {"answers": {"Test": "A"}}
        answers = parser.parse(response)

        assert parser.was_answered(answers, "Test") is True
        assert parser.was_answered(answers, "NotAnswered") is False

    def test_invalid_response_format(self):
        """Test that invalid response format raises error."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])
        parser = ResponseParser(question_set)

        with pytest.raises(QuestionValidationError, match="must be a dictionary"):
            parser.parse("not a dict")

    def test_missing_answers_key(self):
        """Test that response without 'answers' key returns empty dict."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])
        parser = ResponseParser(question_set)

        # Missing 'answers' key should return empty dict (all questions optional)
        result = parser.parse({"wrong_key": {}})
        assert result == {}


class TestParsedResponse:
    """Tests for ParsedResponse class."""

    def test_get_answer(self):
        """Test getting answer for a specific question."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])
        answers = {"Test": "A"}
        parsed = ParsedResponse(question_set, answers)

        assert parsed.get("Test") == "A"
        assert parsed.get("NonExistent") is None

    def test_was_answered(self):
        """Test checking if question was answered."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])
        answers = {"Test": "A"}
        parsed = ParsedResponse(question_set, answers)

        assert parsed.was_answered("Test") is True
        assert parsed.was_answered("NotAnswered") is False

    def test_get_all(self):
        """Test getting all answers as dictionary."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])
        answers = {"Test": "A", "Other": "B"}
        parsed = ParsedResponse(question_set, answers)

        all_answers = parsed.get_all()
        assert all_answers == {"Test": "A", "Other": "B"}
        # Verify it's a copy
        all_answers["Test"] = "Modified"
        assert parsed.get("Test") == "A"


class TestFallbackMechanism:
    """Tests for text fallback mechanism."""

    def test_should_use_fallback_empty_response(self):
        """Test fallback detection for empty response."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        assert question_set._should_use_fallback({}) is True
        assert question_set._should_use_fallback(None) is True
        assert question_set._should_use_fallback("not a dict") is True

    def test_should_use_fallback_missing_answers(self):
        """Test fallback detection for missing answers key."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        assert question_set._should_use_fallback({"wrong_key": {}}) is True

    def test_should_use_fallback_empty_answers(self):
        """Test fallback detection for empty answers."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        assert question_set._should_use_fallback({"answers": {}}) is True

    def test_should_use_fallback_fake_responses(self):
        """Test fallback detection for fake/placeholder responses."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        assert question_set._should_use_fallback({"answers": {"Test": "."}}) is True
        assert question_set._should_use_fallback({"answers": {"Test": ""}}) is True

    def test_should_not_use_fallback_valid_response(self):
        """Test that valid responses don't trigger fallback."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        assert question_set._should_use_fallback({"answers": {"Test": "A"}}) is False

    def test_match_single_input_numeric(self):
        """Test matching numeric input to options."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("PostgreSQL", "Database 1")
            .add_option("MongoDB", "Database 2")
            .build()
        )
        question_set = QuestionSet([question])

        assert question_set._match_single_input("1", question.options) == "PostgreSQL"
        assert question_set._match_single_input("2", question.options) == "MongoDB"
        assert question_set._match_single_input("3", question.options) is None

    def test_match_single_input_exact(self):
        """Test exact label matching."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("PostgreSQL", "Database 1")
            .add_option("MongoDB", "Database 2")
            .build()
        )
        question_set = QuestionSet([question])

        assert (
            question_set._match_single_input("PostgreSQL", question.options)
            == "PostgreSQL"
        )
        assert (
            question_set._match_single_input("postgresql", question.options)
            == "PostgreSQL"
        )
        assert (
            question_set._match_single_input("MONGODB", question.options) == "MongoDB"
        )

    def test_match_single_input_partial(self):
        """Test partial label matching."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("PostgreSQL", "Database 1")
            .add_option("MongoDB", "Database 2")
            .build()
        )
        question_set = QuestionSet([question])

        assert (
            question_set._match_single_input("postgres", question.options)
            == "PostgreSQL"
        )
        assert question_set._match_single_input("mongo", question.options) == "MongoDB"

    def test_match_single_input_no_match(self):
        """Test that non-matching input returns None."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("PostgreSQL", "Database 1")
            .add_option("MongoDB", "Database 2")
            .build()
        )
        question_set = QuestionSet([question])

        assert question_set._match_single_input("Redis", question.options) is None

    def test_parse_text_response_single_numeric(self):
        """Test parsing single numeric response."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("Option A", "First")
            .add_option("Option B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        result = question_set._parse_text_response("1", question.options, False)
        assert result == "Option A"

    def test_parse_text_response_single_label(self):
        """Test parsing single label response."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("Option A", "First")
            .add_option("Option B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        result = question_set._parse_text_response("Option A", question.options, False)
        assert result == "Option A"

    def test_parse_text_response_single_custom(self):
        """Test parsing custom answer."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("Option A", "First")
            .add_option("Option B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        result = question_set._parse_text_response(
            "Custom answer", question.options, False
        )
        assert result == "Custom answer"

    def test_parse_text_response_multi_numeric(self):
        """Test parsing multi-select numeric response."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("Option A", "First")
            .add_option("Option B", "Second")
            .add_option("Option C", "Third")
            .build()
        )
        question_set = QuestionSet([question])

        result = question_set._parse_text_response("1,2", question.options, True)
        assert result == ["Option A", "Option B"]

    def test_parse_text_response_multi_labels(self):
        """Test parsing multi-select label response."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("Auth", "Authentication")
            .add_option("Search", "Search feature")
            .add_option("Analytics", "Analytics feature")
            .build()
        )
        question_set = QuestionSet([question])

        result = question_set._parse_text_response(
            "Auth, Search", question.options, True
        )
        assert result == ["Auth", "Search"]

    def test_parse_text_response_multi_mixed(self):
        """Test parsing multi-select mixed (numbers and labels)."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("Auth", "Authentication")
            .add_option("Search", "Search feature")
            .add_option("Analytics", "Analytics feature")
            .build()
        )
        question_set = QuestionSet([question])

        result = question_set._parse_text_response("1, Search", question.options, True)
        assert result == ["Auth", "Search"]

    def test_parse_text_response_multi_custom(self):
        """Test parsing multi-select with custom answers."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("Auth", "Authentication")
            .add_option("Search", "Search feature")
            .build()
        )
        question_set = QuestionSet([question])

        result = question_set._parse_text_response(
            "Auth, Custom feature", question.options, True
        )
        assert result == ["Auth", "Custom feature"]

    def test_execute_with_valid_response(self):
        """Test execute with valid AskUserQuestion response."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        response = {"answers": {"Test": "A"}}
        parsed = question_set.execute(response)

        assert isinstance(parsed, ParsedResponse)
        assert parsed.get("Test") == "A"

    def test_execute_with_empty_response_no_fallback(self):
        """Test execute with empty response and fallback disabled."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        # Empty response with fallback disabled should use standard parser
        # which returns empty dict for missing answers
        response = {"answers": {}}
        parsed = question_set.execute(response, use_fallback_if_needed=False)
        assert parsed.get("Test") is None

    def test_execute_with_none_response_no_fallback(self):
        """Test execute with None response and fallback disabled."""
        question = (
            QuestionBuilder()
            .ask("Test?")
            .header("Test")
            .add_option("A", "First")
            .add_option("B", "Second")
            .build()
        )
        question_set = QuestionSet([question])

        with pytest.raises(
            QuestionValidationError, match="No response provided and fallback disabled"
        ):
            question_set.execute(None, use_fallback_if_needed=False)


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_workflow(self):
        """Test a complete question -> response -> parse workflow."""
        # Build questions
        q1 = (
            QuestionBuilder()
            .ask("Which database?")
            .header("Database")
            .add_option("PostgreSQL", "Robust SQL database")
            .add_option("MongoDB", "Flexible NoSQL database")
            .build()
        )

        q2 = (
            QuestionBuilder()
            .ask("Which features?")
            .header("Features")
            .add_option("Auth", "User authentication")
            .add_option("Search", "Full-text search")
            .add_option("Analytics", "Usage analytics")
            .multi_select()
            .build()
        )

        # Create question set
        question_set = QuestionSet([q1, q2])

        # Get parameters for AskUserQuestion
        params = question_set.to_ask_user_question_params()
        assert "questions" in params
        assert len(params["questions"]) == 2

        # Simulate user response
        user_response = {
            "answers": {"Database": "PostgreSQL", "Features": ["Auth", "Search"]}
        }

        # Parse response
        parser = ResponseParser(question_set)
        answers = parser.parse(user_response)

        # Verify parsed answers
        assert answers["Database"] == "PostgreSQL"
        assert answers["Features"] == ["Auth", "Search"]
        assert parser.was_answered(answers, "Database")
        assert parser.was_answered(answers, "Features")

    def test_complete_workflow_with_execute(self):
        """Test complete workflow using new execute method."""
        # Build questions
        q1 = (
            QuestionBuilder()
            .ask("Which database?")
            .header("Database")
            .add_option("PostgreSQL", "Robust SQL database")
            .add_option("MongoDB", "Flexible NoSQL database")
            .build()
        )

        q2 = (
            QuestionBuilder()
            .ask("Which features?")
            .header("Features")
            .add_option("Auth", "User authentication")
            .add_option("Search", "Full-text search")
            .multi_select()
            .build()
        )

        # Create question set
        question_set = QuestionSet([q1, q2])

        # Simulate user response
        user_response = {
            "answers": {"Database": "PostgreSQL", "Features": ["Auth", "Search"]}
        }

        # Execute and parse in one step
        parsed = question_set.execute(user_response)

        # Verify parsed answers
        assert parsed.get("Database") == "PostgreSQL"
        assert parsed.get("Features") == ["Auth", "Search"]
        assert parsed.was_answered("Database")
        assert parsed.was_answered("Features")
