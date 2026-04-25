from typing import List, Optional, Dict, Callable

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

    MAX_TURNS = 10

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
        self._last_user_message: Optional[str] = None
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

    @staticmethod
    def _is_timeout_error(response: str) -> bool:
        return response.startswith("[Error") and "timeout" in response.lower()

    def followup(
        self,
        user_message: str,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Send a follow-up message and get the agent's response.

        Falls back to cached follow-up responses when the API fails.
        Enforces max conversation depth to keep context coherent.
        """
        if self.turn_count >= self.MAX_TURNS:
            limit_msg = (
                f"We have reached the conversation limit ({self.MAX_TURNS} follow-ups). "
                f"Please start a new session if you have more questions."
            )
            self.history.append(ChatMessage(role="user", content=user_message))
            self.history.append(ChatMessage(role="agent", content=limit_msg))
            return limit_msg

        self.history.append(ChatMessage(role="user", content=user_message))
        self._last_user_message = user_message

        history_dicts = [
            {"role": m.role, "content": m.content}
            for m in self.history[:-1]
        ]

        response = self.client.send_with_context(
            self.system_prompt,
            user_message,
            history_dicts,
            status_callback=status_callback,
            timeout_seconds=GeminiClient.REQUEST_TIMEOUT_SECONDS,
        )

        if response.startswith("[Error"):
            cached = self.cache.get_cached_followup(
                self.definition.id, self._inputs, user_message
            )
            if cached:
                response = cached
            elif self._is_timeout_error(response):
                response = (
                    "The API request timed out after 30s. "
                    "Please click Retry to resend your last follow-up."
                )
            else:
                response = (
                    "The API is currently unavailable. "
                    "Please try again in a moment or click Retry."
                )

        self.history.append(ChatMessage(role="agent", content=response))
        return response

    def retry_last_followup(
        self,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[str]:
        if not self._last_user_message:
            return None
        if len(self.history) >= 2:
            last = self.history[-1]
            second_last = self.history[-2]
            if second_last.role == "user" and second_last.content == self._last_user_message:
                self.history.pop()
                self.history.pop()
        return self.followup(self._last_user_message, status_callback=status_callback)

    def get_history(self) -> List[ChatMessage]:
        return list(self.history)

    def get_history_dicts(self) -> List[dict]:
        return [m.to_dict() for m in self.history]

    def clear(self):
        self.history.clear()
        self.system_prompt = ""
        self.tool_results = {}
        self._inputs = {}
        self._last_user_message = None

    @property
    def turn_count(self) -> int:
        return sum(1 for m in self.history if m.role == "user")

    @property
    def is_active(self) -> bool:
        return len(self.history) > 0 and self.system_prompt != ""

    @property
    def last_user_message(self) -> Optional[str]:
        return self._last_user_message
