"""
Tests for AIGenerator in ai_generator.py

These tests evaluate:
1. Initialization with valid/invalid API keys
2. Tool calling behavior - does it correctly invoke the CourseSearchTool
3. Response handling with and without tools
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, MagicMock, patch
from ai_generator import AIGenerator
import anthropic


class TestAIGeneratorInitialization:
    """Tests for AIGenerator initialization and API key handling"""
    
    def test_init_with_empty_api_key_creates_client(self):
        """Test that empty API key still creates client (fails on first call)"""
        # This tests the bug we found - empty API key should be caught early
        generator = AIGenerator(api_key="", model="claude-sonnet-4-20250514")
        
        # Client is created but will fail on API call
        assert generator.client is not None
        assert generator.model == "claude-sonnet-4-20250514"
    
    def test_init_with_valid_api_key(self):
        """Test initialization with a valid-looking API key"""
        generator = AIGenerator(
            api_key="sk-ant-api03-test-key",
            model="claude-sonnet-4-20250514"
        )
        
        assert generator.client is not None
        assert generator.model == "claude-sonnet-4-20250514"
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 800


class TestAIGeneratorToolCalling:
    """Tests for AIGenerator tool calling functionality"""
    
    @patch('anthropic.Anthropic')
    def test_generate_response_calls_api_with_tools(self, mock_anthropic_class):
        """Test that generate_response passes tools to API when provided"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Test response", type="text")]
        mock_client.messages.create.return_value = mock_response
        
        generator = AIGenerator(api_key="test-key", model="test-model")
        
        tools = [{
            "name": "search_course_content",
            "description": "Search courses",
            "input_schema": {"type": "object", "properties": {}}
        }]
        
        # Act
        result = generator.generate_response(
            query="What is Python?",
            tools=tools,
            tool_manager=None
        )
        
        # Assert
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == {"type": "auto"}
    
    @patch('anthropic.Anthropic')
    def test_generate_response_executes_tool_when_requested(self, mock_anthropic_class):
        """Test that tool is executed when Claude requests tool use"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # First response: tool use
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "search_course_content"
        mock_tool_use.id = "tool_123"
        mock_tool_use.input = {"query": "Python basics"}
        
        first_response = Mock()
        first_response.stop_reason = "tool_use"
        first_response.content = [mock_tool_use]
        
        # Second response: final answer
        final_response = Mock()
        final_response.content = [Mock(text="Python is a programming language.")]
        
        mock_client.messages.create.side_effect = [first_response, final_response]
        
        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Python is used for..."
        
        generator = AIGenerator(api_key="test-key", model="test-model")
        
        tools = [{"name": "search_course_content", "description": "Search"}]
        
        # Act
        result = generator.generate_response(
            query="What is Python?",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        # Assert
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="Python basics"
        )
        assert result == "Python is a programming language."
    
    @patch('anthropic.Anthropic')
    def test_generate_response_without_tools(self, mock_anthropic_class):
        """Test response generation without tools"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Direct response")]
        mock_client.messages.create.return_value = mock_response
        
        generator = AIGenerator(api_key="test-key", model="test-model")
        
        # Act
        result = generator.generate_response(query="Hello")
        
        # Assert
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "tools" not in call_kwargs
        assert result == "Direct response"


class TestAIGeneratorAPIKeyValidation:
    """Tests specifically for API key validation - the bug we encountered"""

    def test_empty_api_key_fails_on_api_call(self):
        """Test that empty API key causes failure when making API call

        THIS TEST DOCUMENTS THE BUG: When .env file is empty, the API key is ""
        and the Anthropic SDK raises TypeError instead of AuthenticationError.
        """
        generator = AIGenerator(api_key="", model="claude-sonnet-4-20250514")

        # Empty API key raises TypeError with message about authentication
        with pytest.raises(TypeError, match="Could not resolve authentication method"):
            generator.generate_response(query="test")

    def test_none_api_key_fails_on_api_call(self):
        """Test that None API key causes failure"""
        generator = AIGenerator(api_key=None, model="claude-sonnet-4-20250514")

        # None API key also raises TypeError
        with pytest.raises(TypeError, match="Could not resolve authentication method"):
            generator.generate_response(query="test")
    
    def test_invalid_api_key_format_fails(self):
        """Test that invalid API key format fails on API call"""
        generator = AIGenerator(api_key="invalid-key", model="claude-sonnet-4-20250514")
        
        with pytest.raises(anthropic.AuthenticationError):
            generator.generate_response(query="test")


class TestAIGeneratorConversationHistory:
    """Tests for conversation history handling"""
    
    @patch('anthropic.Anthropic')
    def test_conversation_history_included_in_system(self, mock_anthropic_class):
        """Test that conversation history is added to system prompt"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response")]
        mock_client.messages.create.return_value = mock_response
        
        generator = AIGenerator(api_key="test-key", model="test-model")
        
        # Act
        generator.generate_response(
            query="Follow-up question",
            conversation_history="User: Hi\nAssistant: Hello!"
        )
        
        # Assert
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "Previous conversation:" in call_kwargs["system"]
        assert "User: Hi" in call_kwargs["system"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
