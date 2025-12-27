"""Integration tests for indexing endpoints."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.indexing import router as indexing_router
from app.db.database import get_db
from app.rag.embeddings import HuggingFaceEmbeddingService
from app.rag.indexing import IndexingService


@pytest.fixture
def test_indexing_app(test_db_session, test_chroma_vector_store):
    """Create test FastAPI app for indexing endpoints."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.indexing import router as indexing_router
    from app.db.database import get_db

    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    # Create test indexing service with test vector store
    embedding_service = HuggingFaceEmbeddingService()
    test_indexing_service = IndexingService(
        vector_store=test_chroma_vector_store,
        embedding_service=embedding_service,
    )

    app = FastAPI()
    app.include_router(indexing_router)

    # Override get_db dependency
    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app), test_indexing_service


class TestIndexDatabaseDocuments:
    """Tests for POST /index/database endpoint."""

    def test_index_database_documents_basic(
        self, test_indexing_app, seeded_test_data, monkeypatch
    ):
        """Test basic database document indexing."""
        test_client, test_indexing_service = test_indexing_app

        # Patch IndexingService instantiation to use our test instance
        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        response = test_client.post("/index/database?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "indexed" in data
        assert "skipped" in data
        assert "errors" in data
        assert "total" in data
        assert data["indexed"] > 0

    @pytest.mark.parametrize(
        "filters,expected_min_indexed",
        [
            ({"limit": 5}, 1),
            ({"year": 2023, "limit": 5}, 1),
            ({"region": "Пловдив", "limit": 5}, 1),
            ({"status": "Действащо", "limit": 5}, 1),
            ({"region": "Пловдив", "year": 2023, "limit": 5}, 1),
        ],
    )
    def test_index_database_documents_with_filters(
        self, test_indexing_app, seeded_test_data, filters, expected_min_indexed, monkeypatch
    ):
        """Test indexing with various filter combinations."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Build query string
        query_params = "&".join([f"{k}={v}" for k, v in filters.items()])
        response = test_client.post(f"/index/database?{query_params}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["indexed"] >= expected_min_indexed

    def test_index_database_documents_verifies_count(
        self, test_indexing_app, seeded_test_data, monkeypatch
    ):
        """Test that indexed documents are actually stored in Chroma."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Index documents
        response = test_client.post("/index/database?limit=5")
        assert response.status_code == 200
        data = response.json()
        indexed_count = data["indexed"]

        # Verify count in Chroma
        stats_response = test_client.get("/index/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()

        assert stats_data["total_documents"] == indexed_count
        assert stats_data["source_distribution"].get("database") == indexed_count

    def test_index_database_documents_metadata_stored(
        self, test_indexing_app, seeded_test_data, monkeypatch
    ):
        """Test that metadata is correctly stored for database documents."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Index documents
        response = test_client.post("/index/database?limit=2")
        assert response.status_code == 200
        assert response.json()["indexed"] > 0

        # Get documents from Chroma to verify metadata
        collection = test_indexing_service.collection
        results = collection.get(limit=10)

        assert results.get("metadatas") is not None
        assert len(results["metadatas"]) > 0

        # Verify metadata structure
        for metadata in results["metadatas"]:
            assert metadata.get("source") == "database"
            assert "chitalishte_id" in metadata
            assert "year" in metadata
            assert "region" in metadata or metadata.get("region") is None

    def test_index_database_documents_idempotent(
        self, test_indexing_app, seeded_test_data, monkeypatch
    ):
        """Test that re-indexing the same documents doesn't create duplicates."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Index documents first time
        response1 = test_client.post("/index/database?limit=3")
        assert response1.status_code == 200
        first_indexed = response1.json()["indexed"]

        # Get count after first indexing
        stats1 = test_client.get("/index/stats").json()
        count_after_first = stats1["total_documents"]

        # Index same documents again
        response2 = test_client.post("/index/database?limit=3")
        assert response2.status_code == 200
        second_indexed = response2.json()["indexed"]

        # Get count after second indexing
        stats2 = test_client.get("/index/stats").json()
        count_after_second = stats2["total_documents"]

        # Count should be the same (idempotent - Chroma overwrites duplicates)
        assert count_after_second == count_after_first
        # Second indexing may report fewer if some were duplicates, but count should be same
        assert second_indexed <= first_indexed


class TestIndexAnalysisDocument:
    """Tests for POST /index/analysis-document endpoint."""

    def test_index_analysis_document_basic(
        self, test_indexing_app, monkeypatch
    ):
        """Test basic analysis document indexing."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        response = test_client.post(
            "/index/analysis-document",
            json={"document_name": "Chitalishta_demo_ver2.docx"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "indexed" in data
        assert data["indexed"] > 0

    def test_index_analysis_document_verifies_count(
        self, test_indexing_app, monkeypatch
    ):
        """Test that indexed chunks are actually stored in Chroma."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Index analysis document
        response = test_client.post(
            "/index/analysis-document",
            json={"document_name": "Chitalishta_demo_ver2.docx"},
        )
        assert response.status_code == 200
        data = response.json()
        indexed_count = data["indexed"]

        # Verify count in Chroma
        stats_response = test_client.get("/index/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()

        assert stats_data["total_documents"] == indexed_count
        assert (
            stats_data["source_distribution"].get("analysis_document") == indexed_count
        )

    def test_index_analysis_document_metadata_stored(
        self, test_indexing_app, monkeypatch
    ):
        """Test that metadata is correctly stored for analysis documents."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Index analysis document
        response = test_client.post(
            "/index/analysis-document",
            json={"document_name": "Chitalishta_demo_ver2.docx"},
        )
        assert response.status_code == 200
        assert response.json()["indexed"] > 0

        # Get documents from Chroma to verify metadata
        collection = test_indexing_service.collection
        results = collection.get(limit=10)

        assert results.get("metadatas") is not None
        assert len(results["metadatas"]) > 0

        # Verify metadata structure
        for metadata in results["metadatas"]:
            assert metadata.get("source") == "analysis_document"
            assert "document_name" in metadata
            assert "section_heading" in metadata
            assert "section_index" in metadata

    def test_index_analysis_document_idempotent(
        self, test_indexing_app, monkeypatch
    ):
        """Test that re-indexing the same document doesn't create duplicates."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Index document first time
        response1 = test_client.post(
            "/index/analysis-document",
            json={"document_name": "Chitalishta_demo_ver2.docx"},
        )
        assert response1.status_code == 200
        first_indexed = response1.json()["indexed"]

        # Get count after first indexing
        stats1 = test_client.get("/index/stats").json()
        count_after_first = stats1["total_documents"]

        # Index same document again
        response2 = test_client.post(
            "/index/analysis-document",
            json={"document_name": "Chitalishta_demo_ver2.docx"},
        )
        assert response2.status_code == 200
        second_indexed = response2.json()["indexed"]

        # Get count after second indexing
        stats2 = test_client.get("/index/stats").json()
        count_after_second = stats2["total_documents"]

        # Count should be the same (idempotent)
        assert count_after_second == count_after_first
        # Second indexing should report same number indexed
        assert second_indexed == first_indexed

    def test_index_analysis_document_not_found(
        self, test_indexing_app, monkeypatch
    ):
        """Test error handling for non-existent document."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        response = test_client.post(
            "/index/analysis-document",
            json={"document_name": "non_existent_document.docx"},
        )

        assert response.status_code == 200  # Endpoint returns 200 with error status
        data = response.json()

        assert data["status"] == "error"
        assert "not found" in data["message"].lower() or "file" in data["message"].lower()


class TestGetIndexStats:
    """Tests for GET /index/stats endpoint."""

    def test_get_index_stats_empty(self, test_indexing_app, monkeypatch):
        """Test stats endpoint when index is empty."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        response = test_client.get("/index/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["total_documents"] == 0
        assert data["source_distribution"] == {}

    def test_get_index_stats_with_database_documents(
        self, test_indexing_app, seeded_test_data, monkeypatch
    ):
        """Test stats endpoint after indexing database documents."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Index some documents
        index_response = test_client.post("/index/database?limit=3")
        assert index_response.status_code == 200
        indexed_count = index_response.json()["indexed"]

        # Get stats
        stats_response = test_client.get("/index/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()

        assert stats_data["status"] == "success"
        assert stats_data["total_documents"] == indexed_count
        assert stats_data["source_distribution"].get("database") == indexed_count

    def test_get_index_stats_with_analysis_documents(
        self, test_indexing_app, monkeypatch
    ):
        """Test stats endpoint after indexing analysis documents."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Index analysis document
        index_response = test_client.post(
            "/index/analysis-document",
            json={"document_name": "Chitalishta_demo_ver2.docx"},
        )
        assert index_response.status_code == 200
        indexed_count = index_response.json()["indexed"]

        # Get stats
        stats_response = test_client.get("/index/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()

        assert stats_data["status"] == "success"
        assert stats_data["total_documents"] == indexed_count
        assert (
            stats_data["source_distribution"].get("analysis_document") == indexed_count
        )

    def test_get_index_stats_source_distribution_accurate(
        self, test_indexing_app, seeded_test_data, monkeypatch
    ):
        """Test that source distribution accurately reflects both source types."""
        test_client, test_indexing_service = test_indexing_app

        monkeypatch.setattr(
            "app.api.indexing.IndexingService",
            lambda *args, **kwargs: test_indexing_service,
        )

        # Index database documents
        db_response = test_client.post("/index/database?limit=2")
        assert db_response.status_code == 200
        db_count = db_response.json()["indexed"]

        # Index analysis document
        analysis_response = test_client.post(
            "/index/analysis-document",
            json={"document_name": "Chitalishta_demo_ver2.docx"},
        )
        assert analysis_response.status_code == 200
        analysis_count = analysis_response.json()["indexed"]

        # Get stats
        stats_response = test_client.get("/index/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()

        # Verify total and distribution
        assert stats_data["total_documents"] == db_count + analysis_count
        assert stats_data["source_distribution"].get("database") == db_count
        assert (
            stats_data["source_distribution"].get("analysis_document") == analysis_count
        )

