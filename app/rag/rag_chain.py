"""RAG (Retrieval-Augmented Generation) chain using LangChain."""

import logging
from typing import Dict, List, Optional, Tuple

from app.rag.langchain_integration import LangChainChromaFactory, get_langchain_retriever
from app.rag.llm_intent_classification import get_default_llm

logger = logging.getLogger(__name__)

try:
    from langchain.chains import RetrievalQA
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.runnables import RunnablePassthrough
except ImportError as _e:  # pragma: no cover - guarded by tests
    RetrievalQA = None  # type: ignore[assignment]
    BaseChatModel = object  # type: ignore[assignment]
    ChatPromptTemplate = object  # type: ignore[assignment]
    PromptTemplate = object  # type: ignore[assignment]
    BaseRetriever = object  # type: ignore[assignment]
    RunnablePassthrough = object  # type: ignore[assignment]
    _LANGCHAIN_IMPORT_ERROR = _e
else:
    _LANGCHAIN_IMPORT_ERROR = None


class ContextAssembler:
    """
    Custom context assembler that maintains separation between DB facts and analysis document.

    This ensures we have full control over how context is assembled before passing to LLM.
    """

    def __init__(
        self,
        db_retriever: BaseRetriever,
        analysis_retriever: Optional[BaseRetriever] = None,
        prefer_db_for_factual: bool = True,
    ):
        """
        Initialize context assembler.

        Args:
            db_retriever: Retriever for database content
            analysis_retriever: Optional retriever for analysis document. If None, uses db_retriever with filter.
            prefer_db_for_factual: If True, prioritize DB content for factual queries
        """
        self.db_retriever = db_retriever
        self.analysis_retriever = analysis_retriever
        self.prefer_db_for_factual = prefer_db_for_factual

    def assemble_context(
        self, query: str, k_db: int = 4, k_analysis: int = 2, use_analysis: bool = True
    ) -> Tuple[List, Dict[str, any]]:
        """
        Assemble context from both DB and analysis document with priority logic.

        Args:
            query: User query
            k_db: Number of DB documents to retrieve
            k_analysis: Number of analysis documents to retrieve
            use_analysis: Whether to include analysis documents

        Returns:
            Tuple of (retrieved_documents, context_metadata)
        """
        # Always retrieve DB content (primary source of facts)
        db_docs = self.db_retriever.invoke(query) if hasattr(self.db_retriever, "invoke") else []
        if not isinstance(db_docs, list):
            db_docs = []

        # Limit DB docs
        db_docs = db_docs[:k_db]

        # Retrieve analysis document only if requested and available
        analysis_docs = []
        if use_analysis and self.analysis_retriever:
            try:
                analysis_docs = (
                    self.analysis_retriever.invoke(query)
                    if hasattr(self.analysis_retriever, "invoke")
                    else []
                )
                if not isinstance(analysis_docs, list):
                    analysis_docs = []
                # Limit analysis docs
                analysis_docs = analysis_docs[:k_analysis]
            except Exception as e:
                logger.warning(f"Failed to retrieve analysis documents: {e}")
                analysis_docs = []

        # Priority logic: if prefer_db_for_factual and we have DB docs, prioritize them
        if self.prefer_db_for_factual and db_docs:
            # Put DB docs first, then analysis
            all_docs = db_docs + analysis_docs
        else:
            # Combine based on relevance (analysis might be more relevant for some queries)
            all_docs = db_docs + analysis_docs

        context_metadata = {
            "db_doc_count": len(db_docs),
            "analysis_doc_count": len(analysis_docs),
            "total_doc_count": len(all_docs),
            "prefer_db": self.prefer_db_for_factual,
        }

        return all_docs, context_metadata

    def format_context(self, documents: List) -> str:
        """
        Format retrieved documents into context string.

        Maintains separation between DB facts and analysis document.

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted context string
        """
        if not documents:
            return "Няма налична информация за тази заявка."

        context_parts = []
        db_parts = []
        analysis_parts = []

        for doc in documents:
            metadata = getattr(doc, "metadata", {}) if hasattr(doc, "metadata") else {}
            source = metadata.get("source", "unknown")
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)

            if source == "database":
                db_parts.append(content)
            elif source == "analysis_document":
                analysis_parts.append(content)
            else:
                # Unknown source, add to DB parts as fallback
                db_parts.append(content)

        # Format with clear separation
        if db_parts:
            context_parts.append("=== ДАННИ ОТ БАЗА ДАННИ ===\n")
            for i, part in enumerate(db_parts, 1):
                context_parts.append(f"[Документ {i}]\n{part}\n")

        if analysis_parts:
            context_parts.append("\n=== АНАЛИЗЕН ДОКУМЕНТ ===\n")
            for i, part in enumerate(analysis_parts, 1):
                context_parts.append(f"[Анализ {i}]\n{part}\n")

        return "\n".join(context_parts)


class RAGChainService:
    """
    RAG chain service using LangChain with custom context assembly.

    This service maintains full control over context assembly while using
    LangChain for orchestration.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        db_retriever: Optional[BaseRetriever] = None,
        analysis_retriever: Optional[BaseRetriever] = None,
        prefer_db_for_factual: bool = True,
    ):
        """
        Initialize RAG chain service.

        Args:
            llm: Optional LLM instance. If None, creates one from settings.
            db_retriever: Optional retriever for DB content. If None, creates default.
            analysis_retriever: Optional retriever for analysis document. If None, creates default with filter.
            prefer_db_for_factual: If True, prioritize DB content for factual queries
        """
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain dependencies are required for RAGChainService.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-openai langchain-community langchain-chroma"
            ) from _LANGCHAIN_IMPORT_ERROR

        self.llm = llm or get_default_llm()
        self.prefer_db_for_factual = prefer_db_for_factual

        # Create retrievers if not provided
        if db_retriever is None:
            factory = LangChainChromaFactory()
            vectorstore = factory.get_vectorstore()
            # Add metadata filter for database content
            db_retriever = vectorstore.as_retriever(
                search_kwargs={"k": 4, "filter": {"source": "database"}}
            )

        if analysis_retriever is None:
            factory = LangChainChromaFactory()
            vectorstore = factory.get_vectorstore()
            # Add metadata filter for analysis document
            analysis_retriever = vectorstore.as_retriever(
                search_kwargs={"k": 2, "filter": {"source": "analysis_document"}}
            )

        self.db_retriever = db_retriever
        self.analysis_retriever = analysis_retriever

        # Create context assembler
        self.context_assembler = ContextAssembler(
            db_retriever=self.db_retriever,
            analysis_retriever=self.analysis_retriever,
            prefer_db_for_factual=self.prefer_db_for_factual,
        )

        # Create Bulgarian prompt template
        self.prompt_template = self._create_bulgarian_prompt()

        # Build the chain
        self.chain = self._build_chain()

    def _create_bulgarian_prompt(self) -> ChatPromptTemplate:
        """Create Bulgarian prompt template for RAG."""
        system_prompt = (
            "Ти си помощник за система за данни за читалища в България.\n"
            "Твоята задача е да отговориш на въпроси на базата на предоставения контекст.\n"
            "\n"
            "ВАЖНИ ПРАВИЛА:\n"
            "1. Отговаряй САМО на базата на предоставения контекст. Не измисляй факти.\n"
            "2. Ако контекстът не съдържа информация за заявката, кажи честно че нямаш информация.\n"
            "3. Разграничавай между факти от базата данни и информация от анализите.\n"
            "4. За фактически въпроси (брой, статистика, данни), използвай предимно информацията от базата данни.\n"
            "5. За обяснения и контекст, можеш да използваш и анализите.\n"
            "6. Отговори на български език.\n"
            "7. Бъди точен и конкретен.\n"
            "\n"
            "Контекст:\n"
            "{context}\n"
            "\n"
            "Въпрос: {question}\n"
            "\n"
            "Отговор:"
        )

        # Note: The system prompt includes {context} and {question} placeholders
        # We'll format it manually in the chain
        return ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{question}"),
            ]
        )

    def _build_chain(self):
        """
        Build the RAG chain with custom context assembly.

        We use a custom chain that:
        1. Retrieves documents using our context assembler
        2. Formats context with separation between DB and analysis
        3. Passes formatted context to LLM via prompt
        """
        # Create a custom chain that uses our context assembler
        def retrieve_and_format(inputs: Dict[str, str]) -> Dict[str, str]:
            """Retrieve documents and format context."""
            query = inputs.get("question", inputs.get("query", ""))
            use_analysis = inputs.get("use_analysis", True)

            # Retrieve and assemble context
            documents, metadata = self.context_assembler.assemble_context(
                query, k_db=4, k_analysis=2, use_analysis=use_analysis
            )

            # Format context
            formatted_context = self.context_assembler.format_context(documents)

            return {
                "context": formatted_context,
                "question": query,
                "metadata": metadata,
            }

        # Create chain: retrieve -> format -> prompt -> LLM
        # The prompt template expects "context" and "question" keys
        # retrieve_and_format returns a dict with these keys
        chain = (
            RunnablePassthrough()
            | retrieve_and_format
            | self.prompt_template
            | self.llm
        )

        return chain

    def query(self, question: str, use_analysis: bool = True) -> Dict[str, any]:
        """
        Query the RAG chain.

        Args:
            question: User question in Bulgarian
            use_analysis: Whether to include analysis documents

        Returns:
            Dictionary with answer and metadata
        """
        # Invoke the chain with use_analysis parameter
        result = self.chain.invoke({"question": question, "use_analysis": use_analysis})

        # Extract answer from result
        if hasattr(result, "content"):
            answer = result.content
        elif isinstance(result, str):
            answer = result
        else:
            answer = str(result)

        # Get context metadata by retrieving again
        # (The chain doesn't preserve metadata in the final output)
        _, metadata = self.context_assembler.assemble_context(
            question, k_db=4, k_analysis=2, use_analysis=use_analysis
        )

        return {
            "answer": answer,
            "metadata": metadata,
            "question": question,
        }

    def query_with_context(self, question: str, use_analysis: bool = True) -> Dict[str, any]:
        """
        Query the RAG chain and return full context information.

        Args:
            question: User question in Bulgarian
            use_analysis: Whether to include analysis documents

        Returns:
            Dictionary with answer, context, and metadata
        """
        # Retrieve documents
        documents, metadata = self.context_assembler.assemble_context(
            question, k_db=4, k_analysis=2, use_analysis=use_analysis
        )

        # Format context
        formatted_context = self.context_assembler.format_context(documents)

        # Get answer using the chain
        result = self.query(question, use_analysis=use_analysis)

        # Add context information
        result["context"] = formatted_context
        result["retrieved_documents"] = [
            {
                "content": doc.page_content if hasattr(doc, "page_content") else str(doc),
                "metadata": doc.metadata if hasattr(doc, "metadata") else {},
            }
            for doc in documents
        ]

        return result


def get_rag_chain_service(
    llm: Optional[BaseChatModel] = None,
    prefer_db_for_factual: bool = True,
) -> RAGChainService:
    """
    Factory function to get a default RAGChainService.

    Args:
        llm: Optional LLM instance. If None, creates one from settings.
        prefer_db_for_factual: If True, prioritize DB content for factual queries

    Returns:
        RAGChainService instance
    """
    return RAGChainService(
        llm=llm,
        prefer_db_for_factual=prefer_db_for_factual,
    )

