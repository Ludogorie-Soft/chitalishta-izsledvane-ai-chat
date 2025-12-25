"""Tests for structured output formatter."""

import pytest
from unittest.mock import MagicMock

from app.rag.structured_output import (
    OutputFormat,
    StructuredOutputFormatter,
    get_structured_output_formatter,
)


class TestStructuredOutputFormatter:
    """Tests for StructuredOutputFormatter."""

    def test_format_text_default(self):
        """Test formatting with default text format."""
        formatter = StructuredOutputFormatter()
        result = formatter.format("Test answer", OutputFormat.TEXT)

        assert result["format"] == "text"
        assert result["formatted_answer"] == "Test answer"

    def test_format_bullets_rule_based(self):
        """Test formatting as bullets using rule-based parsing."""
        formatter = StructuredOutputFormatter()
        answer = "Първа точка.\nВтора точка.\nТрета точка."
        result = formatter.format(answer, OutputFormat.BULLETS)

        assert result["format"] == "bullets"
        assert "formatted_answer" in result
        # Should contain bullet markers
        assert "-" in result["formatted_answer"] or "•" in result["formatted_answer"]

    def test_format_table_from_key_value_pairs(self):
        """Test formatting as table from key-value pairs."""
        formatter = StructuredOutputFormatter()
        answer = "Регион: Пловдив\nБрой: 10\nРегион: София\nБрой: 15"
        result = formatter.format(answer, OutputFormat.TABLE)

        assert result["format"] == "table"
        assert "formatted_answer" in result
        # Should contain markdown table format
        assert "|" in result["formatted_answer"]

    def test_format_statistics_from_text(self):
        """Test formatting as statistics from text."""
        formatter = StructuredOutputFormatter()
        answer = "Общо: 100. Средно: 50. Минимум: 10. Максимум: 200."
        result = formatter.format(answer, OutputFormat.STATISTICS)

        assert result["format"] == "statistics"
        assert "formatted_answer" in result

    def test_format_table_with_sql_result(self):
        """Test formatting as table with SQL result data."""
        formatter = StructuredOutputFormatter()
        answer = "Регион: Пловдив, Брой: 10"
        query_result = {
            "sql_executed": True,
            "sql_success": True,
            "sql_answer": answer,
            "rag_executed": False,
        }
        result = formatter.format(answer, OutputFormat.TABLE, query_result)

        assert result["format"] == "table"
        assert "formatted_answer" in result

    def test_format_statistics_with_sql_result(self):
        """Test formatting as statistics with SQL result data."""
        formatter = StructuredOutputFormatter()
        answer = "Общо: 100"
        query_result = {
            "sql_executed": True,
            "sql_success": True,
            "sql_answer": answer,
            "rag_executed": False,
        }
        result = formatter.format(answer, OutputFormat.STATISTICS, query_result)

        assert result["format"] == "statistics"
        assert "formatted_answer" in result

    def test_format_table_with_llm(self):
        """Test formatting as table using LLM."""
        # Mock LLM
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "| Колона 1 | Колона 2 |\n| --- | --- |\n| Стойност 1 | Стойност 2 |"
        mock_llm.invoke.return_value = mock_response

        formatter = StructuredOutputFormatter(llm=mock_llm)
        answer = "Някакъв текст с данни"
        result = formatter.format(answer, OutputFormat.TABLE)

        assert result["format"] == "table"
        assert "formatted_answer" in result
        mock_llm.invoke.assert_called_once()

    def test_format_bullets_with_llm(self):
        """Test formatting as bullets using LLM."""
        # Mock LLM
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "- Точка 1\n- Точка 2\n- Точка 3"
        mock_llm.invoke.return_value = mock_response

        formatter = StructuredOutputFormatter(llm=mock_llm)
        answer = "Някакъв текст"
        result = formatter.format(answer, OutputFormat.BULLETS)

        assert result["format"] == "bullets"
        assert "formatted_answer" in result
        mock_llm.invoke.assert_called_once()

    def test_format_statistics_with_llm(self):
        """Test formatting as statistics using LLM."""
        # Mock LLM
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "## Статистика\n- Брой: 100\n- Средно: 50"
        mock_llm.invoke.return_value = mock_response

        formatter = StructuredOutputFormatter(llm=mock_llm)
        answer = "Някакъв текст с числа"
        result = formatter.format(answer, OutputFormat.STATISTICS)

        assert result["format"] == "statistics"
        assert "formatted_answer" in result
        mock_llm.invoke.assert_called_once()

    def test_format_unknown_format_fallback(self):
        """Test formatting with unknown format falls back to text."""
        formatter = StructuredOutputFormatter()
        # Use a string that's not in the enum
        result = formatter.format("Test", "unknown_format")  # type: ignore

        assert result["format"] == "text"
        assert result["formatted_answer"] == "Test"

    def test_extract_table_from_markdown(self):
        """Test extracting table data from markdown format."""
        formatter = StructuredOutputFormatter()
        markdown = "| Регион | Брой |\n| --- | --- |\n| Пловдив | 10 |\n| София | 15 |"
        table_data = formatter._extract_table_from_sql_answer(markdown)

        assert table_data is not None
        assert len(table_data) == 2
        assert table_data[0]["Регион"] == "Пловдив"
        assert table_data[0]["Брой"] == "10"

    def test_parse_text_for_bullets(self):
        """Test parsing text to extract bullet points."""
        formatter = StructuredOutputFormatter()
        text = "Първа точка.\nВтора точка.\nТрета точка."
        bullets = formatter._parse_text_for_bullets(text)

        assert len(bullets) == 3
        assert "Първа точка" in bullets[0]
        assert "Втора точка" in bullets[1]

    def test_extract_statistics_from_text(self):
        """Test extracting statistics from text."""
        formatter = StructuredOutputFormatter()
        text = "Общо: 100. Средно: 50. Минимум: 10. Максимум: 200."
        stats = formatter._extract_statistics_from_text(text)

        assert stats is not None
        assert "values" in stats or "count" in stats

    def test_create_markdown_table(self):
        """Test creating markdown table from data."""
        formatter = StructuredOutputFormatter()
        data = [
            {"Регион": "Пловдив", "Брой": "10"},
            {"Регион": "София", "Брой": "15"},
        ]
        table = formatter._create_markdown_table(data)

        assert "|" in table
        assert "Регион" in table
        assert "Брой" in table
        assert "Пловдив" in table
        assert "София" in table


class TestStructuredOutputFormatterFactory:
    """Tests for factory function."""

    def test_get_structured_output_formatter_default(self):
        """Test getting formatter without LLM."""
        formatter = get_structured_output_formatter()
        assert isinstance(formatter, StructuredOutputFormatter)
        assert formatter.llm is None

    def test_get_structured_output_formatter_with_llm(self):
        """Test getting formatter with LLM."""
        mock_llm = MagicMock()
        formatter = get_structured_output_formatter(llm=mock_llm)
        assert isinstance(formatter, StructuredOutputFormatter)
        assert formatter.llm == mock_llm

