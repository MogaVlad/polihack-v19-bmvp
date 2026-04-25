from typing import List, Optional, Dict

from models.agent_definition import AgentDefinition
from models.chat import ChatMessage
from engine.prompt_builder import PromptBuilder
from llm.gemini_client import GeminiClient


class ConversationManager:
    """Multi-turn conversation manager for an agent session.

    Maintains chat history and context so the agent can have coherent
    follow-up conversations after the initial run.
    """

    def __init__(
        self,
        definition: AgentDefinition,
        gemini_client: Optional[GeminiClient] = None,
    ):
        self.definition = definition
        self.client = gemini_client or GeminiClient()
        self.history: List[ChatMessage] = []
        self.system_prompt = ""
        self.tool_results: Dict[str, str] = {}

    def initialize(
        self,
        system_prompt: str,
        initial_response: str,
        tool_results: Optional[Dict[str, str]] = None,
    ):
        """Initialize the conversation with the agent's first response.

        Called after AgentRunner.run_agent() completes.
        """
        self.system_prompt = system_prompt
        self.tool_results = tool_results or {}
        self.history.clear()
        self.history.append(ChatMessage(role="agent", content=initial_response))

    def followup(self, user_message: str) -> str:
        """Send a follow-up message and get the agent's response.

        Preserves full conversation history and agent context.
        """
        self.history.append(ChatMessage(role="user", content=user_message))

        # Build history in the format expected by the Gemini client
        history_dicts = [
            {"role": m.role, "content": m.content}
            for m in self.history[:-1]  # Exclude the message we're about to send
        ]

        response = self.client.send_with_context(
            self.system_prompt,
            user_message,
            history_dicts,
        )

        self.history.append(ChatMessage(role="agent", content=response))
        return response

    def get_history(self) -> List[ChatMessage]:
        """Return a copy of the conversation history."""
        return list(self.history)

    def get_history_dicts(self) -> List[dict]:
        """Return history as a list of dicts (for serialization)."""
        return [m.to_dict() for m in self.history]

    def clear(self):
        """Reset the conversation state."""
        self.history.clear()
        self.system_prompt = ""
        self.tool_results = {}

    @property
    def turn_count(self) -> int:
        """Number of conversation turns (user messages)."""
        return sum(1 for m in self.history if m.role == "user")

    @property
    def is_active(self) -> bool:
        """Whether a conversation has been initialized."""
        return len(self.history) > 0 and self.system_prompt != ""
