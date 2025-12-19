"""Integration tests for /ingest/preview endpoint."""
import pytest
from fastapi.testclient import TestClient


class TestIngestionPreviewBasic:
    """Basic functionality tests for preview endpoint."""

    @pytest.mark.parametrize(
        "request_body,expected_min_docs",
        [
            ({"limit": 5}, 1),  # No filters
            ({"year": 2023, "limit": 5}, 1),  # Year filter
            ({"region": "Пловдив", "limit": 5}, 1),  # Region filter
            ({"status": "Действащо", "limit": 5}, 1),  # Status filter
            ({"region": "Пловдив", "year": 2023, "limit": 5}, 1),  # Combined filters
        ],
    )
    def test_preview_with_filters(
        self, test_app: TestClient, seeded_test_data, request_body, expected_min_docs
    ):
        """Test preview endpoint with various filter combinations."""
        response = test_app.post("/ingest/preview", json=request_body)

        assert response.status_code == 200
        data = response.json()

        assert "documents" in data
        assert "statistics" in data
        assert len(data["documents"]) >= expected_min_docs

    def test_preview_default_limit(self, test_app: TestClient, seeded_test_data):
        """Test that default limit is applied when not specified."""
        response = test_app.post("/ingest/preview", json={})

        assert response.status_code == 200
        data = response.json()

        assert len(data["documents"]) <= 10  # Default limit

    @pytest.mark.parametrize(
        "limit,expected_max",
        [
            (1, 1),
            (5, 5),
            (10, 10),
            (100, 100),  # Max limit
            (200, 100),  # Should be capped at 100
        ],
    )
    def test_preview_limit_enforcement(
        self, test_app: TestClient, seeded_test_data, limit, expected_max
    ):
        """Test that limit parameter is respected and capped at 100."""
        response = test_app.post("/ingest/preview", json={"limit": limit})

        assert response.status_code == 200
        data = response.json()

        assert len(data["documents"]) <= expected_max


class TestIngestionPreviewResponseStructure:
    """Tests for response structure validation."""

    def test_response_schema(self, test_app: TestClient, seeded_test_data):
        """Test that response matches expected schema."""
        response = test_app.post("/ingest/preview", json={"limit": 2})

        assert response.status_code == 200
        data = response.json()

        # Check top-level structure
        assert "documents" in data
        assert "statistics" in data
        assert isinstance(data["documents"], list)
        assert isinstance(data["statistics"], dict)

    def test_document_structure(self, test_app: TestClient, seeded_test_data):
        """Test that each document has required fields."""
        response = test_app.post("/ingest/preview", json={"limit": 1})

        assert response.status_code == 200
        data = response.json()

        if data["documents"]:
            doc = data["documents"][0]

            # Required fields
            assert "content" in doc
            assert "metadata" in doc
            assert "size_info" in doc
            assert "is_valid" in doc

            # Content should not be empty
            assert isinstance(doc["content"], str)
            assert len(doc["content"]) > 0

            # is_valid should be boolean
            assert isinstance(doc["is_valid"], bool)

    def test_metadata_structure(self, test_app: TestClient, seeded_test_data):
        """Test that metadata has required fields."""
        response = test_app.post("/ingest/preview", json={"limit": 1})

        assert response.status_code == 200
        data = response.json()

        if data["documents"]:
            metadata = data["documents"][0]["metadata"]

            # Required metadata fields
            required_fields = [
                "source",
                "chitalishte_id",
                "region",
                "year",
                "counts",
            ]

            for field in required_fields:
                assert field in metadata, f"Missing required field: {field}"

            # Verify types
            assert metadata["source"] == "database"
            assert isinstance(metadata["chitalishte_id"], int)
            assert isinstance(metadata["counts"], dict)

    def test_size_info_structure(self, test_app: TestClient, seeded_test_data):
        """Test that size_info has required fields."""
        response = test_app.post("/ingest/preview", json={"limit": 1})

        assert response.status_code == 200
        data = response.json()

        if data["documents"]:
            size_info = data["documents"][0]["size_info"]

            required_fields = ["characters", "words", "estimated_tokens"]

            for field in required_fields:
                assert field in size_info, f"Missing required field: {field}"
                assert isinstance(size_info[field], int)
                assert size_info[field] >= 0

    def test_statistics_structure(self, test_app: TestClient, seeded_test_data):
        """Test that statistics have required fields."""
        response = test_app.post("/ingest/preview", json={"limit": 5})

        assert response.status_code == 200
        data = response.json()

        stats = data["statistics"]

        required_fields = [
            "total_documents",
            "valid_documents",
            "invalid_documents",
            "average_size",
            "min_size",
            "max_size",
        ]

        for field in required_fields:
            assert field in stats, f"Missing required field: {field}"
            assert isinstance(stats[field], int)


class TestIngestionPreviewDataIntegrity:
    """Tests for data integrity and correctness."""

    def test_no_duplicate_documents(self, test_app: TestClient, seeded_test_data):
        """Test that no duplicate documents are returned."""
        response = test_app.post("/ingest/preview", json={"limit": 10})

        assert response.status_code == 200
        data = response.json()

        documents = data["documents"]

        # Check for duplicates (same chitalishte_id + year combination)
        seen = set()
        for doc in documents:
            key = (
                doc["metadata"]["chitalishte_id"],
                doc["metadata"]["year"],
            )
            assert key not in seen, f"Duplicate document found: {key}"
            seen.add(key)

    @pytest.mark.parametrize(
        "filter_key,filter_value",
        [
            ("region", "Пловдив"),
            ("region", "София"),
            ("status", "Действащо"),
            ("status", "Закрито"),
            ("year", 2023),
            ("year", 2022),
        ],
    )
    def test_filters_match_results(
        self, test_app: TestClient, seeded_test_data, filter_key, filter_value
    ):
        """Test that returned documents match applied filters."""
        response = test_app.post(
            "/ingest/preview", json={filter_key: filter_value, "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()

        for doc in data["documents"]:
            if filter_key == "year":
                assert doc["metadata"]["year"] == filter_value
            elif filter_key == "region":
                assert doc["metadata"]["region"] == filter_value
            elif filter_key == "status":
                assert doc["metadata"]["status"] == filter_value

    def test_one_document_per_chitalishte_per_year(
        self, test_app: TestClient, seeded_test_data
    ):
        """Test that exactly one document exists per Chitalishte per year."""
        response = test_app.post("/ingest/preview", json={"limit": 10})

        assert response.status_code == 200
        data = response.json()

        # Group by chitalishte_id and year
        grouped = {}
        for doc in data["documents"]:
            key = (doc["metadata"]["chitalishte_id"], doc["metadata"]["year"])
            grouped[key] = grouped.get(key, 0) + 1

        # Each combination should appear exactly once
        for key, count in grouped.items():
            assert count == 1, f"Found {count} documents for {key}, expected 1"

    def test_statistics_match_documents(self, test_app: TestClient, seeded_test_data):
        """Test that statistics accurately reflect the document list."""
        response = test_app.post("/ingest/preview", json={"limit": 10})

        assert response.status_code == 200
        data = response.json()

        documents = data["documents"]
        stats = data["statistics"]

        # Total documents should match
        assert stats["total_documents"] == len(documents)

        # Valid/invalid counts should match
        valid_count = sum(1 for doc in documents if doc["is_valid"])
        invalid_count = sum(1 for doc in documents if not doc["is_valid"])

        assert stats["valid_documents"] == valid_count
        assert stats["invalid_documents"] == invalid_count

        # Average size should be calculated correctly
        if documents:
            sizes = [doc["size_info"]["estimated_tokens"] for doc in documents]
            expected_avg = int(sum(sizes) / len(sizes))
            assert stats["average_size"] == expected_avg

            # Min and max should be correct
            assert stats["min_size"] == min(sizes)
            assert stats["max_size"] == max(sizes)

    def test_content_contains_bulgarian_text(
        self, test_app: TestClient, seeded_test_data
    ):
        """Test that document content contains Bulgarian text."""
        response = test_app.post("/ingest/preview", json={"limit": 1})

        assert response.status_code == 200
        data = response.json()

        if data["documents"]:
            content = data["documents"][0]["content"]

            # Check for Bulgarian text indicators
            bulgarian_indicators = ["Читалище", "област", "член", "година", "регион"]
            has_bulgarian = any(indicator in content for indicator in bulgarian_indicators)

            assert has_bulgarian, "Content should contain Bulgarian text"


class TestIngestionPreviewEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.parametrize(
        "request_body",
        [
            {"region": "NonExistentRegion", "limit": 5},
            {"year": 2099, "limit": 5},  # Future year
            {"year": 1900, "limit": 5},  # Very old year
            {"region": "Пловдив", "year": 2099, "limit": 5},  # No matching data
        ],
    )
    def test_filters_with_no_results(
        self, test_app: TestClient, seeded_test_data, request_body
    ):
        """Test that filters with no matching data return empty results gracefully."""
        response = test_app.post("/ingest/preview", json=request_body)

        assert response.status_code == 200
        data = response.json()

        assert "documents" in data
        assert "statistics" in data
        assert isinstance(data["documents"], list)
        assert data["statistics"]["total_documents"] == 0

    def test_empty_request_body(self, test_app: TestClient, seeded_test_data):
        """Test that empty request body works (uses defaults)."""
        response = test_app.post("/ingest/preview", json={})

        assert response.status_code == 200
        data = response.json()

        assert "documents" in data
        assert len(data["documents"]) <= 10  # Default limit

    def test_all_filters_combined(self, test_app: TestClient, seeded_test_data):
        """Test with all filters combined."""
        response = test_app.post(
            "/ingest/preview",
            json={
                "region": "Пловдив",
                "town": None,
                "status": "Действащо",
                "year": 2023,
                "limit": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all filters are applied
        for doc in data["documents"]:
            assert doc["metadata"]["region"] == "Пловдив"
            assert doc["metadata"]["status"] == "Действащо"
            assert doc["metadata"]["year"] == 2023

    def test_document_size_validation(self, test_app: TestClient, seeded_test_data):
        """Test that document size validation works correctly."""
        response = test_app.post("/ingest/preview", json={"limit": 5})

        assert response.status_code == 200
        data = response.json()

        for doc in data["documents"]:
            # is_valid should be based on size
            estimated_tokens = doc["size_info"]["estimated_tokens"]
            max_tokens = 8000  # From DocumentAssemblyService.MAX_TOKENS

            if estimated_tokens <= max_tokens:
                assert doc["is_valid"] is True
            else:
                assert doc["is_valid"] is False

