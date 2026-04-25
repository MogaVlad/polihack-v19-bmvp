from models.agent_definition import AgentDefinition
from typing import Dict, Optional


class PromptBuilder:
    """Assembles LLM prompts from agent definitions, inputs, and tool results."""

    @staticmethod
    def build_system_prompt(
        definition: AgentDefinition,
        tool_results: Optional[Dict[str, str]] = None,
    ) -> str:
        lines = []

        lines.append(f"You are the '{definition.name}' agent on the AgentForge platform.")
        lines.append(f"Your goal: {definition.goal}")
        lines.append("")

        if definition.constraints:
            lines.append("CONSTRAINTS — You MUST respect these rules:")
            for i, c in enumerate(definition.constraints, 1):
                lines.append(f"  {i}. {c}")
            lines.append("")

        if definition.inputs:
            lines.append("EXPECTED INPUTS (the user will provide these):")
            for inp in definition.inputs:
                lines.append(f"  - {inp.name} ({inp.type}): {inp.description}")
            lines.append("")

        if definition.outputs:
            lines.append("EXPECTED OUTPUTS — produce ALL of these in your response:")
            json_outputs = []
            for o in definition.outputs:
                lines.append(f"  - {o.name} ({o.type}): {o.description}")
                if o.type == "json":
                    json_outputs.append(o.name)
            lines.append("")

            if json_outputs:
                lines.append("OUTPUT FORMAT INSTRUCTIONS:")
                lines.append("For each JSON output, wrap it in a ```json code block.")
                lines.append("Ensure the JSON is valid and parseable.")
                lines.append(f"Required JSON outputs: {', '.join(json_outputs)}")
                lines.append("Place each JSON block after your analysis of that data.")
                lines.append("")

        if tool_results:
            lines.append("=" * 50)
            lines.append("TOOL RESULTS — Computational tools have already analyzed the data.")
            lines.append("You MUST use these results as the factual basis for your response.")
            lines.append("=" * 50)
            for tool_name, result in tool_results.items():
                lines.append(f"\n[Tool: {tool_name}]")
                lines.append(result)
            lines.append("")
            lines.append("IMPORTANT — When referencing tool findings:")
            lines.append("  - Cite the tool name (e.g., 'The P118 Validator found...')")
            lines.append("  - Quote specific measured values and thresholds from the tool data")
            lines.append("  - Reference specific locations by room/corridor ID and name")
            lines.append("  - Do NOT invent violations or measurements — use only what the tools report")
            lines.append("")

        if definition.conversational and definition.conversation_guidelines:
            lines.append("CONVERSATION GUIDELINES:")
            lines.append(f"  {definition.conversation_guidelines}")
            lines.append("")

        if definition.conversational:
            lines.append("SCOPE BOUNDARIES:")
            lines.append("  - Stay within your defined goal. Do not perform tasks outside your scope.")
            lines.append("  - If the user asks about something outside your scope, politely redirect them")
            lines.append("    to the appropriate agent (mention the agent by name if possible).")
            lines.append("  - Be proactive: flag issues, ask clarifying questions about ambiguities.")
            lines.append("")

        lines.append("Provide structured, actionable output.")
        lines.append("Reference specific locations, measurements, and data from the inputs.")
        lines.append("Be precise but explain your reasoning clearly.")

        return "\n".join(lines)

    @staticmethod
    def build_user_prompt(inputs: Dict[str, str]) -> str:
        if not inputs:
            return "Please analyze the provided data."

        parts = []
        for name, value in inputs.items():
            parts.append(f"[{name}]:\n{value}")
        return "\n\n".join(parts)
