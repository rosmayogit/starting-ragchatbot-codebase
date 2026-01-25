"""
Tests for CourseSearchTool.execute() method in search_tools.py

These tests evaluate:
1. Output format of execute() with valid search results
2. Handling of empty results
3. Course and lesson filtering
4. Source tracking (last_sources population)
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, MagicMock
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Tests for CourseSearchTool.execute() method"""
    
    def setup_method(self):
        """Set up mock vector store for each test"""
        self.mock_store = Mock()
        self.tool = CourseSearchTool(self.mock_store)
    
    def test_execute_returns_formatted_results_on_success(self):
        """Test that execute returns properly formatted results when content is found"""
        # Arrange: Mock successful search results
        mock_results = SearchResults(
            documents=["This is lesson content about Python basics."],
            metadata=[{"course_title": "Python 101", "lesson_number": 1}],
            distances=[0.5],
            error=None
        )
        self.mock_store.search.return_value = mock_results
        self.mock_store.get_lesson_link.return_value = "https://example.com/lesson1"
        
        # Act
        result = self.tool.execute(query="Python basics")
        
        # Assert
        assert "[Python 101 - Lesson 1]" in result
        assert "This is lesson content about Python basics." in result
        self.mock_store.search.assert_called_once_with(
            query="Python basics",
            course_name=None,
            lesson_number=None
        )
    
    def test_execute_returns_error_message_on_empty_results(self):
        """Test that execute returns appropriate message when no results found"""
        # Arrange: Mock empty results
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_store.search.return_value = mock_results
        
        # Act
        result = self.tool.execute(query="nonexistent topic")
        
        # Assert
        assert "No relevant content found" in result
    
    def test_execute_handles_search_error(self):
        """Test that execute properly returns error messages from vector store"""
        # Arrange: Mock error result
        mock_results = SearchResults.empty("Search error: Connection failed")
        self.mock_store.search.return_value = mock_results
        
        # Act
        result = self.tool.execute(query="any query")
        
        # Assert
        assert "Search error" in result
    
    def test_execute_passes_course_filter(self):
        """Test that course_name filter is passed to vector store"""
        # Arrange
        mock_results = SearchResults(documents=[], metadata=[], distances=[])
        self.mock_store.search.return_value = mock_results
        
        # Act
        self.tool.execute(query="test", course_name="Python 101")
        
        # Assert
        self.mock_store.search.assert_called_once_with(
            query="test",
            course_name="Python 101",
            lesson_number=None
        )
    
    def test_execute_passes_lesson_filter(self):
        """Test that lesson_number filter is passed to vector store"""
        # Arrange
        mock_results = SearchResults(documents=[], metadata=[], distances=[])
        self.mock_store.search.return_value = mock_results
        
        # Act
        self.tool.execute(query="test", lesson_number=3)
        
        # Assert
        self.mock_store.search.assert_called_once_with(
            query="test",
            course_name=None,
            lesson_number=3
        )
    
    def test_execute_populates_last_sources(self):
        """Test that execute correctly populates last_sources for UI"""
        # Arrange
        mock_results = SearchResults(
            documents=["Content 1", "Content 2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2}
            ],
            distances=[0.3, 0.5]
        )
        self.mock_store.search.return_value = mock_results
        self.mock_store.get_lesson_link.side_effect = [
            "https://example.com/a/1",
            "https://example.com/b/2"
        ]
        
        # Act
        self.tool.execute(query="test")
        
        # Assert
        assert len(self.tool.last_sources) == 2
        assert self.tool.last_sources[0]["text"] == "Course A - Lesson 1"
        assert self.tool.last_sources[0]["link"] == "https://example.com/a/1"
        assert self.tool.last_sources[1]["text"] == "Course B - Lesson 2"
    
    def test_execute_handles_missing_lesson_number(self):
        """Test handling of results without lesson numbers"""
        # Arrange
        mock_results = SearchResults(
            documents=["Course overview content"],
            metadata=[{"course_title": "Python 101", "lesson_number": None}],
            distances=[0.4]
        )
        self.mock_store.search.return_value = mock_results
        
        # Act
        result = self.tool.execute(query="overview")
        
        # Assert
        assert "[Python 101]" in result
        assert "Lesson" not in result.split("]")[0]  # No lesson in header


class TestToolManager:
    """Tests for ToolManager functionality"""
    
    def test_tool_registration(self):
        """Test that tools can be registered and retrieved"""
        manager = ToolManager()
        mock_store = Mock()
        tool = CourseSearchTool(mock_store)
        
        manager.register_tool(tool)
        
        definitions = manager.get_tool_definitions()
        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"
    
    def test_execute_tool_calls_correct_tool(self):
        """Test that execute_tool routes to the correct tool"""
        manager = ToolManager()
        mock_store = Mock()
        mock_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_store.search.return_value = mock_results
        
        tool = CourseSearchTool(mock_store)
        manager.register_tool(tool)
        
        result = manager.execute_tool("search_course_content", query="test")
        
        assert "No relevant content found" in result
    
    def test_execute_tool_unknown_tool(self):
        """Test handling of unknown tool names"""
        manager = ToolManager()
        
        result = manager.execute_tool("nonexistent_tool", query="test")
        
        assert "not found" in result
    
    def test_get_last_sources(self):
        """Test retrieval of sources from tools"""
        manager = ToolManager()
        mock_store = Mock()
        mock_results = SearchResults(
            documents=["content"],
            metadata=[{"course_title": "Test", "lesson_number": 1}],
            distances=[0.5]
        )
        mock_store.search.return_value = mock_results
        mock_store.get_lesson_link.return_value = None
        
        tool = CourseSearchTool(mock_store)
        manager.register_tool(tool)
        manager.execute_tool("search_course_content", query="test")
        
        sources = manager.get_last_sources()
        assert len(sources) == 1
        assert sources[0]["text"] == "Test - Lesson 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
