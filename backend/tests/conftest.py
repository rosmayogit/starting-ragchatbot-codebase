"""
Shared fixtures for RAG system tests
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


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


@pytest.fixture
def mock_config():
    """Provide mock configuration"""
    return MockConfig()


@pytest.fixture
def sample_course():
    """Provide a sample course for testing"""
    return Course(
        title="Test Course: Introduction to Testing",
        course_link="https://example.com/course",
        instructor="Test Instructor",
        lessons=[
            Lesson(lesson_number=0, title="Introduction", lesson_link="https://example.com/lesson0"),
            Lesson(lesson_number=1, title="Getting Started", lesson_link="https://example.com/lesson1"),
            Lesson(lesson_number=2, title="Advanced Topics", lesson_link="https://example.com/lesson2"),
        ]
    )


@pytest.fixture
def sample_chunks():
    """Provide sample course chunks for testing"""
    return [
        CourseChunk(
            content="This is the introduction to testing. Testing is important for software quality.",
            course_title="Test Course: Introduction to Testing",
            lesson_number=0,
            chunk_index=0
        ),
        CourseChunk(
            content="Getting started with unit tests. Unit tests verify individual components.",
            course_title="Test Course: Introduction to Testing",
            lesson_number=1,
            chunk_index=1
        ),
        CourseChunk(
            content="Advanced testing includes integration tests and end-to-end tests.",
            course_title="Test Course: Introduction to Testing",
            lesson_number=2,
            chunk_index=2
        ),
    ]


@pytest.fixture
def mock_search_results():
    """Provide mock search results"""
    return SearchResults(
        documents=[
            "This is content about MCP servers and how they work.",
            "MCP (Model Context Protocol) enables AI applications."
        ],
        metadata=[
            {"course_title": "MCP Course", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "MCP Course", "lesson_number": 2, "chunk_index": 1}
        ],
        distances=[0.1, 0.2]
    )


@pytest.fixture
def empty_search_results():
    """Provide empty search results"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[]
    )


@pytest.fixture
def error_search_results():
    """Provide error search results"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[],
        error="No course found matching 'NonexistentCourse'"
    )


@pytest.fixture
def mock_vector_store():
    """Provide a mock vector store"""
    mock = Mock()
    mock.search = Mock(return_value=SearchResults(
        documents=["Test content about testing."],
        metadata=[{"course_title": "Test Course", "lesson_number": 1, "chunk_index": 0}],
        distances=[0.1]
    ))
    mock.get_lesson_link = Mock(return_value="https://example.com/lesson1")
    mock.get_course_link = Mock(return_value="https://example.com/course")
    mock.get_course_count = Mock(return_value=1)
    mock.get_existing_course_titles = Mock(return_value=["Test Course"])
    return mock


@pytest.fixture
def mock_anthropic_response():
    """Provide a mock Anthropic API response (text only)"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"
    mock_content = Mock()
    mock_content.text = "This is a test response about the course content."
    mock_content.type = "text"
    mock_response.content = [mock_content]
    return mock_response


@pytest.fixture
def mock_anthropic_tool_response():
    """Provide a mock Anthropic API response with tool use"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    # Text block
    mock_text = Mock()
    mock_text.type = "text"
    mock_text.text = "Let me search for that information."

    # Tool use block
    mock_tool_use = Mock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.id = "tool_call_123"
    mock_tool_use.name = "search_course_content"
    mock_tool_use.input = {"query": "MCP servers", "course_name": None, "lesson_number": None}

    mock_response.content = [mock_text, mock_tool_use]
    return mock_response


@pytest.fixture
def mock_anthropic_final_response():
    """Provide a mock final response after tool execution"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"
    mock_content = Mock()
    mock_content.text = "Based on the course materials, MCP servers are used for..."
    mock_content.type = "text"
    mock_response.content = [mock_content]
    return mock_response
