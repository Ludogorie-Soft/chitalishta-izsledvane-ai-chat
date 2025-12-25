"""Structured output formatting for chat responses."""

import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.prompts import ChatPromptTemplate
except ImportError as _e:  # pragma: no cover - guarded by tests
    BaseChatModel = object  # type: ignore[assignment]
    ChatPromptTemplate = object  # type: ignore[assignment]
    _LANGCHAIN_IMPORT_ERROR = _e
else:
    _LANGCHAIN_IMPORT_ERROR = None


class OutputFormat(str, Enum):
    """Supported output formats for structured responses."""

    TEXT = "text"  # Default plain text
    TABLE = "table"  # Tabular format
    BULLETS = "bullets"  # Bullet point summary
    STATISTICS = "statistics"  # Statistical summary format


class StructuredOutputFormatter:
    """
    Formatter for converting text answers into structured formats.

    Supports:
    - Tables: Converts data into markdown tables
    - Bullets: Converts into bullet point lists
    - Statistics: Formats numerical data as statistics
    """

    def __init__(self, llm: Optional[BaseChatModel] = None):
        """
        Initialize structured output formatter.

        Args:
            llm: Optional LLM for intelligent formatting (if None, uses rule-based parsing)
        """
        self.llm = llm

    def format(
        self,
        answer: str,
        format_type: OutputFormat,
        query_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format answer into requested structured format.

        Args:
            answer: Plain text answer
            format_type: Desired output format
            query_result: Optional raw query result with SQL/RAG data for better formatting

        Returns:
            Dictionary with formatted output and metadata
        """
        if format_type == OutputFormat.TEXT:
            return {"formatted_answer": answer, "format": "text"}

        elif format_type == OutputFormat.TABLE:
            return self._format_as_table(answer, query_result)

        elif format_type == OutputFormat.BULLETS:
            return self._format_as_bullets(answer, query_result)

        elif format_type == OutputFormat.STATISTICS:
            return self._format_as_statistics(answer, query_result)

        else:
            logger.warning(f"Unknown format type: {format_type}, returning text")
            return {"formatted_answer": answer, "format": "text"}

    def _format_as_table(
        self, answer: str, query_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format answer as a markdown table.

        Args:
            answer: Plain text answer
            query_result: Optional raw query result

        Returns:
            Dictionary with table-formatted answer
        """
        # Try to extract table data from SQL results if available
        if query_result and query_result.get("sql_executed") and query_result.get("sql_success"):
            # If we have SQL results, try to format them as a table
            sql_answer = query_result.get("sql_answer", "")
            table_data = self._extract_table_from_sql_answer(sql_answer)
            if table_data:
                markdown_table = self._create_markdown_table(table_data)
                return {
                    "formatted_answer": markdown_table,
                    "format": "table",
                    "raw_data": table_data,
                }

        # Use LLM to convert text to table if available
        if self.llm:
            try:
                table_prompt = self._create_table_conversion_prompt(answer)
                result = self.llm.invoke(table_prompt)
                if hasattr(result, "content"):
                    table_text = result.content
                else:
                    table_text = str(result)
                return {"formatted_answer": table_text, "format": "table"}
            except Exception as e:
                logger.warning(f"LLM table conversion failed: {e}, using rule-based")

        # Fallback: Try to parse text for table-like structures
        table_data = self._parse_text_for_table(answer)
        if table_data:
            markdown_table = self._create_markdown_table(table_data)
            return {
                "formatted_answer": markdown_table,
                "format": "table",
                "raw_data": table_data,
            }

        # Last resort: Return answer with table formatting instructions
        return {
            "formatted_answer": answer,
            "format": "table",
            "note": "Could not automatically format as table. Answer returned as text.",
        }

    def _format_as_bullets(
        self, answer: str, query_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format answer as bullet points.

        Args:
            answer: Plain text answer
            query_result: Optional raw query result

        Returns:
            Dictionary with bullet-formatted answer
        """
        # Use LLM to convert text to bullets if available
        if self.llm:
            try:
                bullets_prompt = self._create_bullets_conversion_prompt(answer)
                result = self.llm.invoke(bullets_prompt)
                if hasattr(result, "content"):
                    bullets_text = result.content
                else:
                    bullets_text = str(result)
                return {"formatted_answer": bullets_text, "format": "bullets"}
            except Exception as e:
                logger.warning(f"LLM bullets conversion failed: {e}, using rule-based")

        # Fallback: Rule-based parsing
        bullets = self._parse_text_for_bullets(answer)
        if bullets:
            bullets_text = "\n".join(f"- {bullet}" for bullet in bullets)
            return {
                "formatted_answer": bullets_text,
                "format": "bullets",
                "raw_data": bullets,
            }

        # Last resort: Split by sentences/paragraphs
        lines = [line.strip() for line in answer.split("\n") if line.strip()]
        bullets_text = "\n".join(f"- {line}" for line in lines)
        return {"formatted_answer": bullets_text, "format": "bullets"}

    def _format_as_statistics(
        self, answer: str, query_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format answer as statistics summary.

        Args:
            answer: Plain text answer
            query_result: Optional raw query result

        Returns:
            Dictionary with statistics-formatted answer
        """
        # Extract numerical data from SQL results if available
        if query_result and query_result.get("sql_executed") and query_result.get("sql_success"):
            sql_answer = query_result.get("sql_answer", "")
            stats = self._extract_statistics_from_sql_answer(sql_answer)
            if stats:
                stats_text = self._format_statistics_text(stats)
                return {
                    "formatted_answer": stats_text,
                    "format": "statistics",
                    "raw_data": stats,
                }

        # Use LLM to extract and format statistics if available
        if self.llm:
            try:
                stats_prompt = self._create_statistics_conversion_prompt(answer)
                result = self.llm.invoke(stats_prompt)
                if hasattr(result, "content"):
                    stats_text = result.content
                else:
                    stats_text = str(result)
                return {"formatted_answer": stats_text, "format": "statistics"}
            except Exception as e:
                logger.warning(f"LLM statistics conversion failed: {e}, using rule-based")

        # Fallback: Rule-based extraction
        stats = self._extract_statistics_from_text(answer)
        if stats:
            stats_text = self._format_statistics_text(stats)
            return {
                "formatted_answer": stats_text,
                "format": "statistics",
                "raw_data": stats,
            }

        # Last resort: Return answer with statistics formatting
        return {
            "formatted_answer": answer,
            "format": "statistics",
            "note": "Could not automatically extract statistics. Answer returned as text.",
        }

    # Helper methods for table formatting

    def _extract_table_from_sql_answer(self, sql_answer: str) -> Optional[List[Dict[str, Any]]]:
        """Extract table data from SQL answer text."""
        # Look for patterns like "Region: X, Count: Y" or "| Region | Count |"
        # This is a simple parser - could be enhanced
        lines = sql_answer.split("\n")
        table_data = []
        headers = None

        for line in lines:
            # Check for markdown table format
            if "|" in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                # Skip separator rows (containing only --- or similar)
                if all(part.replace("-", "").strip() == "" for part in parts):
                    continue
                if not headers and len(parts) > 1:
                    headers = parts
                elif headers and len(parts) == len(headers):
                    row = dict(zip(headers, parts))
                    table_data.append(row)
            # Check for key-value pairs
            elif ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if not headers:
                        headers = ["Metric", "Value"]
                    table_data.append({"Metric": key, "Value": value})

        return table_data if table_data else None

    def _parse_text_for_table(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """Parse text to extract table-like structures."""
        # Look for patterns that suggest tabular data
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        table_data = []

        for line in lines:
            # Pattern: "Key: Value" or "Key - Value"
            if ":" in line or " - " in line:
                separator = ":" if ":" in line else " - "
                parts = line.split(separator, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    table_data.append({"Metric": key, "Value": value})

        return table_data if table_data else None

    def _create_markdown_table(self, data: List[Dict[str, Any]]) -> str:
        """Create markdown table from list of dictionaries."""
        if not data:
            return ""

        # Get all unique keys as headers
        headers = list(data[0].keys())
        header_row = "| " + " | ".join(headers) + " |"
        separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"

        rows = []
        for row in data:
            values = [str(row.get(header, "")) for header in headers]
            rows.append("| " + " | ".join(values) + " |")

        return "\n".join([header_row, separator_row] + rows)

    # Helper methods for bullets formatting

    def _parse_text_for_bullets(self, text: str) -> List[str]:
        """Parse text to extract bullet points."""
        bullets = []
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        for line in lines:
            # Remove existing bullet markers
            line = re.sub(r"^[-•*]\s*", "", line)
            # Remove numbering
            line = re.sub(r"^\d+[.)]\s*", "", line)
            if line:
                bullets.append(line)

        return bullets

    # Helper methods for statistics formatting

    def _extract_statistics_from_sql_answer(self, sql_answer: str) -> Optional[Dict[str, Any]]:
        """Extract statistics from SQL answer."""
        stats = {}
        # Look for numerical patterns
        numbers = re.findall(r"(\d+(?:\.\d+)?)", sql_answer)
        if numbers:
            stats["values"] = [float(n) for n in numbers]
            stats["count"] = len(numbers)
            stats["sum"] = sum(stats["values"])
            stats["average"] = stats["sum"] / stats["count"] if stats["count"] > 0 else 0
            stats["min"] = min(stats["values"])
            stats["max"] = max(stats["values"])

        # Look for specific patterns like "Total: X", "Average: Y"
        patterns = {
            "total": r"(?:общо|total|сума|sum)[:\s]+(\d+(?:\.\d+)?)",
            "average": r"(?:средно|average|avg|средна стойност)[:\s]+(\d+(?:\.\d+)?)",
            "count": r"(?:брой|count|броя)[:\s]+(\d+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, sql_answer, re.IGNORECASE)
            if match:
                stats[key] = float(match.group(1))

        return stats if stats else None

    def _extract_statistics_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract statistics from plain text."""
        return self._extract_statistics_from_sql_answer(text)  # Reuse same logic

    def _format_statistics_text(self, stats: Dict[str, Any]) -> str:
        """Format statistics dictionary as text."""
        lines = ["## Статистика\n"]
        if "count" in stats:
            lines.append(f"- **Брой стойности**: {stats['count']}")
        if "sum" in stats:
            lines.append(f"- **Обща сума**: {stats['sum']:.2f}")
        if "average" in stats:
            lines.append(f"- **Средна стойност**: {stats['average']:.2f}")
        if "min" in stats:
            lines.append(f"- **Минимална стойност**: {stats['min']:.2f}")
        if "max" in stats:
            lines.append(f"- **Максимална стойност**: {stats['max']:.2f}")

        return "\n".join(lines)

    # LLM prompt creation methods

    def _create_table_conversion_prompt(self, answer: str) -> str:
        """Create prompt for LLM to convert text to table."""
        return f"""Преобразувай следния текст в markdown таблица.
Ако текстът съдържа данни, които могат да бъдат представени като таблица, създай подходяща таблица.
Ако не, върни оригиналния текст.

Текст:
{answer}

Отговор (само таблицата или оригиналния текст):"""

    def _create_bullets_conversion_prompt(self, answer: str) -> str:
        """Create prompt for LLM to convert text to bullets."""
        return f"""Преобразувай следния текст в списък с bullet points.
Всеки важен факт или точка трябва да бъде отделен bullet point.
Използвай формат: - точка 1
- точка 2
и т.н.

Текст:
{answer}

Отговор (само bullet points):"""

    def _create_statistics_conversion_prompt(self, answer: str) -> str:
        """Create prompt for LLM to extract and format statistics."""
        return f"""Извлечи статистически данни от следния текст и ги форматирай като статистически резюме.
Включи: брой, сума, средна стойност, минимум, максимум където е приложимо.

Текст:
{answer}

Отговор (статистическо резюме):"""


def get_structured_output_formatter(
    llm: Optional[BaseChatModel] = None,
) -> StructuredOutputFormatter:
    """
    Factory function to get a StructuredOutputFormatter.

    Args:
        llm: Optional LLM for intelligent formatting

    Returns:
        StructuredOutputFormatter instance
    """
    return StructuredOutputFormatter(llm=llm)

