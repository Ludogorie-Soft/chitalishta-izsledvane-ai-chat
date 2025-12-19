"""Service for processing DOCX analysis documents."""
import re
from pathlib import Path
from typing import Optional

from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph


class DocumentProcessor:
    """Service for processing and chunking DOCX analysis documents."""

    # Approximate tokens per character for Bulgarian text
    CHARS_PER_TOKEN = 3.5

    # Target chunk size (tokens)
    MIN_CHUNK_TOKENS = 700
    MAX_CHUNK_TOKENS = 900

    # Overlap percentage
    OVERLAP_PERCENTAGE = 0.12  # 12% overlap

    def __init__(self, document_path: Optional[str] = None):
        """
        Initialize the document processor.

        Args:
            document_path: Path to the DOCX file. If None, uses default.
        """
        if document_path is None:
            # Default to project root
            project_root = Path(__file__).parent.parent.parent
            document_path = project_root / "Chitalishta_demo_ver2.docx"

        self.document_path = Path(document_path)
        self.document: Optional[DocumentType] = None

    def load_document(self) -> DocumentType:
        """
        Load the DOCX document.

        Returns:
            Document object

        Raises:
            FileNotFoundError: If document file doesn't exist
        """
        if not self.document_path.exists():
            raise FileNotFoundError(f"Document not found: {self.document_path}")

        self.document = Document(str(self.document_path))
        return self.document

    def extract_sections(self) -> list[dict]:
        """
        Extract structured sections from the document.

        Returns:
            List of sections, each with heading and paragraphs
        """
        if self.document is None:
            self.load_document()

        sections = []
        current_section = None

        for paragraph in self.document.paragraphs:
            text = paragraph.text.strip()

            if not text:
                continue

            # Check if paragraph is a heading (style-based or formatting-based)
            is_heading = self._is_heading(paragraph)

            if is_heading:
                # Save previous section if exists
                if current_section is not None:
                    sections.append(current_section)

                # Start new section
                current_section = {
                    "heading": text,
                    "paragraphs": [],
                    "level": self._get_heading_level(paragraph),
                }
            else:
                # Add paragraph to current section
                if current_section is None:
                    # No heading yet, create a default section
                    current_section = {
                        "heading": "Въведение",
                        "paragraphs": [],
                        "level": 1,
                    }

                current_section["paragraphs"].append(text)

        # Add last section
        if current_section is not None:
            sections.append(current_section)

        return sections

    def chunk_document(self) -> list[dict]:
        """
        Chunk the document using hierarchical strategy.

        Returns:
            List of chunks with content and metadata
        """
        sections = self.extract_sections()
        chunks = []

        for section in sections:
            heading = section["heading"]
            paragraphs = section["paragraphs"]

            # Step 1: Create base chunk from section
            section_text = self._combine_section_text(heading, paragraphs)
            section_tokens = self._estimate_tokens(section_text)

            # Step 2: If section fits in one chunk, use it as-is
            if section_tokens <= self.MAX_CHUNK_TOKENS:
                chunk = self._create_chunk(
                    content=section_text,
                    heading=heading,
                    section_index=len(chunks),
                )
                chunks.append(chunk)
            else:
                # Step 3: Split long sections by paragraphs with overlap
                section_chunks = self._split_section_with_overlap(
                    heading, paragraphs, section_index=len(chunks)
                )
                chunks.extend(section_chunks)

        return chunks

    def _is_heading(self, paragraph: Paragraph) -> bool:
        """
        Determine if a paragraph is a heading.

        Args:
            paragraph: Paragraph to check

        Returns:
            True if paragraph is a heading
        """
        # Check style name
        style_name = paragraph.style.name.lower()
        if "heading" in style_name or "заглавие" in style_name:
            return True

        # Check if paragraph is short and formatted (common heading pattern)
        text = paragraph.text.strip()
        if len(text) < 100 and len(text.split()) < 15:
            # Check formatting (bold, larger font, etc.)
            runs = paragraph.runs
            if runs:
                first_run = runs[0]
                if first_run.bold or (first_run.font.size and first_run.font.size.pt > 12):
                    return True

        return False

    def _get_heading_level(self, paragraph: Paragraph) -> int:
        """
        Get heading level (1-6).

        Args:
            paragraph: Heading paragraph

        Returns:
            Heading level (default: 1)
        """
        style_name = paragraph.style.name.lower()
        # Extract number from style name (e.g., "Heading 1" -> 1)
        match = re.search(r"heading\s*(\d+)", style_name)
        if match:
            return int(match.group(1))

        return 1

    def _combine_section_text(self, heading: str, paragraphs: list[str]) -> str:
        """Combine heading and paragraphs into section text."""
        parts = [heading]
        parts.extend(paragraphs)
        return "\n\n".join(parts)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return int(len(text) / self.CHARS_PER_TOKEN)

    def _split_section_with_overlap(
        self, heading: str, paragraphs: list[str], section_index: int
    ) -> list[dict]:
        """
        Split a long section into chunks with overlap.

        Args:
            heading: Section heading
            paragraphs: List of paragraph texts
            section_index: Index of the section (for chunk numbering)

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        current_chunk_paragraphs = []
        current_tokens = 0

        # Estimate tokens per paragraph
        para_tokens = [self._estimate_tokens(p) for p in paragraphs]

        i = 0
        while i < len(paragraphs):
            para = paragraphs[i]
            para_token_count = para_tokens[i]

            # Check if adding this paragraph would exceed max
            if (
                current_tokens + para_token_count > self.MAX_CHUNK_TOKENS
                and current_chunk_paragraphs
            ):
                # Create chunk from current paragraphs
                chunk_text = self._combine_section_text(heading, current_chunk_paragraphs)
                chunk = self._create_chunk(
                    content=chunk_text,
                    heading=heading,
                    section_index=section_index,
                    chunk_index=len(chunks),
                )
                chunks.append(chunk)

                # Calculate overlap: keep last N paragraphs for overlap
                overlap_tokens = int(current_tokens * self.OVERLAP_PERCENTAGE)
                overlap_paragraphs = []
                overlap_count = 0

                # Add paragraphs from the end until we reach overlap size
                for para_idx in range(len(current_chunk_paragraphs) - 1, -1, -1):
                    if overlap_count >= overlap_tokens:
                        break
                    overlap_paragraphs.insert(0, current_chunk_paragraphs[para_idx])
                    overlap_count += para_tokens[
                        i - len(current_chunk_paragraphs) + para_idx
                    ]

                # Start new chunk with overlap
                current_chunk_paragraphs = overlap_paragraphs
                current_tokens = overlap_count

            # Add paragraph to current chunk
            current_chunk_paragraphs.append(para)
            current_tokens += para_token_count
            i += 1

        # Add remaining paragraphs as final chunk
        if current_chunk_paragraphs:
            chunk_text = self._combine_section_text(heading, current_chunk_paragraphs)
            chunk = self._create_chunk(
                content=chunk_text,
                heading=heading,
                section_index=section_index,
                chunk_index=len(chunks),
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        content: str,
        heading: str,
        section_index: int,
        chunk_index: Optional[int] = None,
    ) -> dict:
        """
        Create a chunk dictionary with content and metadata.

        Args:
            content: Chunk content text
            heading: Section heading
            section_index: Index of the section
            chunk_index: Optional index within the section

        Returns:
            Chunk dictionary
        """
        estimated_tokens = self._estimate_tokens(content)

        metadata = {
            "source": "analysis_document",
            "document_type": "main_analysis",
            "document_name": "Chitalishta_demo_ver2",
            "author": "ИПИ",
            "document_date": "2025-12-09",
            "language": "bg",
            "scope": "national",
            "version": "v2",
            "section_heading": heading,
            "section_index": section_index,
        }

        if chunk_index is not None:
            metadata["chunk_index"] = chunk_index

        size_info = {
            "characters": len(content),
            "words": len(content.split()),
            "estimated_tokens": estimated_tokens,
        }

        return {
            "content": content,
            "metadata": metadata,
            "size_info": size_info,
            "is_valid": estimated_tokens <= 8000,  # Same max as DB documents
        }

