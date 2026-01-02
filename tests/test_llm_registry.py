"""Tests for LLM registry."""

import pytest
from unittest.mock import MagicMock, patch

pytest.importorskip("langchain_core")

from app.rag.llm_registry import (
    LLMRegistry,
    LLMTask,
    get_classification_llm,
    get_generation_llm,
    get_llm_for_task,
    get_llm_registry,
    get_synthesis_llm,
)


class TestLLMRegistry:
    """Tests for LLMRegistry."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        try:
            from langchain_core.language_models.chat_models import BaseChatModel

            class MockLLM(BaseChatModel):
                def _generate(self, messages, stop=None, run_manager=None, **kwargs):
                    return self._generate_helper(messages, stop, **kwargs)

                def _generate_helper(self, messages, stop=None, **kwargs):
                    from langchain_core.messages import AIMessage
                    return [
                        type("Generation", (), {
                            "message": AIMessage(content="Mock response"),
                            "generation_info": {},
                        })()
                    ]

                @property
                def _llm_type(self):
                    return "mock"

            return MockLLM()
        except ImportError:
            pytest.skip("LangChain not available")

    def test_registry_initializes(self):
        """Registry should initialize with default providers."""
        registry = LLMRegistry()
        assert registry.default_provider is not None
        assert registry.classification_provider is not None
        assert registry.generation_provider is not None
        assert registry.synthesis_provider is not None

    def test_registry_with_custom_providers(self):
        """Registry should accept custom providers for each task."""
        registry = LLMRegistry(
            default_provider="openai",
            classification_provider="openai",
            generation_provider="openai",
            synthesis_provider="openai",
        )
        assert registry.default_provider == "openai"
        assert registry.classification_provider == "openai"
        assert registry.generation_provider == "openai"
        assert registry.synthesis_provider == "openai"

    def test_get_llm_for_classification_task(self, mock_llm):
        """Registry should return LLM for classification task."""
        with patch("app.rag.llm_registry.LLMRegistry._create_llm") as mock_create:
            mock_create.return_value = mock_llm

            registry = LLMRegistry()
            llm = registry.get_llm(task=LLMTask.CLASSIFICATION)

            assert llm == mock_llm
            mock_create.assert_called_once()
            # Check that task is passed correctly
            # Temperature is None (defaults are set inside _create_llm)
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs.get("task") == LLMTask.CLASSIFICATION
            # Temperature defaults are handled inside _create_llm, so we see None here
            assert call_kwargs.get("temperature") is None

    def test_get_llm_for_generation_task(self, mock_llm):
        """Registry should return LLM for generation task."""
        with patch("app.rag.llm_registry.LLMRegistry._create_llm") as mock_create:
            mock_create.return_value = mock_llm

            registry = LLMRegistry()
            llm = registry.get_llm(task=LLMTask.GENERATION)

            assert llm == mock_llm
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs.get("task") == LLMTask.GENERATION

    def test_get_llm_for_synthesis_task(self, mock_llm):
        """Registry should return LLM for synthesis task."""
        with patch("app.rag.llm_registry.LLMRegistry._create_llm") as mock_create:
            mock_create.return_value = mock_llm

            registry = LLMRegistry()
            llm = registry.get_llm(task=LLMTask.SYNTHESIS)

            assert llm == mock_llm
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            # Temperature defaults are handled inside _create_llm, so we see None here
            # The actual default (0.3) is set inside _create_llm
            assert call_kwargs.get("temperature") is None
            assert call_kwargs.get("task") == LLMTask.SYNTHESIS

    def test_llm_caching(self, mock_llm):
        """Registry should cache LLM instances."""
        with patch("app.rag.llm_registry.LLMRegistry._create_llm") as mock_create:
            mock_create.return_value = mock_llm

            registry = LLMRegistry()

            # Get same LLM twice
            llm1 = registry.get_llm(task=LLMTask.CLASSIFICATION)
            llm2 = registry.get_llm(task=LLMTask.CLASSIFICATION)

            assert llm1 == llm2
            # Should only create once
            assert mock_create.call_count == 1

    def test_clear_cache(self, mock_llm):
        """Registry should clear cache when requested."""
        with patch("app.rag.llm_registry.LLMRegistry._create_llm") as mock_create:
            mock_create.return_value = mock_llm

            registry = LLMRegistry()
            registry.get_llm(task=LLMTask.CLASSIFICATION)

            assert registry.get_cached_llm_count() == 1

            registry.clear_cache()

            assert registry.get_cached_llm_count() == 0

    def test_custom_temperature(self, mock_llm):
        """Registry should respect custom temperature."""
        with patch("app.rag.llm_registry.LLMRegistry._create_llm") as mock_create:
            mock_create.return_value = mock_llm

            registry = LLMRegistry()
            registry.get_llm(task=LLMTask.GENERATION, temperature=0.7)

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs.get("temperature") == 0.7

    def test_custom_model_name(self, mock_llm):
        """Registry should respect custom model name."""
        with patch("app.rag.llm_registry.LLMRegistry._create_llm") as mock_create:
            mock_create.return_value = mock_llm

            registry = LLMRegistry()
            registry.get_llm(task=LLMTask.GENERATION, model_name="gpt-4")

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs.get("model_name") == "gpt-4"

    def test_provider_override(self, mock_llm):
        """Registry should allow provider override per call."""
        with patch("app.rag.llm_registry.LLMRegistry._create_llm") as mock_create:
            mock_create.return_value = mock_llm

            registry = LLMRegistry(default_provider="openai")
            registry.get_llm(task=LLMTask.GENERATION, provider="tgi")

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs.get("provider") == "tgi"


class TestLLMRegistryConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_llm_registry_returns_singleton(self):
        """get_llm_registry should return singleton instance."""
        registry1 = get_llm_registry()
        registry2 = get_llm_registry()

        assert registry1 is registry2

    def test_get_classification_llm(self):
        """get_classification_llm should return LLM for classification."""
        with patch("app.rag.llm_registry.get_llm_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_llm = MagicMock()
            mock_registry.get_llm.return_value = mock_llm
            mock_get_registry.return_value = mock_registry

            llm = get_classification_llm()

            assert llm == mock_llm
            # The function passes provider=None, model_name=None, temperature=None as kwargs
            mock_registry.get_llm.assert_called_once()
            call_kwargs = mock_registry.get_llm.call_args[1]
            assert call_kwargs.get("task") == LLMTask.CLASSIFICATION

    def test_get_generation_llm(self):
        """get_generation_llm should return LLM for generation."""
        with patch("app.rag.llm_registry.get_llm_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_llm = MagicMock()
            mock_registry.get_llm.return_value = mock_llm
            mock_get_registry.return_value = mock_registry

            llm = get_generation_llm()

            assert llm == mock_llm
            # The function passes provider=None, model_name=None, temperature=None as kwargs
            mock_registry.get_llm.assert_called_once()
            call_kwargs = mock_registry.get_llm.call_args[1]
            assert call_kwargs.get("task") == LLMTask.GENERATION

    def test_get_synthesis_llm(self):
        """get_synthesis_llm should return LLM for synthesis."""
        with patch("app.rag.llm_registry.get_llm_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_llm = MagicMock()
            mock_registry.get_llm.return_value = mock_llm
            mock_get_registry.return_value = mock_registry

            llm = get_synthesis_llm()

            assert llm == mock_llm
            # The function passes provider=None, model_name=None, temperature=None as kwargs
            mock_registry.get_llm.assert_called_once()
            call_kwargs = mock_registry.get_llm.call_args[1]
            assert call_kwargs.get("task") == LLMTask.SYNTHESIS

    def test_get_llm_for_task(self):
        """get_llm_for_task should delegate to registry."""
        with patch("app.rag.llm_registry.get_llm_registry") as mock_get_registry:
            mock_registry = MagicMock()
            mock_llm = MagicMock()
            mock_registry.get_llm.return_value = mock_llm
            mock_get_registry.return_value = mock_registry

            llm = get_llm_for_task(task=LLMTask.GENERATION, temperature=0.5)

            assert llm == mock_llm
            # The function passes all kwargs, including provider=None, model_name=None
            mock_registry.get_llm.assert_called_once()
            call_kwargs = mock_registry.get_llm.call_args[1]
            assert call_kwargs.get("task") == LLMTask.GENERATION
            assert call_kwargs.get("temperature") == 0.5

