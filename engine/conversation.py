from typing import List, Optional

from models.agent_definition import AgentDefinition
from models.chat import ChatMessage
from engine.prompt_builder import PromptBuilder
from llm.gemini_client import GeminiClient


class ConversationManager:
    def __init__(
        self,
        definition: AgentDefinition,
        gemini_client: Optional[GeminiClient] = None,
    ):
        self.definition = definition
        self.client = gemini_client or GeminiClient()
        self.history: List[ChatMessage] = []
        self.system_prompt = ""
        self.tool_results = {}

    def initialize(self, system_prompt: str, initial_response: str, tool_results: dict = None):
        self.system_prompt = system_prompt
        self.tool_results = tool_results or {}
        self.history.append(ChatMessage(role="agent", content=initial_response))

    def followup(self, user_message: str) -> str:
        self.history.append(ChatMessage(role="user", content=user_message))

        history_dicts = [{"role": m.role, "content": m.content} for m in self.history]

        response = self.client.send_with_context(
            self.system_prompt,
            user_message,
            history_dicts,
        )

        self.history.append(ChatMessage(role="agent", content=response))
        return response

    def get_history(self) -> List[ChatMessage]:
        return list(self.history)

    def clear(self):
        self.history.clear()
        self.system_prompt = ""
        self.tool_results = {}
