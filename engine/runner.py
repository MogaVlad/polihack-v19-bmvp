import json
from typing import Dict, Optional

from models.agent_definition import AgentDefinition
from models.chat import AgentResult
from engine.prompt_builder import PromptBuilder
from llm.gemini_client import GeminiClient
from tools.registry import ToolRegistry


class AgentRunner:
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()
        self.prompt_builder = PromptBuilder()
        self.registry = ToolRegistry()

    def run_agent(
        self,
        definition: AgentDefinition,
        inputs: Dict[str, str],
    ) -> AgentResult:
        tool_results = {}
        for tool_name in definition.tools:
            tool_fn = self.registry.get_tool(tool_name)
            if tool_fn:
                try:
                    result = tool_fn(inputs)
                    tool_results[tool_name] = json.dumps(result, default=str)
                except Exception as e:
                    tool_results[tool_name] = f"[Tool error: {e}]"

        system_prompt = self.prompt_builder.build_system_prompt(definition, tool_results)
        user_prompt = self.prompt_builder.build_user_prompt(inputs)

        response = self.client.send_with_context(system_prompt, user_prompt)

        return AgentResult(
            agent_id=definition.id,
            success=not response.startswith("[Error"),
            outputs={"response": response},
            explanation=response,
            tool_results=tool_results,
        )
