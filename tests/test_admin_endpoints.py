"""Integration tests for admin API endpoints."""

import uuid
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.admin import router as admin_router
from app.db.database import get_db
from app.db.models import ChatLog


@pytest.fixture
def test_admin_app(test_db_session: Session):
    """Create test FastAPI app with admin router and overridden database dependency."""
    app = FastAPI()
    app.include_router(admin_router)

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass  # Session cleanup handled by fixture

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def sample_chat_logs(test_db_session: Session):
    """Create sample chat logs for testing."""
    now = datetime.now()
    conv_id_1 = str(uuid.uuid4())
    conv_id_2 = str(uuid.uuid4())
    conv_id_3 = str(uuid.uuid4())

    # Conversation 1: SQL query with 2 messages, no errors
    log1_1 = ChatLog(
        request_id=str(uuid.uuid4()),
        conversation_id=conv_id_1,
        request_timestamp=now - timedelta(hours=2),
        user_message="Колко читалища има в Пловдив?",
        answer="В Пловдив има 45 читалища.",
        intent="sql",
        routing_confidence=0.95,
        sql_executed=True,
        rag_executed=False,
        sql_query="SELECT COUNT(*) FROM chitalishte WHERE town = 'Пловдив'",
        response_time_ms=250,
        total_input_tokens=100,
        total_output_tokens=50,
        total_tokens=150,
        cost_usd=0.0005,
        llm_model="gpt-4o-mini",
        error_occurred=False,
        hallucination_mode="medium",
    )

    log1_2 = ChatLog(
        request_id=str(uuid.uuid4()),
        conversation_id=conv_id_1,
        request_timestamp=now - timedelta(hours=1),
        user_message="А в София?",
        answer="В София има 120 читалища.",
        intent="sql",
        routing_confidence=0.92,
        sql_executed=True,
        rag_executed=False,
        sql_query="SELECT COUNT(*) FROM chitalishte WHERE town = 'София'",
        response_time_ms=200,
        total_input_tokens=80,
        total_output_tokens=40,
        total_tokens=120,
        cost_usd=0.0004,
        llm_model="gpt-4o-mini",
        error_occurred=False,
        hallucination_mode="medium",
    )

    # Conversation 2: RAG query with 1 message, no errors
    log2_1 = ChatLog(
        request_id=str(uuid.uuid4()),
        conversation_id=conv_id_2,
        request_timestamp=now - timedelta(hours=3),
        user_message="Как се финансират читалищата?",
        answer="Читалищата се финансират от държавата и общините.",
        intent="rag",
        routing_confidence=0.88,
        sql_executed=False,
        rag_executed=True,
        response_time_ms=500,
        total_input_tokens=150,
        total_output_tokens=80,
        total_tokens=230,
        cost_usd=0.001,
        llm_model="gpt-4o-mini",
        error_occurred=False,
        hallucination_mode="low",
    )

    # Conversation 3: Hybrid query with 1 message, has error
    log3_1 = ChatLog(
        request_id=str(uuid.uuid4()),
        conversation_id=conv_id_3,
        request_timestamp=now - timedelta(hours=4),
        user_message="Колко читалища има и разкажи за тях?",
        answer=None,  # Error occurred
        intent="hybrid",
        routing_confidence=0.75,
        sql_executed=True,
        rag_executed=True,
        sql_query="SELECT COUNT(*) FROM chitalishte",
        response_time_ms=1000,
        total_input_tokens=200,
        total_output_tokens=0,
        total_tokens=200,
        cost_usd=0.0015,
        llm_model="gpt-4o",
        error_occurred=True,
        error_type="TimeoutError",
        error_message="Request timeout",
        http_status_code=500,
        hallucination_mode="high",
    )

    test_db_session.add_all([log1_1, log1_2, log2_1, log3_1])
    test_db_session.commit()

    return {
        "conversation_ids": [conv_id_1, conv_id_2, conv_id_3],
        "conv_id_1": conv_id_1,
        "conv_id_2": conv_id_2,
        "conv_id_3": conv_id_3,
    }


class TestAdminListConversations:
    """Tests for GET /admin/chat endpoint."""

    def test_list_conversations_basic(self, test_admin_app, sample_chat_logs):
        """Test basic listing of conversations."""
        response = test_admin_app.get("/admin/chat")

        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

        # Should have 3 conversations
        assert data["total"] == 3
        assert len(data["conversations"]) == 3

        # Check first conversation (most recent)
        conv = data["conversations"][0]
        assert "conversation_id" in conv
        assert "first_message" in conv
        assert "last_message_timestamp" in conv
        assert "message_count" in conv
        assert "total_cost_usd" in conv
        assert "intents_used" in conv
        assert "has_errors" in conv

    def test_list_conversations_pagination(self, test_admin_app, sample_chat_logs):
        """Test pagination."""
        # First page
        response1 = test_admin_app.get("/admin/chat?limit=2&offset=0")
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["conversations"]) == 2
        assert data1["total"] == 3
        assert data1["limit"] == 2
        assert data1["offset"] == 0

        # Second page
        response2 = test_admin_app.get("/admin/chat?limit=2&offset=2")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["conversations"]) == 1
        assert data2["total"] == 3
        assert data2["limit"] == 2
        assert data2["offset"] == 2

    def test_list_conversations_filter_by_intent(self, test_admin_app, sample_chat_logs):
        """Test filtering by intent."""
        # Filter by SQL intent
        response = test_admin_app.get("/admin/chat?intent=sql")
        assert response.status_code == 200
        data = response.json()
        # Should have 1 conversation with SQL intent (conv_id_1)
        assert data["total"] == 1
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["intents_used"] == ["sql"]

        # Filter by RAG intent
        response = test_admin_app.get("/admin/chat?intent=rag")
        assert response.status_code == 200
        data = response.json()
        # Should have 1 conversation with RAG intent (conv_id_2)
        assert data["total"] == 1
        assert "rag" in data["conversations"][0]["intents_used"]

    def test_list_conversations_filter_by_has_errors(self, test_admin_app, sample_chat_logs):
        """Test filtering by error status."""
        # Filter conversations with errors
        response = test_admin_app.get("/admin/chat?has_errors=true")
        assert response.status_code == 200
        data = response.json()
        # Should have 1 conversation with errors (conv_id_3)
        assert data["total"] == 1
        assert data["conversations"][0]["has_errors"] is True

        # Filter conversations without errors
        response = test_admin_app.get("/admin/chat?has_errors=false")
        assert response.status_code == 200
        data = response.json()
        # Should have 2 conversations without errors
        assert data["total"] == 2
        assert all(not conv["has_errors"] for conv in data["conversations"])

    def test_list_conversations_filter_by_date_range(self, test_admin_app, sample_chat_logs):
        """Test filtering by date range."""
        now = datetime.now()
        start_date = (now - timedelta(hours=2, minutes=30)).isoformat()
        end_date = (now - timedelta(minutes=30)).isoformat()

        response = test_admin_app.get(
            f"/admin/chat?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200
        data = response.json()
        # Should have 1 conversation (conv_id_1) within the date range
        assert data["total"] == 1

    def test_list_conversations_aggregation(self, test_admin_app, sample_chat_logs):
        """Test that conversation aggregation works correctly."""
        response = test_admin_app.get("/admin/chat")
        assert response.status_code == 200
        data = response.json()

        # Find conversation with 2 messages (conv_id_1)
        conv_with_2_messages = next(
            (c for c in data["conversations"] if c["message_count"] == 2), None
        )
        assert conv_with_2_messages is not None
        assert conv_with_2_messages["message_count"] == 2
        # Total cost should be sum of both messages
        assert conv_with_2_messages["total_cost_usd"] == pytest.approx(0.0009, abs=0.0001)
        assert conv_with_2_messages["intents_used"] == ["sql"]
        assert conv_with_2_messages["has_errors"] is False

        # Find conversation with error (conv_id_3)
        conv_with_error = next(
            (c for c in data["conversations"] if c["has_errors"]), None
        )
        assert conv_with_error is not None
        assert conv_with_error["has_errors"] is True
        assert "hybrid" in conv_with_error["intents_used"]

    def test_list_conversations_empty_result(self, test_admin_app):
        """Test listing conversations when there are none."""
        response = test_admin_app.get("/admin/chat")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["conversations"]) == 0

    def test_list_conversations_sorted_by_timestamp(self, test_admin_app, sample_chat_logs):
        """Test that conversations are sorted by last_message_timestamp (most recent first)."""
        response = test_admin_app.get("/admin/chat")
        assert response.status_code == 200
        data = response.json()

        # Check that conversations are sorted by last_message_timestamp descending
        timestamps = [
            datetime.fromisoformat(conv["last_message_timestamp"].replace("Z", "+00:00"))
            for conv in data["conversations"]
        ]
        assert timestamps == sorted(timestamps, reverse=True)


class TestAdminConversationDetails:
    """Tests for GET /admin/chat/{conversation_id} endpoint."""

    def test_get_conversation_details_success(self, test_admin_app, sample_chat_logs):
        """Test getting conversation details for existing conversation."""
        conv_id = sample_chat_logs["conv_id_1"]
        response = test_admin_app.get(f"/admin/chat/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conv_id
        assert "chat_logs" in data
        assert "total_messages" in data

        # Should have 2 messages
        assert data["total_messages"] == 2
        assert len(data["chat_logs"]) == 2

        # Check first message (chronological order)
        first_log = data["chat_logs"][0]
        assert first_log["user_message"] == "Колко читалища има в Пловдив?"
        assert first_log["intent"] == "sql"
        assert first_log["sql_executed"] is True
        assert first_log["rag_executed"] is False
        assert first_log["sql_query"] is not None
        assert first_log["error_occurred"] is False

        # Check second message
        second_log = data["chat_logs"][1]
        assert second_log["user_message"] == "А в София?"
        assert second_log["intent"] == "sql"

    def test_get_conversation_details_ordered_chronologically(
        self, test_admin_app, sample_chat_logs
    ):
        """Test that chat logs are ordered chronologically."""
        conv_id = sample_chat_logs["conv_id_1"]
        response = test_admin_app.get(f"/admin/chat/{conv_id}")

        assert response.status_code == 200
        data = response.json()

        # Check that timestamps are in ascending order
        timestamps = [
            datetime.fromisoformat(log["request_timestamp"].replace("Z", "+00:00"))
            for log in data["chat_logs"]
        ]
        assert timestamps == sorted(timestamps)

    def test_get_conversation_details_includes_all_fields(
        self, test_admin_app, sample_chat_logs
    ):
        """Test that all expected fields are included in the response."""
        conv_id = sample_chat_logs["conv_id_1"]
        response = test_admin_app.get(f"/admin/chat/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        log = data["chat_logs"][0]

        # Check all expected fields
        assert "id" in log
        assert "request_id" in log
        assert "request_timestamp" in log
        assert "user_message" in log
        assert "answer" in log
        assert "intent" in log
        assert "routing_confidence" in log
        assert "sql_executed" in log
        assert "rag_executed" in log
        assert "sql_query" in log
        assert "response_time_ms" in log
        assert "total_input_tokens" in log
        assert "total_output_tokens" in log
        assert "total_tokens" in log
        assert "cost_usd" in log
        assert "llm_model" in log
        assert "llm_operations" in log
        assert "response_metadata" in log
        assert "structured_output" in log
        assert "error_occurred" in log
        assert "error_type" in log
        assert "error_message" in log
        assert "http_status_code" in log
        assert "client_ip" in log
        assert "user_agent" in log

    def test_get_conversation_details_with_error(self, test_admin_app, sample_chat_logs):
        """Test getting conversation details for conversation with error."""
        conv_id = sample_chat_logs["conv_id_3"]
        response = test_admin_app.get(f"/admin/chat/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        log = data["chat_logs"][0]

        assert log["error_occurred"] is True
        assert log["error_type"] == "TimeoutError"
        assert log["error_message"] == "Request timeout"
        assert log["http_status_code"] == 500

    def test_get_conversation_details_not_found(self, test_admin_app):
        """Test getting conversation details for non-existent conversation."""
        non_existent_id = str(uuid.uuid4())
        response = test_admin_app.get(f"/admin/chat/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert non_existent_id in data["detail"]

    def test_get_conversation_details_single_message(self, test_admin_app, sample_chat_logs):
        """Test getting conversation details for conversation with single message."""
        conv_id = sample_chat_logs["conv_id_2"]
        response = test_admin_app.get(f"/admin/chat/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 1
        assert len(data["chat_logs"]) == 1
        assert data["chat_logs"][0]["intent"] == "rag"
        assert data["chat_logs"][0]["rag_executed"] is True
        assert data["chat_logs"][0]["sql_executed"] is False

