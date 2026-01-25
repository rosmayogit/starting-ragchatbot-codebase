"""
Tests for RAGSystem query handling in rag_system.py

These tests evaluate:
1. End-to-end query processing
2. Content-related question handling
3. Error handling when components fail
4. Integration between components
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass


@dataclass
class MockConfig:
    """Mock configuration for testing"""
    ANTHROPIC_API_KEY: str = "test-api-key"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = "./test_chroma_db"


class TestRAGSystemQueryHandling:
    """Tests for RAGSystem.query() method"""
    
    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    def test_query_returns_response_and_sources(
        self, mock_doc_proc, mock_session, mock_ai_gen, mock_vector_store
    ):
        """Test that query returns both response and sources"""
        from rag_system import RAGSystem
        
        # Arrange
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "This is the answer."
        mock_ai_gen.return_value = mock_ai_instance
        
        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance
        
        config = MockConfig()
        rag = RAGSystem(config)
        
        # Simulate sources being set by tool
        rag.tool_manager.tools["search_course_content"].last_sources = [
            {"text": "Course A - Lesson 1", "link": "https://example.com"}
        ]
        
        # Act
        response, sources = rag.query("What is Python?", session_id="test_session")
        
        # Assert
        assert response == "This is the answer."
        assert len(sources) == 1
        assert sources[0]["text"] == "Course A - Lesson 1"
    
    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    def test_query_passes_tools_to_ai_generator(
        self, mock_doc_proc, mock_session, mock_ai_gen, mock_vector_store
    ):
        """Test that query provides tools to AIGenerator"""
        from rag_system import RAGSystem
        
        # Arrange
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "Response"
        mock_ai_gen.return_value = mock_ai_instance
        
        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance
        
        config = MockConfig()
        rag = RAGSystem(config)
        
        # Act
        rag.query("Test query")
        
        # Assert
        call_kwargs = mock_ai_instance.generate_response.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] is not None
        assert len(call_kwargs["tools"]) > 0
        assert call_kwargs["tool_manager"] is not None
    
    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    def test_query_resets_sources_after_retrieval(
        self, mock_doc_proc, mock_session, mock_ai_gen, mock_vector_store
    ):
        """Test that sources are reset after being retrieved"""
        from rag_system import RAGSystem
        
        # Arrange
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "Response"
        mock_ai_gen.return_value = mock_ai_instance
        
        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance
        
        config = MockConfig()
        rag = RAGSystem(config)
        
        # Set initial sources
        rag.tool_manager.tools["search_course_content"].last_sources = [
            {"text": "Source 1", "link": None}
        ]
        
        # Act
        rag.query("Test query")
        
        # Assert - sources should be reset
        sources = rag.tool_manager.get_last_sources()
        assert sources == []


class TestRAGSystemErrorHandling:
    """Tests for error handling in RAG system"""
    
    def test_empty_api_key_causes_query_failure(self):
        """Test that empty API key causes query to fail - THE BUG WE FOUND

        This documents the root cause of 'Query failed' error:
        When .env file is empty or missing ANTHROPIC_API_KEY, the config loads ""
        as the API key, and the Anthropic SDK raises TypeError on first API call.
        """
        from rag_system import RAGSystem

        # Arrange - Config with empty API key (the bug!)
        config = MockConfig()
        config.ANTHROPIC_API_KEY = ""  # Empty key!

        # This should work for initialization
        with patch('rag_system.VectorStore'):
            with patch('rag_system.DocumentProcessor'):
                rag = RAGSystem(config)

        # Act & Assert - Query should fail with TypeError about authentication
        with pytest.raises(TypeError, match="Could not resolve authentication method"):
            rag.query("What is Python?")
    
    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    def test_ai_generator_exception_propagates(
        self, mock_doc_proc, mock_session, mock_ai_gen, mock_vector_store
    ):
        """Test that exceptions from AIGenerator propagate correctly"""
        from rag_system import RAGSystem
        
        # Arrange
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.side_effect = Exception("API Error")
        mock_ai_gen.return_value = mock_ai_instance
        
        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance
        
        config = MockConfig()
        rag = RAGSystem(config)
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            rag.query("Test query")
        
        assert "API Error" in str(exc_info.value)


class TestRAGSystemSessionManagement:
    """Tests for session and conversation history handling"""
    
    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    def test_query_gets_conversation_history_for_session(
        self, mock_doc_proc, mock_session, mock_ai_gen, mock_vector_store
    ):
        """Test that conversation history is retrieved for sessions"""
        from rag_system import RAGSystem
        
        # Arrange
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "Response"
        mock_ai_gen.return_value = mock_ai_instance
        
        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = "Previous chat"
        mock_session.return_value = mock_session_instance
        
        config = MockConfig()
        rag = RAGSystem(config)
        
        # Act
        rag.query("Follow-up question", session_id="session_123")
        
        # Assert
        mock_session_instance.get_conversation_history.assert_called_with("session_123")
        call_kwargs = mock_ai_instance.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] == "Previous chat"
    
    @patch('rag_system.VectorStore')
    @patch('rag_system.AIGenerator')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    def test_query_adds_exchange_to_session(
        self, mock_doc_proc, mock_session, mock_ai_gen, mock_vector_store
    ):
        """Test that query and response are added to session history"""
        from rag_system import RAGSystem
        
        # Arrange
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response.return_value = "The answer is 42."
        mock_ai_gen.return_value = mock_ai_instance
        
        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance
        
        config = MockConfig()
        rag = RAGSystem(config)
        
        # Act
        rag.query("What is the answer?", session_id="session_456")
        
        # Assert
        mock_session_instance.add_exchange.assert_called_once()
        call_args = mock_session_instance.add_exchange.call_args[0]
        assert call_args[0] == "session_456"
        assert "What is the answer?" in call_args[1]
        assert call_args[2] == "The answer is 42."


class TestRAGSystemIntegration:
    """Integration tests for the full query flow"""
    
    @patch('rag_system.VectorStore')
    @patch('rag_system.SessionManager')
    @patch('rag_system.DocumentProcessor')
    def test_full_query_flow_with_valid_api_key(
        self, mock_doc_proc, mock_session, mock_vector_store
    ):
        """
        Integration test: Full query flow with mocked external dependencies.
        This tests the actual AIGenerator with a mock API key scenario.
        """
        from rag_system import RAGSystem
        
        # Skip if no real API key (this is an integration test)
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key or api_key == "test-api-key":
            pytest.skip("Skipping integration test - no real API key")
        
        # Arrange
        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history.return_value = None
        mock_session.return_value = mock_session_instance
        
        config = MockConfig()
        config.ANTHROPIC_API_KEY = api_key
        
        rag = RAGSystem(config)
        
        # Act
        response, sources = rag.query("Hello")
        
        # Assert
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0


class TestConfigValidation:
    """Tests for configuration validation"""

    def test_config_raises_error_on_missing_api_key(self, monkeypatch):
        """Test that config validation catches missing API key at startup"""
        import importlib

        # Mock os.getenv to return empty string for API key
        original_getenv = os.getenv
        def mock_getenv(key, default=""):
            if key == "ANTHROPIC_API_KEY":
                return ""
            return original_getenv(key, default)

        # Remove cached config module
        if "config" in sys.modules:
            del sys.modules["config"]

        try:
            # Patch os.getenv before importing config
            monkeypatch.setattr(os, "getenv", mock_getenv)

            # Importing config should raise ValueError
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
                importlib.import_module("config")

        finally:
            # Clean up cached module
            if "config" in sys.modules:
                del sys.modules["config"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
