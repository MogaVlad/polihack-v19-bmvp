from models.agent_definition import AgentDefinition
from typing import Dict, List, Optional


class PromptBuilder:
    """Assembles LLM prompts from agent definitions, inputs, and tool results."""

    @staticmethod
    def build_system_prompt(
        definition: AgentDefinition,
        tool_results: Optional[Dict[str, str]] = None,
    ) -> str:
        lines = []

        # ── Identity & Goal ─────────────────────────────────────────
        lines.append(f"You are the '{definition.name}' agent.")
        lines.append(f"Your goal: {definition.goal}")
        lines.append("")

        # ── Constraints ─────────────────────────────────────────────
        if definition.constraints:
            lines.append("CONSTRAINTS — You MUST respect these rules:")
            for i, c in enumerate(definition.constraints, 1):
                lines.append(f"  {i}. {c}")
            lines.append("")

        # ── Expected Inputs ─────────────────────────────────────────
        if definition.inputs:
            lines.append("EXPECTED INPUTS (the user will provide these):")
            for inp in definition.inputs:
                lines.append(f"  - {inp.name} ({inp.type}): {inp.description}")
            lines.append("")

        # ── Expected Outputs ────────────────────────────────────────
        if definition.outputs:
            lines.append("EXPECTED OUTPUTS — produce these in your response:")
            json_outputs = []
            for o in definition.outputs:
                lines.append(f"  - {o.name} ({o.type}): {o.description}")
                if o.type == "json":
                    json_outputs.append(o.name)
            lines.append("")

            if json_outputs:
                lines.append("OUTPUT FORMAT INSTRUCTIONS:")
                lines.append("When providing JSON outputs, wrap them in a ```json code block.")
                lines.append("Make sure the JSON is valid and parseable.")
                lines.append(f"JSON outputs needed: {', '.join(json_outputs)}")
                lines.append("")

        # ── Tool Results ────────────────────────────────────────────
        if tool_results:
            lines.append("=" * 50)
            lines.append("TOOL RESULTS — Use these data in your analysis:")
            lines.append("=" * 50)
            for tool_name, result in tool_results.items():
                lines.append(f"\n[Tool: {tool_name}]")
                lines.append(result)
            lines.append("")
            lines.append("Reference specific tool findings in your response.")
            lines.append("Cite tool names when making claims based on their data.")
            lines.append("")

        # ── Conversation Guidelines ────────────────────────────────
        if definition.conversational and definition.conversation_guidelines:
            lines.append("CONVERSATION GUIDELINES:")
            lines.append(f"  {definition.conversation_guidelines}")
            lines.append("")

        # ── Scope Boundaries ────────────────────────────────────────
        if definition.conversational:
            lines.append("SCOPE BOUNDARIES:")
            lines.append("  - Stay within your defined goal. Do not perform tasks outside your scope.")
            lines.append("  - If the user asks about something outside your scope, politely redirect them")
            lines.append("    to the appropriate agent (mention the agent by name if possible).")
            lines.append("  - Be proactive: flag issues, ask clarifying questions about ambiguities.")
            lines.append("")

        # ── General Instructions ────────────────────────────────────
        lines.append("Provide structured, actionable output.")
        lines.append("Reference specific locations, measurements, and data from the inputs.")
        lines.append("Be precise but explain your reasoning.")

        return "\n".join(lines)

    @staticmethod
    def build_user_prompt(inputs: Dict[str, str]) -> str:
        """Build the user message from provided inputs."""
        if not inputs:
            return "Please analyze the provided data."

        parts = []
        for name, value in inputs.items():
            parts.append(f"[{name}]:\n{value}")
        return "\n\n".join(parts)
