import json
import re
import threading
from typing import Callable, Dict, Optional

from models.agent_definition import AgentDefinition
from models.chat import AgentResult
from engine.prompt_builder import PromptBuilder
from engine.cache import ResponseCache
from llm.gemini_client import GeminiClient
from tools.registry import ToolRegistry


class AgentRunner:
    """Core agent execution engine.

    Orchestrates: tool execution -> prompt assembly -> LLM call -> output parsing.
    Falls back to cached responses when the API is unavailable.
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.client = gemini_client or GeminiClient()
        self.prompt_builder = PromptBuilder()
        self.registry = ToolRegistry()
        self.cache = ResponseCache()
        self.cache_validation_report = self.cache.validate_all_cached_responses()

    def run_agent(
        self,
        definition: AgentDefinition,
        inputs: Dict[str, str],
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> AgentResult:
        """Execute an agent: run tools -> build prompt -> call LLM -> parse output.

        Falls back to cached responses if the LLM call fails.
        """
        def _status(msg: str):
            if status_callback:
                status_callback(msg)

        _status("Running tools...")
        tool_results = self._run_tools(definition, inputs, _status)

        _status("Assembling prompt...")
        system_prompt = self.prompt_builder.build_system_prompt(definition, tool_results)
        user_prompt = self.prompt_builder.build_user_prompt(inputs)

        _status("Calling LLM...")
        response = self.client.send_with_context(
            system_prompt,
            user_prompt,
            status_callback=_status,
            timeout_seconds=GeminiClient.REQUEST_TIMEOUT_SECONDS,
        )

        if self._is_error(response):
            if "timeout" in response.lower():
                _status("LLM timed out — checking cache...")
            else:
                _status("LLM unavailable, checking cache...")
            cached = self.cache.get_cached_result(definition.id, inputs)
            if cached:
                _status("Loaded cached response")
                cached.tool_results = tool_results
                if not cached.outputs or cached.outputs == {}:
                    cached.outputs = self._parse_outputs(
                        cached.explanation, definition,
                    )
                return cached
            if "timeout" in response.lower():
                _status("Timeout — no cached fallback available")
            else:
                _status("Error — no cached fallback available")
            return AgentResult(
                agent_id=definition.id,
                success=False,
                outputs={"response": response},
                explanation=response,
                tool_results=tool_results,
                error=response,
            )

        _status("Parsing output...")
        parsed_outputs = self._parse_outputs(response, definition)

        _status("Done")
        return AgentResult(
            agent_id=definition.id,
            success=True,
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
        """Run agent in a background thread. Calls callback with the result."""
        def _run():
            try:
                result = self.run_agent(definition, inputs, status_callback)
                callback(result)
            except Exception as e:
                callback(AgentResult(
                    agent_id=definition.id,
                    success=False,
                    error=str(e),
                ))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def _run_tools(
        self,
        definition: AgentDefinition,
        inputs: Dict[str, str],
        _status: Callable[[str], None],
    ) -> Dict[str, str]:
        tool_results = {}
        tool_input = self._prepare_tool_input(inputs)

        for tool_name in definition.tools:
            tool_fn = self.registry.get_tool(tool_name)
            if not tool_fn:
                continue
            _status(f"Running tool: {tool_name}...")
            try:
                result = tool_fn(tool_input)
                tool_results[tool_name] = json.dumps(result, default=str, indent=2)
            except Exception as e:
                tool_results[tool_name] = json.dumps({"error": str(e)})

        return tool_results

    def _prepare_tool_input(self, inputs: Dict[str, str]) -> dict:
        """Parse JSON strings from user inputs into a merged dict for tools."""
        tool_input = {}
        for key, value in inputs.items():
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    tool_input.update(parsed)
                else:
                    tool_input[key] = parsed
            except (json.JSONDecodeError, TypeError):
                tool_input[key] = value
        return tool_input

    def _parse_outputs(self, response: str, definition: AgentDefinition) -> dict:
        """Extract structured JSON from LLM response."""
        outputs = {"response": response}

        # Find all markdown blocks, or just use the response if no blocks exist
        blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
        if not blocks:
            blocks = [response]

        parsed_objects = []
        for block in blocks:
            b = block.strip()
            # If it looks like JSON, try to parse it
            if b.startswith("{") or b.startswith("["):
                try:
                    parsed_objects.append(json.loads(b))
                except json.JSONDecodeError:
                    continue

        json_output_names = [o.name for o in definition.outputs if o.type == "json"]
        used_objects = set()

        # 1. Look for overarching dictionaries that contain the requested keys
        for i, obj in enumerate(parsed_objects):
            if isinstance(obj, dict):
                matched = False
                for name in json_output_names:
                    if name in obj and name not in outputs:
                        outputs[name] = obj[name]
                        matched = True
                if matched:
                    used_objects.add(i)

        # 2. Assign any remaining requested outputs in order from unused objects
        remaining_names = [n for n in json_output_names if n not in outputs]
        unused_objects = [obj for i, obj in enumerate(parsed_objects) if i not in used_objects]

        for name, obj in zip(remaining_names, unused_objects):
            outputs[name] = obj

        # 3. Put any leftover unused objects into generic keys
        leftovers = unused_objects[len(remaining_names):]
        for i, obj in enumerate(leftovers):
            outputs[f"json_output_{i}"] = obj

        return outputs

    @staticmethod
    def _is_error(response: str) -> bool:
        if not response:
            return True
        return response.startswith("[Error")
