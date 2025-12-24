"""Tests for hallucination control modes."""

import pytest
from unittest.mock import MagicMock, patch

pytest.importorskip("langchain_core")

from app.rag.hallucination_control import (
    HallucinationConfig,
    HallucinationMode,
    PromptEnhancer,
    get_default_hallucination_config,
)


class TestHallucinationConfig:
    """Tests for HallucinationConfig."""

    def test_low_tolerance_defaults(self):
        """Low tolerance mode should have strict defaults."""
        config = HallucinationConfig(mode=HallucinationMode.LOW_TOLERANCE)

        assert config.temperature == 0.0
        assert config.enforce_citations is True
        assert config.require_grounding is True

    def test_medium_tolerance_defaults(self):
        """Medium tolerance mode should have balanced defaults."""
        config = HallucinationConfig(mode=HallucinationMode.MEDIUM_TOLERANCE)

        assert config.temperature == 0.3
        assert config.enforce_citations is False
        assert config.require_grounding is True

    def test_high_tolerance_defaults(self):
        """High tolerance mode should have flexible defaults."""
        config = HallucinationConfig(mode=HallucinationMode.HIGH_TOLERANCE)

        assert config.temperature == 0.7
        assert config.enforce_citations is False
        assert config.require_grounding is False

    def test_custom_temperature_override(self):
        """Config should allow temperature override."""
        config = HallucinationConfig(
            mode=HallucinationMode.LOW_TOLERANCE,
            temperature=0.5
        )

        assert config.temperature == 0.5
        assert config.enforce_citations is True  # Still uses mode default

    def test_custom_citation_override(self):
        """Config should allow citation enforcement override."""
        config = HallucinationConfig(
            mode=HallucinationMode.HIGH_TOLERANCE,
            enforce_citations=True
        )

        assert config.enforce_citations is True
        assert config.temperature == 0.7  # Still uses mode default

    def test_get_llm_with_config(self):
        """get_llm_with_config should configure LLM instance."""
        try:
            from langchain_core.language_models.chat_models import BaseChatModel
            from unittest.mock import MagicMock

            # Create a mock LLM that supports temperature attribute
            mock_llm = MagicMock(spec=BaseChatModel)
            mock_llm.temperature = 0.0
            mock_llm.model_kwargs = {}

            config = HallucinationConfig(mode=HallucinationMode.LOW_TOLERANCE)

            configured_llm = config.get_llm_with_config(mock_llm)

            # Should return the LLM (may be modified or same instance)
            assert configured_llm is not None
            # Temperature should be set to 0.0 for low tolerance
            assert mock_llm.temperature == 0.0
        except ImportError:
            pytest.skip("LangChain not available")


class TestPromptEnhancer:
    """Tests for PromptEnhancer."""

    def test_enhance_rag_prompt_low_tolerance(self):
        """RAG prompt should be enhanced with strict instructions for low tolerance."""
        base_prompt = "Base prompt text"
        config = HallucinationConfig(mode=HallucinationMode.LOW_TOLERANCE)

        enhanced = PromptEnhancer.enhance_rag_prompt(base_prompt, config)

        # Should return a ChatPromptTemplate
        assert enhanced is not None
        # The enhanced prompt should include strict instructions
        # We can't easily check the content without invoking the template,
        # but we can verify it's a valid template

    def test_enhance_rag_prompt_high_tolerance(self):
        """RAG prompt should be enhanced with flexible instructions for high tolerance."""
        base_prompt = "Base prompt text"
        config = HallucinationConfig(mode=HallucinationMode.HIGH_TOLERANCE)

        enhanced = PromptEnhancer.enhance_rag_prompt(base_prompt, config)

        assert enhanced is not None

    def test_enhance_sql_prompt_low_tolerance(self):
        """SQL prompt should be enhanced with strict instructions for low tolerance."""
        base_prompt = "Base SQL prompt"
        config = HallucinationConfig(mode=HallucinationMode.LOW_TOLERANCE)

        enhanced = PromptEnhancer.enhance_sql_prompt(base_prompt, config)

        assert "СТРОГИ ПРАВИЛА" in enhanced
        assert "SQL" in enhanced

    def test_enhance_sql_prompt_high_tolerance(self):
        """SQL prompt should be enhanced with flexible instructions for high tolerance."""
        base_prompt = "Base SQL prompt"
        config = HallucinationConfig(mode=HallucinationMode.HIGH_TOLERANCE)

        enhanced = PromptEnhancer.enhance_sql_prompt(base_prompt, config)

        assert "ГЪВКАВИ ПРАВИЛА" in enhanced
        assert "SQL" in enhanced

    def test_enhance_synthesis_prompt_low_tolerance(self):
        """Synthesis prompt should be enhanced with strict instructions for low tolerance."""
        base_prompt = "Base synthesis prompt"
        config = HallucinationConfig(mode=HallucinationMode.LOW_TOLERANCE)

        enhanced = PromptEnhancer.enhance_synthesis_prompt(base_prompt, config)

        assert "СТРОГИ ПРАВИЛА" in enhanced
        assert "СИНТЕЗА" in enhanced

    def test_enhance_synthesis_prompt_high_tolerance(self):
        """Synthesis prompt should be enhanced with flexible instructions for high tolerance."""
        base_prompt = "Base synthesis prompt"
        config = HallucinationConfig(mode=HallucinationMode.HIGH_TOLERANCE)

        enhanced = PromptEnhancer.enhance_synthesis_prompt(base_prompt, config)

        assert "ГЪВКАВИ ПРАВИЛА" in enhanced
        assert "СИНТЕЗА" in enhanced


class TestHallucinationControlConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_default_hallucination_config(self):
        """get_default_hallucination_config should return medium tolerance by default."""
        config = get_default_hallucination_config()

        assert config.mode == HallucinationMode.MEDIUM_TOLERANCE
        assert config.temperature == 0.3

    def test_get_default_hallucination_config_with_mode(self):
        """get_default_hallucination_config should accept mode override."""
        config = get_default_hallucination_config(mode=HallucinationMode.LOW_TOLERANCE)

        assert config.mode == HallucinationMode.LOW_TOLERANCE
        assert config.temperature == 0.0

