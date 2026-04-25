from models.agent_definition import AgentDefinition
from typing import Dict, Optional


class PromptBuilder:
    @staticmethod
    def build_system_prompt(
        definition: AgentDefinition,
        tool_results: Optional[Dict[str, str]] = None,
    ) -> str:
        lines = []
        lines.append(f"You are the '{definition.name}' agent.")
        lines.append(f"Goal: {definition.goal}")
        lines.append("")

        if definition.constraints:
            lines.append("CONSTRAINTS (you must respect these rules):")
            for i, c in enumerate(definition.constraints, 1):
                lines.append(f"  {i}. {c}")
            lines.append("")

        if definition.outputs:
            lines.append("EXPECTED OUTPUTS:")
            for o in definition.outputs:
                lines.append(f"  - {o.name} ({o.type}): {o.description}")
            lines.append("")

        if tool_results:
            lines.append("TOOL RESULTS (use these in your analysis):")
            for tool_name, result in tool_results.items():
                lines.append(f"  [{tool_name}]: {result}")
            lines.append("")

        if definition.conversational and definition.conversation_guidelines:
            lines.append(f"CONVERSATION GUIDELINES: {definition.conversation_guidelines}")
            lines.append("")

        lines.append("Provide structured, actionable output. Reference specific locations and measurements.")
        return "\n".join(lines)

    @staticmethod
    def build_user_prompt(inputs: Dict[str, str]) -> str:
        parts = []
        for name, value in inputs.items():
            parts.append(f"[{name}]:\n{value}")
        return "\n\n".join(parts)
