from typing import List, Optional, Dict

from models.agent_definition import AgentDefinition
from models.chat import ChatMessage
from engine.cache import ResponseCache
from llm.gemini_client import GeminiClient


class ConversationManager:
    """Multi-turn conversation manager for an agent session.

    Maintains chat history and context so the agent can have coherent
    follow-up conversations after the initial run. Falls back to cached
    responses when the API is unavailable.
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
        self._inputs: Dict[str, str] = {}
        self.cache = ResponseCache()

    def initialize(
        self,
        system_prompt: str,
        initial_response: str,
        tool_results: Optional[Dict[str, str]] = None,
        inputs: Optional[Dict[str, str]] = None,
    ):
        """Initialize the conversation with the agent's first response."""
        self.system_prompt = system_prompt
        self.tool_results = tool_results or {}
        self._inputs = inputs or {}
        self.history.clear()
        self.history.append(ChatMessage(role="agent", content=initial_response))

    def followup(self, user_message: str) -> str:
        """Send a follow-up message and get the agent's response.

        Falls back to cached follow-up responses when the API fails.
        """
        self.history.append(ChatMessage(role="user", content=user_message))

        history_dicts = [
            {"role": m.role, "content": m.content}
            for m in self.history[:-1]
        ]

        response = self.client.send_with_context(
            self.system_prompt,
            user_message,
            history_dicts,
        )

        if response.startswith("[Error"):
            cached = self.cache.get_cached_followup(
                self.definition.id, self._inputs, user_message
            )
            if cached:
                response = cached

        self.history.append(ChatMessage(role="agent", content=response))
        return response

    def get_history(self) -> List[ChatMessage]:
        return list(self.history)

    def get_history_dicts(self) -> List[dict]:
        return [m.to_dict() for m in self.history]

    def clear(self):
        self.history.clear()
        self.system_prompt = ""
        self.tool_results = {}
        self._inputs = {}

    @property
    def turn_count(self) -> int:
        return sum(1 for m in self.history if m.role == "user")

    @property
    def is_active(self) -> bool:
        return len(self.history) > 0 and self.system_prompt != ""
