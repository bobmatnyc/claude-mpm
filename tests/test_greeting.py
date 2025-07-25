import pytest
from greeting import greet


class TestGreetFunction:
    """Test suite for the greet() function."""
    
    def test_greet_with_simple_name(self):
        """Test greeting with a simple name."""
        assert greet("Alice") == "Hello, Alice!"
        assert greet("Bob") == "Hello, Bob!"
        assert greet("Charlie") == "Hello, Charlie!"
    
    def test_greet_with_empty_string(self):
        """Test greeting with empty string."""
        assert greet("") == "Hello, !"
    
    def test_greet_with_spaces(self):
        """Test greeting with names containing spaces."""
        assert greet("John Doe") == "Hello, John Doe!"
        assert greet("Mary Jane Watson") == "Hello, Mary Jane Watson!"
    
    def test_greet_with_special_characters(self):
        """Test greeting with special characters in names."""
        assert greet("O'Brien") == "Hello, O'Brien!"
        assert greet("Jean-Claude") == "Hello, Jean-Claude!"
        assert greet("José") == "Hello, José!"
        assert greet("李明") == "Hello, 李明!"
    
    def test_greet_with_numbers(self):
        """Test greeting with numbers in names."""
        assert greet("Agent007") == "Hello, Agent007!"
        assert greet("R2D2") == "Hello, R2D2!"
        assert greet("4chan") == "Hello, 4chan!"
    
    def test_greet_with_whitespace_variations(self):
        """Test greeting with various whitespace scenarios."""
        assert greet("  Alice  ") == "Hello,   Alice  !"
        assert greet("\tBob\t") == "Hello, \tBob\t!"
        assert greet("Charlie\n") == "Hello, Charlie\n!"
    
    def test_greet_with_punctuation(self):
        """Test greeting with punctuation marks."""
        assert greet("Mr. Smith") == "Hello, Mr. Smith!"
        assert greet("Dr.") == "Hello, Dr.!"
        assert greet("!!!") == "Hello, !!!!"
    
    def test_greet_return_type(self):
        """Test that greet() returns a string."""
        result = greet("Test")
        assert isinstance(result, str)
    
    def test_greet_format_consistency(self):
        """Test that greeting format is consistent."""
        name = "TestUser"
        result = greet(name)
        assert result.startswith("Hello, ")
        assert result.endswith("!")
        assert name in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])