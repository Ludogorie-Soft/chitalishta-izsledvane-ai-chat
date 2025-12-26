"""Hybrid pipeline that combines SQL and RAG for comprehensive query answering."""

import structlog
from typing import Dict, List, Optional

from app.rag.hybrid_router import HybridIntentRouter, get_hybrid_router
from app.rag.intent_classification import QueryIntent
from app.rag.langchain_callbacks import get_langchain_callback_handler
from app.rag.rag_chain import RAGChainService, get_rag_chain_service
from app.rag.sql_agent import SQLAgentService, get_sql_agent_service
from app.rag.hallucination_control import (
    HallucinationConfig,
    HallucinationMode,
    PromptEnhancer,
    get_default_hallucination_config,
)

logger = structlog.get_logger(__name__)

try:
    from langchain_core.callbacks import BaseCallbackHandler
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.runnables import RunnablePassthrough
except ImportError as _e:  # pragma: no cover - guarded by tests
    BaseCallbackHandler = object  # type: ignore[assignment]
    BaseChatModel = object  # type: ignore[assignment]
    ChatPromptTemplate = object  # type: ignore[assignment]
    RunnablePassthrough = object  # type: ignore[assignment]
    _LANGCHAIN_IMPORT_ERROR = _e
else:
    _LANGCHAIN_IMPORT_ERROR = None


class SQLResultFormatter:
    """Formatter for converting SQL results into narrative text context."""

    @staticmethod
    def format_sql_result(sql_result: Dict[str, any]) -> str:
        """
        Convert SQL query result into narrative Bulgarian text.

        Args:
            sql_result: Result from SQLAgentService.query()

        Returns:
            Formatted narrative text in Bulgarian
        """
        if not sql_result.get("success", False):
            return f"SQL заявката не беше успешна: {sql_result.get('error', 'Неизвестна грешка')}"

        answer = sql_result.get("answer", "")
        sql_query = sql_result.get("sql_query", "")

        # Format as narrative context
        formatted = f"=== РЕЗУЛТАТИ ОТ БАЗА ДАННИ ===\n\n"

        if sql_query:
            formatted += f"Изпълнена SQL заявка: {sql_query}\n\n"

        formatted += f"Резултат:\n{answer}\n"

        return formatted

    @staticmethod
    def format_sql_results_for_rag(sql_results: List[Dict[str, any]]) -> str:
        """
        Format multiple SQL results for RAG context.

        Args:
            sql_results: List of SQL result dictionaries

        Returns:
            Combined formatted text
        """
        if not sql_results:
            return ""

        formatted_parts = []
        for i, result in enumerate(sql_results, 1):
            formatted_parts.append(f"[SQL Резултат {i}]\n{SQLResultFormatter.format_sql_result(result)}\n")

        return "\n".join(formatted_parts)


class HybridPipelineService:
    """
    Hybrid pipeline service that orchestrates SQL and RAG chains.

    This service uses the hybrid router to determine intent, then routes to
    SQL agent, RAG chain, or both, and combines results using LangChain.
    """

    def __init__(
        self,
        router: Optional[HybridIntentRouter] = None,
        sql_agent: Optional[SQLAgentService] = None,
        rag_chain: Optional[RAGChainService] = None,
        llm: Optional[BaseChatModel] = None,
        hallucination_config: Optional[HallucinationConfig] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
    ):
        """
        Initialize hybrid pipeline service.

        Args:
            router: Optional hybrid intent router. If None, creates default.
            sql_agent: Optional SQL agent service. If None, creates default.
            rag_chain: Optional RAG chain service. If None, creates default.
            llm: Optional LLM instance for final answer synthesis. If None, uses default.
            hallucination_config: Optional hallucination control configuration. If None, uses default (MEDIUM_TOLERANCE).
            callbacks: Optional list of LangChain callback handlers for observability.
        """
        if _LANGCHAIN_IMPORT_ERROR is not None:
            raise ImportError(
                "LangChain dependencies are required for HybridPipelineService.\n"
                "Install them with:\n"
                "  poetry add langchain langchain-openai langchain-community"
            ) from _LANGCHAIN_IMPORT_ERROR

        self.hallucination_config = hallucination_config or get_default_hallucination_config()

        # Store callbacks (default to structured logging callback if not provided)
        if callbacks is None:
            callbacks = [get_langchain_callback_handler()]
        self.callbacks = callbacks

        self.router = router or get_hybrid_router()
        self.sql_agent = sql_agent or get_sql_agent_service(
            hallucination_config=self.hallucination_config,
            callbacks=callbacks,
        )
        self.rag_chain = rag_chain or get_rag_chain_service(
            hallucination_config=self.hallucination_config,
            callbacks=callbacks,
        )

        # Configure synthesis LLM with hallucination settings
        base_llm = llm or self.rag_chain.llm
        self.llm = self.hallucination_config.get_llm_with_config(base_llm)

        # Create synthesis chain for combining SQL and RAG results
        self.synthesis_chain = self._create_synthesis_chain()

    def _create_synthesis_chain(self):
        """Create LangChain chain for synthesizing SQL and RAG results with hallucination control."""
        base_system_prompt = (
            "Ти си помощник за система за данни за читалища в България.\n"
            "Твоята задача е да комбинираш резултати от SQL заявки и RAG извличания "
            "в единен, кохерентен отговор на български език.\n"
            "\n"
            "ПРАВИЛА:\n"
            "1. Използвай SQL резултатите за точни числени данни и статистики.\n"
            "2. Използвай RAG контекста за обяснения, история и допълнителна информация.\n"
            "3. Не повтаряй информация - комбинирай я логично.\n"
            "4. Ако има противоречия, приоритизирай SQL резултатите за фактически данни.\n"
            "5. Отговорът трябва да бъде естествен и четим на български език.\n"
            "6. Структурирай отговора ясно: първо числа/статистика, после обяснения.\n"
            "\n"
            "SQL Резултати:\n"
            "{sql_results}\n"
            "\n"
            "RAG Контекст:\n"
            "{rag_context}\n"
            "\n"
            "Оригинален въпрос: {question}\n"
            "\n"
            "Създай единен отговор:"
        )

        # Enhance with hallucination control instructions
        enhanced_prompt = PromptEnhancer.enhance_synthesis_prompt(
            base_system_prompt, self.hallucination_config
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", enhanced_prompt),
                ("human", "{question}"),
            ]
        )

        # Create chain: prompt -> LLM
        chain = prompt | self.llm
        return chain

    def query(self, question: str) -> Dict[str, any]:
        """
        Process query through hybrid pipeline.

        Args:
            question: User question in Bulgarian

        Returns:
            Dictionary with answer, metadata, and execution details
        """
        # Step 1: Route query to determine intent
        routing_result = self.router.route(question)
        intent = routing_result.intent

        logger.info(
            "query_routed",
            intent=intent.value,
            confidence=routing_result.confidence,
            question=question[:200],  # Preview
        )

        # Step 2: Execute based on intent
        sql_result = None
        rag_result = None

        if intent == QueryIntent.SQL:
            # SQL-only query
            sql_result = self.sql_agent.query(question)
            final_answer = sql_result.get("answer", "Не мога да отговоря на този въпрос.")

        elif intent == QueryIntent.RAG:
            # RAG-only query - enable fallback retry with more powerful LLM
            rag_result = self.rag_chain.query(question, enable_fallback=True)
            final_answer = rag_result.get("answer", "Не мога да отговоря на този въпрос.")

        else:  # QueryIntent.HYBRID
            # Hybrid query - execute both and combine
            # Disable fallback for RAG in hybrid queries since SQL might provide answers
            sql_result = self.sql_agent.query(question)
            rag_result = self.rag_chain.query(question, use_analysis=True, enable_fallback=False)

            # Combine results using synthesis chain
            sql_formatted = SQLResultFormatter.format_sql_result(sql_result)
            rag_context = rag_result.get("context", rag_result.get("answer", ""))

            # Synthesize combined answer
            synthesis_input = {
                "sql_results": sql_formatted,
                "rag_context": rag_context,
                "question": question,
            }

            # Invoke synthesis chain with callbacks
            config = {"callbacks": self.callbacks} if self.callbacks else {}
            synthesis_output = self.synthesis_chain.invoke(synthesis_input, config=config)

            # Extract answer from synthesis
            if hasattr(synthesis_output, "content"):
                final_answer = synthesis_output.content
            elif isinstance(synthesis_output, str):
                final_answer = synthesis_output
            else:
                final_answer = str(synthesis_output)

        # Step 3: Prepare response
        response = {
            "answer": final_answer,
            "intent": intent.value,
            "routing_confidence": routing_result.confidence,
            "routing_explanation": routing_result.explanation,
            "question": question,
        }

        # Add execution details
        if sql_result:
            response["sql_executed"] = True
            response["sql_query"] = sql_result.get("sql_query")
            response["sql_success"] = sql_result.get("success", False)
        else:
            response["sql_executed"] = False

        if rag_result:
            response["rag_executed"] = True
            response["rag_metadata"] = rag_result.get("metadata", {})
        else:
            response["rag_executed"] = False

        return response

    def query_with_details(self, question: str) -> Dict[str, any]:
        """
        Process query and return detailed execution information.

        Args:
            question: User question in Bulgarian

        Returns:
            Dictionary with answer, full context, and execution details
        """
        # Get basic query result
        result = self.query(question)

        # Add detailed context if available
        routing_result = self.router.route(question)
        intent = routing_result.intent

        if intent == QueryIntent.HYBRID or intent == QueryIntent.RAG:
            # Get full RAG context
            rag_result = self.rag_chain.query_with_context(question)
            result["rag_context"] = rag_result.get("context", "")
            result["retrieved_documents"] = rag_result.get("retrieved_documents", [])

        if intent == QueryIntent.HYBRID or intent == QueryIntent.SQL:
            # Get SQL details
            sql_result = self.sql_agent.query(question)
            result["sql_formatted"] = SQLResultFormatter.format_sql_result(sql_result)

        return result


def get_hybrid_pipeline_service(
    router: Optional[HybridIntentRouter] = None,
    sql_agent: Optional[SQLAgentService] = None,
    rag_chain: Optional[RAGChainService] = None,
    llm: Optional[BaseChatModel] = None,
    hallucination_config: Optional[HallucinationConfig] = None,
    callbacks: Optional[List[BaseCallbackHandler]] = None,
) -> HybridPipelineService:
    """
    Factory function to get a default HybridPipelineService.

    Args:
        router: Optional hybrid intent router
        sql_agent: Optional SQL agent service
        rag_chain: Optional RAG chain service
        llm: Optional LLM instance for synthesis

    Returns:
        HybridPipelineService instance
    """
    return HybridPipelineService(
        router=router,
        sql_agent=sql_agent,
        rag_chain=rag_chain,
        llm=llm,
        hallucination_config=hallucination_config,
        callbacks=callbacks,
    )

