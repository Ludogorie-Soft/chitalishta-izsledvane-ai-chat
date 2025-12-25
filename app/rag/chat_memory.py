"""Chat memory management for conversation history."""

import logging
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ChatMemory:
    """
    Simple in-memory chat history manager.

    This is a flexible implementation that doesn't lock us into LangChain abstractions.
    For production, this could be replaced with a database-backed solution.
    """

    def __init__(self):
        """Initialize chat memory."""
        # In-memory storage: conversation_id -> list of messages
        self._conversations: Dict[str, List[Dict[str, str]]] = {}

    def create_conversation(self) -> str:
        """
        Create a new conversation and return its ID.

        Returns:
            Conversation ID (UUID string)
        """
        conversation_id = str(uuid4())
        self._conversations[conversation_id] = []
        logger.debug(f"Created new conversation: {conversation_id}")
        return conversation_id

    def add_message(
        self, conversation_id: str, role: str, content: str
    ) -> None:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content
        """
        if conversation_id not in self._conversations:
            # Create conversation if it doesn't exist
            self._conversations[conversation_id] = []

        self._conversations[conversation_id].append({
            "role": role,
            "content": content,
        })
        logger.debug(
            f"Added {role} message to conversation {conversation_id}"
        )

    def get_messages(
        self, conversation_id: str
    ) -> List[Dict[str, str]]:
        """
        Get all messages for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of messages (each with 'role' and 'content' keys)
        """
        return self._conversations.get(conversation_id, [])

    def get_conversation_context(
        self, conversation_id: str, max_messages: int = 10
    ) -> str:
        """
        Get conversation context as formatted string for LLM.

        Args:
            conversation_id: Conversation ID
            max_messages: Maximum number of recent messages to include

        Returns:
            Formatted conversation context string
        """
        messages = self.get_messages(conversation_id)
        if not messages:
            return ""

        # Get last N messages
        recent_messages = messages[-max_messages:]

        # Format as context
        context_parts = []
        for msg in recent_messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                context_parts.append(f"Потребител: {content}")
            elif role == "assistant":
                context_parts.append(f"Асистент: {content}")

        return "\n".join(context_parts)

    def clear_conversation(self, conversation_id: str) -> None:
        """
        Clear all messages from a conversation.

        Args:
            conversation_id: Conversation ID
        """
        if conversation_id in self._conversations:
            self._conversations[conversation_id] = []
            logger.debug(f"Cleared conversation {conversation_id}")

    def delete_conversation(self, conversation_id: str) -> None:
        """
        Delete a conversation entirely.

        Args:
            conversation_id: Conversation ID
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.debug(f"Deleted conversation {conversation_id}")

    def conversation_exists(self, conversation_id: str) -> bool:
        """
        Check if a conversation exists.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if conversation exists, False otherwise
        """
        return conversation_id in self._conversations


# Global memory instance
_global_memory: Optional[ChatMemory] = None


def get_chat_memory() -> ChatMemory:
    """
    Get the global chat memory instance.

    Returns:
        ChatMemory instance
    """
    global _global_memory
    if _global_memory is None:
        _global_memory = ChatMemory()
    return _global_memory



