import json
import re
import threading
from typing import Callable, Dict, Optional

from models.agent_definition import AgentDefinition
from models.chat import AgentResult
from engine.prompt_builder import PromptBuilder
from llm.gemini_client import GeminiClient
from tools.registry import ToolRegistry


class AgentRunner:
    """Core agent execution engine.

    Orchestrates: tool execution → prompt assembly → LLM call → output parsing.
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()
        self.prompt_builder = PromptBuilder()
        self.registry = ToolRegistry()

    def run_agent(
        self,
        definition: AgentDefinition,
        inputs: Dict[str, str],
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> AgentResult:
        """Execute an agent: run tools → build prompt → call LLM → parse output.

        Args:
            definition: The agent definition to execute.
            inputs: User-provided inputs as {name: value} strings.
            status_callback: Optional callback for progress updates.

        Returns:
            AgentResult with outputs, explanation, and tool results.
        """
        def _status(msg: str):
            if status_callback:
                status_callback(msg)

        # Step 1: Run requested tools
        _status("Running tools...")
        tool_results = {}
        for tool_name in definition.tools:
            tool_fn = self.registry.get_tool(tool_name)
            if tool_fn:
                _status(f"Running tool: {tool_name}...")
                try:
                    # Build tool input — pass the raw inputs dict
                    # Tools expect a dict; for floor plan tools, pass the parsed JSON
                    tool_input = self._prepare_tool_input(inputs)
                    result = tool_fn(tool_input)
                    tool_results[tool_name] = json.dumps(result, default=str, indent=2)
                except Exception as e:
                    tool_results[tool_name] = f"[Tool error: {e}]"

        # Step 2: Build prompts
        _status("Assembling prompt...")
        system_prompt = self.prompt_builder.build_system_prompt(definition, tool_results)
        user_prompt = self.prompt_builder.build_user_prompt(inputs)

        # Step 3: Call LLM
        _status("Calling LLM...")
        response = self.client.send_with_context(system_prompt, user_prompt)

        # Step 4: Parse structured output from response
        _status("Parsing output...")
        parsed_outputs = self._parse_outputs(response, definition)

        # Step 5: Build result
        success = not response.startswith("[Error")

        _status("Done" if success else "Error occurred")

        return AgentResult(
            agent_id=definition.id,
            success=success,
            outputs=parsed_outputs,
            explanation=response,
            tool_results=tool_results,
        )

    def run_agent_async(
        self,
        definition: AgentDefinition,
        inputs: Dict[str, str],
        callback: Callable[[AgentResult], None],
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> threading.Thread:
        """Run agent in a background thread. Calls `callback` with the result.

        Returns the thread so the caller can check if it's still running.
        """
        def _run():
            try:
                result = self.run_agent(definition, inputs, status_callback)
                callback(result)
            except Exception as e:
                error_result = AgentResult(
                    agent_id=definition.id,
                    success=False,
                    error=str(e),
                )
                callback(error_result)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def _prepare_tool_input(self, inputs: Dict[str, str]) -> dict:
        """Prepare tool input by parsing JSON strings from user inputs."""
        tool_input = {}
        for key, value in inputs.items():
            # Try to parse JSON values (floor plans, violation lists, etc.)
            try:
                parsed = json.loads(value)
                tool_input.update(parsed) if isinstance(parsed, dict) else tool_input.__setitem__(key, parsed)
            except (json.JSONDecodeError, TypeError):
                tool_input[key] = value
        return tool_input

    def _parse_outputs(self, response: str, definition: AgentDefinition) -> dict:
        """Attempt to extract structured JSON from LLM response."""
        outputs = {"response": response}

        # Try to extract JSON blocks from the response
        json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', response)

        if json_blocks:
            # Map extracted JSON blocks to expected output names
            json_output_names = [o.name for o in definition.outputs if o.type == "json"]
            for i, block in enumerate(json_blocks):
                try:
                    parsed = json.loads(block)
                    if i < len(json_output_names):
                        outputs[json_output_names[i]] = parsed
                    else:
                        outputs[f"json_output_{i}"] = parsed
                except json.JSONDecodeError:
                    continue

        return outputs
