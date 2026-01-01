"""RAG (Retrieval-Augmented Generation) chain using LangChain."""

import logging
import time
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.metrics import track_rag_query
from app.rag.langchain_integration import LangChainChromaFactory, get_langchain_retriever
from app.rag.llm_intent_classification import get_default_llm
from app.rag.hallucination_control import (
    HallucinationConfig,
    HallucinationMode,
    PromptEnhancer,
    get_default_hallucination_config,
)

logger = logging.getLogger(__name__)

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
    from langchain_core.retrievers import BaseRetriever
    from langchain_core.runnables import RunnablePassthrough
except ImportError as _e:  # pragma: no cover - guarded by tests
    BaseCallbackHandler = object  # type: ignore[assignment]
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
        self, query: str, k_db: int = 4, k_analysis: int = 4, use_analysis: bool = True
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
        hallucination_config: Optional[HallucinationConfig] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
    ):
        """
        Initialize RAG chain service.

        Args:
            llm: Optional LLM instance. If None, creates one from settings.
            db_retriever: Optional retriever for DB content. If None, creates default.
            analysis_retriever: Optional retriever for analysis document. If None, creates default with filter.
            prefer_db_for_factual: If True, prioritize DB content for factual queries
            hallucination_config: Optional hallucination control configuration. If None, uses default (MEDIUM_TOLERANCE).
            callbacks: Optional list of LangChain callback handlers for observability.
        """
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain dependencies are required for RAGChainService.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-openai langchain-community langchain-chroma"
            ) from _LANGCHAIN_IMPORT_ERROR

        self.hallucination_config = hallucination_config or get_default_hallucination_config()

        # Configure LLM with hallucination settings
        base_llm = llm or get_default_llm()
        self.llm = self.hallucination_config.get_llm_with_config(base_llm)

        # Create fallback LLM for retry (more powerful model)
        self.fallback_llm = None
        if settings.rag_enable_fallback:
            try:
                from app.rag.llm_registry import LLMRegistry, LLMTask
                registry = LLMRegistry()
                fallback_provider = (
                    settings.llm_provider_fallback.lower()
                    if settings.llm_provider_fallback
                    else settings.llm_provider.lower()
                )
                # Get fallback model name based on provider
                if fallback_provider == "openai":
                    fallback_model = settings.openai_chat_model_fallback
                elif fallback_provider == "tgi":
                    fallback_model = settings.tgi_model_name
                else:
                    fallback_model = None

                self.fallback_llm = registry.get_llm(
                    task=LLMTask.GENERATION,
                    provider=fallback_provider,
                    model_name=fallback_model,
                )
                self.fallback_llm = self.hallucination_config.get_llm_with_config(self.fallback_llm)
                logger.info(f"Fallback LLM configured: {fallback_provider}/{fallback_model}")
            except Exception as e:
                logger.warning(f"Failed to initialize fallback LLM: {e}. Fallback retry will be disabled.")
                self.fallback_llm = None

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
            # Increased k from 2 to 4 to improve semantic retrieval coverage
            analysis_retriever = vectorstore.as_retriever(
                search_kwargs={"k": 4, "filter": {"source": "analysis_document"}}
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

        # Store callbacks (default to structured logging callback if not provided)
        if callbacks is None:
            callbacks = [get_langchain_callback_handler()]
        self.callbacks = callbacks

        # Build the chain
        self.chain = self._build_chain()

    def _create_bulgarian_prompt(self) -> ChatPromptTemplate:
        """Create Bulgarian prompt template for RAG with hallucination control."""
        base_system_prompt = (
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

        # Enhance prompt with hallucination control instructions
        return PromptEnhancer.enhance_rag_prompt(base_system_prompt, self.hallucination_config)

    def _build_chain(self):
        """
        Build the RAG chain with custom context assembly.

        We use a custom chain that:
        1. Retrieves documents using our context assembler
        2. Formats context with separation between DB and analysis
        3. Passes formatted context to LLM via prompt
        """
        # Create chain: retrieve -> format -> prompt -> LLM
        # The prompt template expects "context" and "question" keys
        # retrieve_and_format returns a dict with these keys
        chain = (
            RunnablePassthrough()
            | self._create_retrieve_and_format(use_analysis=True)
            | self.prompt_template
            | self.llm
        )

        return chain

    def _is_no_information_response(self, answer: str) -> bool:
        """
        Check if the answer indicates no information was found.

        Args:
            answer: The generated answer

        Returns:
            True if the answer indicates no information was found
        """
        answer_lower = answer.lower().strip()
        # Check for common "no information" patterns in Bulgarian
        no_info_patterns = [
            "нямам информация",
            "няма информация",
            "не мога да намеря",
            "не мога да отговоря",
            "не знам",
            "няма данни",
            "липсва информация",
        ]
        return any(pattern in answer_lower for pattern in no_info_patterns)

    def query(self, question: str, use_analysis: bool = True, enable_fallback: bool = True) -> Dict[str, any]:
        """
        Query the RAG chain with optional fallback retry using more powerful LLM.

        Args:
            question: User question in Bulgarian
            use_analysis: Whether to include analysis documents
            enable_fallback: Whether to enable fallback retry with more powerful LLM.
                           Should be True for RAG-only queries, False for hybrid queries.

        Returns:
            Dictionary with answer and metadata
        """
        start_time = time.time()
        status = "success"
        documents_retrieved = 0
        used_fallback = False

        try:
            # Invoke the chain with use_analysis parameter and callbacks
            config = {"callbacks": self.callbacks} if self.callbacks else {}
            result = self.chain.invoke(
                {"question": question, "use_analysis": use_analysis},
                config=config,
            )

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
                question, k_db=4, k_analysis=4, use_analysis=use_analysis
            )

            # Extract document count for metrics
            documents_retrieved = metadata.get("total_documents", 0)

            # Check if answer indicates no information and fallback is enabled
            # Only use fallback for RAG-only queries (not hybrid queries where SQL might provide answers)
            if (
                self._is_no_information_response(answer)
                and self.fallback_llm is not None
                and settings.rag_enable_fallback
                and enable_fallback
            ):
                logger.info(
                    f"Initial answer indicates no information. Retrying with fallback LLM for question: {question}"
                )
                # Retry with fallback LLM
                try:
                    # Create a new chain with fallback LLM
                    fallback_chain = (
                        RunnablePassthrough()
                        | self._create_retrieve_and_format(use_analysis)
                        | self.prompt_template
                        | self.fallback_llm
                    )

                    fallback_result = fallback_chain.invoke(
                        {"question": question, "use_analysis": use_analysis},
                        config=config,
                    )

                    # Extract fallback answer
                    if hasattr(fallback_result, "content"):
                        fallback_answer = fallback_result.content
                    elif isinstance(fallback_result, str):
                        fallback_answer = fallback_result
                    else:
                        fallback_answer = str(fallback_result)

                    # Only use fallback answer if it's different from "no information"
                    if not self._is_no_information_response(fallback_answer):
                        answer = fallback_answer
                        used_fallback = True
                        logger.info("Fallback LLM provided a better answer")
                    else:
                        logger.info("Fallback LLM also returned no information")
                except Exception as e:
                    logger.warning(f"Fallback LLM retry failed: {e}. Using original answer.")

            # Add metadata about fallback usage
            metadata["used_fallback_llm"] = used_fallback

            return {
                "answer": answer,
                "metadata": metadata,
                "question": question,
            }
        except Exception as e:
            status = "error"
            raise
        finally:
            # Track RAG query metrics
            duration = time.time() - start_time
            track_rag_query(status=status, duration=duration, documents_retrieved=documents_retrieved)

    def _create_retrieve_and_format(self, use_analysis: bool):
        """Create retrieve_and_format function for chain."""
        def retrieve_and_format(inputs: Dict[str, str]) -> Dict[str, str]:
            """Retrieve documents and format context."""
            query = inputs.get("question", inputs.get("query", ""))

            # Retrieve and assemble context
            documents, metadata = self.context_assembler.assemble_context(
                query, k_db=4, k_analysis=4, use_analysis=use_analysis
            )

            # Format context
            formatted_context = self.context_assembler.format_context(documents)

            return {
                "context": formatted_context,
                "question": query,
                "metadata": metadata,
            }
        return retrieve_and_format

    def query_with_context(self, question: str, use_analysis: bool = True, enable_fallback: bool = True) -> Dict[str, any]:
        """
        Query the RAG chain and return full context information.

        Args:
            question: User question in Bulgarian
            use_analysis: Whether to include analysis documents
            enable_fallback: Whether to enable fallback retry with more powerful LLM

        Returns:
            Dictionary with answer, context, and metadata
        """
        # Retrieve documents
        documents, metadata = self.context_assembler.assemble_context(
            question, k_db=4, k_analysis=4, use_analysis=use_analysis
        )

        # Format context
        formatted_context = self.context_assembler.format_context(documents)

        # Get answer using the chain
        result = self.query(question, use_analysis=use_analysis, enable_fallback=enable_fallback)

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
    hallucination_config: Optional[HallucinationConfig] = None,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
) -> RAGChainService:
    """
    Factory function to get a default RAGChainService.

    Args:
        llm: Optional LLM instance. If None, creates one from settings.
        prefer_db_for_factual: If True, prioritize DB content for factual queries
        hallucination_config: Optional hallucination control configuration
        callbacks: Optional list of LangChain callback handlers

    Returns:
        RAGChainService instance
    """
    return RAGChainService(
        llm=llm,
        prefer_db_for_factual=prefer_db_for_factual,
        hallucination_config=hallucination_config,
        callbacks=callbacks,
    )

