"""Tests for chat API endpoint."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.rag.chat_memory import get_chat_memory
from app.rag.hallucination_control import HallucinationMode

client = TestClient(app)


class TestChatEndpoint:
    """Tests for chat endpoint."""

    def setup_method(self):
        """Clear chat memory before each test."""
        memory = get_chat_memory()
        # Clear all conversations
        for conv_id in list(memory._conversations.keys()):
            memory.delete_conversation(conv_id)

    @patch("app.api.chat.get_hybrid_pipeline_service")
    def test_chat_endpoint_basic(self, mock_get_pipeline):
        """Test basic chat endpoint functionality."""
        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.query = MagicMock(
            return_value={
                "answer": "Тестов отговор",
                "intent": "rag",
                "routing_confidence": 0.9,
                "routing_explanation": "RAG intent detected",
                "sql_executed": False,
                "rag_executed": True,
                "rag_metadata": {},
            }
        )
        mock_get_pipeline.return_value = mock_pipeline

        # Make request
        response = client.post(
            "/chat/",
            json={
                "message": "Какво е читалище?",
                "mode": "medium",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "conversation_id" in data
        assert data["intent"] == "rag"
        assert data["mode"] == "medium"
        assert data["sql_executed"] is False
        assert data["rag_executed"] is True

    @patch("app.api.chat.get_hybrid_pipeline_service")
    def test_chat_endpoint_with_conversation_id(self, mock_get_pipeline):
        """Test chat endpoint with existing conversation ID."""
        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.query = MagicMock(
            return_value={
                "answer": "Отговор",
                "intent": "rag",
                "routing_confidence": 0.8,
                "routing_explanation": "Test",
                "sql_executed": False,
                "rag_executed": True,
            }
        )
        mock_get_pipeline.return_value = mock_pipeline

        # Create a conversation first
        memory = get_chat_memory()
        conv_id = memory.create_conversation()

        # Make request with conversation ID
        response = client.post(
            "/chat/",
            json={
                "message": "Въпрос",
                "conversation_id": conv_id,
                "mode": "medium",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conv_id

    @patch("app.api.chat.get_hybrid_pipeline_service")
    def test_chat_endpoint_different_modes(self, mock_get_pipeline):
        """Test chat endpoint with different hallucination modes."""
        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.query = MagicMock(
            return_value={
                "answer": "Отговор",
                "intent": "rag",
                "routing_confidence": 0.8,
                "routing_explanation": "Test",
                "sql_executed": False,
                "rag_executed": True,
            }
        )
        mock_get_pipeline.return_value = mock_pipeline

        # Test low tolerance mode
        response = client.post(
            "/chat/",
            json={
                "message": "Въпрос",
                "mode": "low",
            },
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "low"

        # Test high tolerance mode
        response = client.post(
            "/chat/",
            json={
                "message": "Въпрос",
                "mode": "high",
            },
        )
        assert response.status_code == 200
        assert response.json()["mode"] == "high"

    @patch("app.api.chat.get_hybrid_pipeline_service")
    def test_chat_endpoint_hybrid_query(self, mock_get_pipeline):
        """Test chat endpoint with hybrid query (SQL + RAG)."""
        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.query = MagicMock(
            return_value={
                "answer": "Комбиниран отговор",
                "intent": "hybrid",
                "routing_confidence": 0.85,
                "routing_explanation": "Hybrid intent",
                "sql_executed": True,
                "rag_executed": True,
                "sql_query": "SELECT COUNT(*) FROM chitalishte",
            }
        )
        mock_get_pipeline.return_value = mock_pipeline

        response = client.post(
            "/chat/",
            json={
                "message": "Колко читалища има и разкажи за тях?",
                "mode": "medium",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "hybrid"
        assert data["sql_executed"] is True
        assert data["rag_executed"] is True

    def test_chat_endpoint_invalid_request(self):
        """Test chat endpoint with invalid request."""
        response = client.post(
            "/chat/",
            json={},  # Missing required 'message' field
        )

        assert response.status_code == 422  # Validation error

    @patch("app.api.chat.get_hybrid_pipeline_service")
    def test_chat_history_management(self, mock_get_pipeline):
        """Test that chat history is maintained across messages."""
        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.query = MagicMock(
            return_value={
                "answer": "Отговор",
                "intent": "rag",
                "routing_confidence": 0.8,
                "routing_explanation": "Test",
                "sql_executed": False,
                "rag_executed": True,
            }
        )
        mock_get_pipeline.return_value = mock_pipeline

        # Send first message
        response1 = client.post(
            "/chat/",
            json={
                "message": "Първи въпрос",
                "mode": "medium",
            },
        )
        assert response1.status_code == 200
        conv_id = response1.json()["conversation_id"]

        # Send second message in same conversation
        response2 = client.post(
            "/chat/",
            json={
                "message": "Втори въпрос",
                "conversation_id": conv_id,
                "mode": "medium",
            },
        )
        assert response2.status_code == 200
        assert response2.json()["conversation_id"] == conv_id

        # Get history
        history_response = client.post(
            "/chat/history",
            json={"conversation_id": conv_id},
        )
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history["messages"]) == 4  # 2 user + 2 assistant messages

    def test_get_chat_history_not_found(self):
        """Test getting chat history for non-existent conversation."""
        response = client.post(
            "/chat/history",
            json={"conversation_id": "non-existent-id"},
        )

        assert response.status_code == 404

    def test_delete_chat_history(self):
        """Test deleting chat history."""
        # Create a conversation
        memory = get_chat_memory()
        conv_id = memory.create_conversation()
        memory.add_message(conv_id, "user", "Test message")

        # Delete it
        response = client.delete(f"/chat/history/{conv_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify it's deleted
        history_response = client.post(
            "/chat/history",
            json={"conversation_id": conv_id},
        )
        assert history_response.status_code == 404

    def test_delete_chat_history_not_found(self):
        """Test deleting non-existent chat history."""
        response = client.delete("/chat/history/non-existent-id")

        assert response.status_code == 404



