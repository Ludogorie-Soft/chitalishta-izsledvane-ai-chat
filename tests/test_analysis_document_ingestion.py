"""Integration tests for /ingest/analysis-document endpoint."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ingestion import router as ingestion_router

# Default document name for tests
DEFAULT_DOCUMENT_NAME = "Chitalishta_demo_ver2.docx"


@pytest.fixture
def test_app():
    """Create test FastAPI app for analysis document endpoint."""
    app = FastAPI()
    app.include_router(ingestion_router)
    return TestClient(app)


class TestAnalysisDocumentIngestionBasic:
    """Basic functionality tests for analysis document ingestion endpoint."""

    def test_endpoint_returns_success(self, test_app: TestClient):
        """Test that endpoint returns success status when document exists."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "message" in data
        assert "chunks_created" in data
        assert "chunks" in data
        assert "statistics" in data

    def test_chunks_are_created(self, test_app: TestClient):
        """Test that chunks are created from the document."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["chunks_created"] > 0
        assert len(data["chunks"]) > 0
        assert len(data["chunks"]) == data["chunks_created"]

    def test_message_contains_chunk_count(self, test_app: TestClient):
        """Test that success message contains the chunk count."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        assert "successfully" in data["message"].lower()
        assert str(data["chunks_created"]) in data["message"]


class TestAnalysisDocumentIngestionResponseStructure:
    """Tests for response structure validation."""

    def test_response_schema(self, test_app: TestClient):
        """Test that response matches expected schema."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        # Check top-level structure
        assert "status" in data
        assert "message" in data
        assert "chunks_created" in data
        assert "chunks" in data
        assert "statistics" in data

        # Verify types
        assert isinstance(data["status"], str)
        assert isinstance(data["message"], str)
        assert isinstance(data["chunks_created"], int)
        assert isinstance(data["chunks"], list)
        assert isinstance(data["statistics"], dict)

    def test_chunk_structure(self, test_app: TestClient):
        """Test that each chunk has required fields."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        if data["chunks"]:
            chunk = data["chunks"][0]

            # Required fields
            assert "content" in chunk
            assert "metadata" in chunk
            assert "size_info" in chunk
            assert "is_valid" in chunk

            # Content should not be empty
            assert isinstance(chunk["content"], str)
            assert len(chunk["content"]) > 0

            # is_valid should be boolean
            assert isinstance(chunk["is_valid"], bool)

    def test_metadata_structure(self, test_app: TestClient):
        """Test that metadata has required fields for analysis documents."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        if data["chunks"]:
            metadata = data["chunks"][0]["metadata"]

            # Required metadata fields for analysis documents
            required_fields = [
                "source",
                "document_type",
                "document_name",
                "author",
                "document_date",
                "language",
                "scope",
                "version",
                "section_heading",
                "section_index",
            ]

            for field in required_fields:
                assert field in metadata, f"Missing required field: {field}"

            # Verify source is analysis_document
            assert metadata["source"] == "analysis_document"

            # chitalishte_id should be None for analysis documents
            assert metadata.get("chitalishte_id") is None

    def test_size_info_structure(self, test_app: TestClient):
        """Test that size_info has required fields."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        if data["chunks"]:
            size_info = data["chunks"][0]["size_info"]

            required_fields = ["characters", "words", "estimated_tokens"]

            for field in required_fields:
                assert field in size_info, f"Missing required field: {field}"
                assert isinstance(size_info[field], int)
                assert size_info[field] >= 0

    def test_statistics_structure(self, test_app: TestClient):
        """Test that statistics have required fields."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        stats = data["statistics"]

        required_fields = [
            "total_chunks",
            "valid_chunks",
            "invalid_chunks",
            "average_size",
            "min_size",
            "max_size",
        ]

        for field in required_fields:
            assert field in stats, f"Missing required field: {field}"
            assert isinstance(stats[field], int)
            assert stats[field] >= 0


class TestAnalysisDocumentIngestionMetadataValidation:
    """Tests for metadata correctness and validation."""

    def test_all_chunks_have_analysis_document_source(self, test_app: TestClient):
        """Test that all chunks have source set to 'analysis_document'."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        for chunk in data["chunks"]:
            assert chunk["metadata"]["source"] == "analysis_document"

    def test_all_chunks_have_document_metadata(self, test_app: TestClient):
        """Test that all chunks have document-specific metadata."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        expected_metadata = {
            "document_type": "main_analysis",
            "document_name": "Chitalishta_demo_ver2",  # Without .docx extension
            "author": "ИПИ",
            "document_date": "2025-12-09",
            "language": "bg",
            "scope": "national",
            "version": "v2",
        }

        for chunk in data["chunks"]:
            metadata = chunk["metadata"]
            for key, expected_value in expected_metadata.items():
                assert metadata[key] == expected_value, (
                    f"Chunk metadata '{key}' should be '{expected_value}', "
                    f"got '{metadata.get(key)}'"
                )

    def test_all_chunks_have_section_info(self, test_app: TestClient):
        """Test that all chunks have section heading and index."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        for chunk in data["chunks"]:
            metadata = chunk["metadata"]

            # Section heading should be present and non-empty
            assert "section_heading" in metadata
            assert isinstance(metadata["section_heading"], str)
            assert len(metadata["section_heading"]) > 0

            # Section index should be present and non-negative
            assert "section_index" in metadata
            assert isinstance(metadata["section_index"], int)
            assert metadata["section_index"] >= 0

    def test_chunks_have_no_database_fields(self, test_app: TestClient):
        """Test that chunks don't have database-specific fields set."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        database_fields = [
            "chitalishte_id",
            "chitalishte_name",
            "registration_number",
            "information_card_id",
        ]

        for chunk in data["chunks"]:
            metadata = chunk["metadata"]
            for field in database_fields:
                # These fields should be None or not present
                assert metadata.get(field) is None, (
                    f"Analysis document chunk should not have '{field}' set, "
                    f"got '{metadata.get(field)}'"
                )

    @pytest.mark.parametrize(
        "metadata_field,expected_type",
        [
            ("source", str),
            ("document_type", str),
            ("document_name", str),
            ("author", str),
            ("document_date", str),
            ("language", str),
            ("scope", str),
            ("version", str),
            ("section_heading", str),
            ("section_index", int),
        ],
    )
    def test_metadata_field_types(self, test_app: TestClient, metadata_field, expected_type):
        """Test that metadata fields have correct types."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        if data["chunks"]:
            metadata = data["chunks"][0]["metadata"]
            assert metadata_field in metadata
            assert isinstance(metadata[metadata_field], expected_type)


class TestAnalysisDocumentIngestionDataIntegrity:
    """Tests for data integrity and correctness."""

    def test_statistics_match_chunks(self, test_app: TestClient):
        """Test that statistics accurately reflect the chunk list."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        chunks = data["chunks"]
        stats = data["statistics"]

        # Total chunks should match
        assert stats["total_chunks"] == len(chunks)
        assert stats["total_chunks"] == data["chunks_created"]

        # Valid/invalid counts should match
        valid_count = sum(1 for chunk in chunks if chunk["is_valid"])
        invalid_count = sum(1 for chunk in chunks if not chunk["is_valid"])

        assert stats["valid_chunks"] == valid_count
        assert stats["invalid_chunks"] == invalid_count

        # Average size should be calculated correctly
        if chunks:
            sizes = [chunk["size_info"]["estimated_tokens"] for chunk in chunks]
            expected_avg = int(sum(sizes) / len(sizes))
            assert stats["average_size"] == expected_avg

            # Min and max should be correct
            assert stats["min_size"] == min(sizes)
            assert stats["max_size"] == max(sizes)

    def test_chunk_content_not_empty(self, test_app: TestClient):
        """Test that all chunks have non-empty content."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        for chunk in data["chunks"]:
            assert len(chunk["content"]) > 0, "Chunk content should not be empty"

    def test_chunk_size_info_consistency(self, test_app: TestClient):
        """Test that size_info fields are consistent with actual content."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        for chunk in data["chunks"]:
            content = chunk["content"]
            size_info = chunk["size_info"]

            # Characters should match content length
            assert size_info["characters"] == len(content)

            # Words should be approximately correct (at least 1 if content exists)
            if len(content) > 0:
                assert size_info["words"] > 0

            # Estimated tokens should be positive if content exists
            if len(content) > 0:
                assert size_info["estimated_tokens"] > 0

    def test_no_duplicate_chunks(self, test_app: TestClient):
        """Test that no duplicate chunks are returned."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        chunks = data["chunks"]

        # Check for duplicates by content
        seen_content = set()
        for chunk in chunks:
            content = chunk["content"]
            assert content not in seen_content, "Duplicate chunk content found"
            seen_content.add(content)


class TestAnalysisDocumentIngestionEdgeCases:
    """Tests for edge cases and error handling."""

    def test_endpoint_handles_missing_document(self, test_app: TestClient):
        """Test that endpoint handles missing document file gracefully."""
        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": "non_existent_document.docx"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "not found" in data["message"].lower() or "file" in data["message"].lower()
        assert data["chunks_created"] == 0
        assert len(data["chunks"]) == 0
        assert data["statistics"] == {}

    def test_endpoint_handles_processing_errors(self, test_app: TestClient, monkeypatch):
        """Test that endpoint handles processing errors gracefully."""
        from app.services import document_processor

        # Mock chunk_document to raise an exception
        original_chunk = document_processor.DocumentProcessor.chunk_document

        def mock_chunk_document(self):
            raise Exception("Test processing error")

        monkeypatch.setattr(
            document_processor.DocumentProcessor,
            "chunk_document",
            mock_chunk_document,
        )

        response = test_app.post(
            "/ingest/analysis-document",
            json={"document_name": DEFAULT_DOCUMENT_NAME},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "error" in data["message"].lower()
        assert data["chunks_created"] == 0
        assert len(data["chunks"]) == 0
        assert data["statistics"] == {}
