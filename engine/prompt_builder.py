from models.agent_definition import AgentDefinition
from typing import Dict, Optional


AGENT_SCOPE_MAP = {
    "floor_plan_parser": {
        "in_scope": [
            "Parsing floor plan images into structured data",
            "Identifying rooms, corridors, doors, exits, stairs",
            "Classifying room types and estimating occupancy",
            "Flagging ambiguous or unusual features in the plan",
        ],
        "out_of_scope": {
            "compliance checking or P118 validation": "Egress Validator",
            "violation explanation or safety impact": "Evacuation Diagnoser",
            "fix proposals or exit placement": "Exit Placement Advisor",
        },
    },
    "egress_validator": {
        "in_scope": [
            "Checking floor plans against P118 fire safety regulations",
            "Reporting violations with severity, location, and rule reference",
            "Explaining which rules were checked and borderline cases",
            "Answering questions about specific violations found",
        ],
        "out_of_scope": {
            "parsing floor plan images": "Floor Plan Parser",
            "plain-language diagnosis or safety impact ranking": "Evacuation Diagnoser",
            "fix proposals or exit placement suggestions": "Exit Placement Advisor",
        },
    },
    "evacuation_diagnoser": {
        "in_scope": [
            "Explaining violations in plain language for non-specialists",
            "Ranking violations by real-world safety impact",
            "Describing what would happen in an actual fire",
            "Comparing to similar buildings or common scenarios",
        ],
        "out_of_scope": {
            "running P118 validation or finding new violations": "Egress Validator",
            "parsing floor plan images": "Floor Plan Parser",
            "proposing fixes or exit placement": "Exit Placement Advisor",
        },
    },
    "exit_placement_advisor": {
        "in_scope": [
            "Suggesting optimal exit locations to resolve violations",
            "Proposing plan modifications ranked by impact-to-effort",
            "Discussing trade-offs and alternative approaches",
            "Adjusting proposals when the engineer pushes back",
        ],
        "out_of_scope": {
            "running P118 validation or diagnosing new violations": "Egress Validator",
            "parsing floor plan images": "Floor Plan Parser",
            "plain-language diagnosis or safety impact analysis": "Evacuation Diagnoser",
        },
    },
}


class PromptBuilder:
    """Assembles LLM prompts from agent definitions, inputs, and tool results."""

    @staticmethod
    def build_system_prompt(
        definition: AgentDefinition,
        tool_results: Optional[Dict[str, str]] = None,
    ) -> str:
        lines = []

        lines.append(f"You are the '{definition.name}' agent on the AgentArchitect platform.")
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
            scope = AGENT_SCOPE_MAP.get(definition.id)
            lines.append("SCOPE BOUNDARIES:")
            if scope:
                lines.append("  You are responsible for:")
                for item in scope["in_scope"]:
                    lines.append(f"    - {item}")
                lines.append("")
                lines.append("  OUT OF SCOPE — If the user asks about any of the following,")
                lines.append("  politely explain it is outside your role and redirect them:")
                for topic, agent in scope["out_of_scope"].items():
                    lines.append(f'    - {topic} → redirect to the "{agent}" agent')
            else:
                lines.append("  - Stay within your defined goal. Do not perform tasks outside your scope.")
                lines.append("  - If the user asks about something outside your scope, politely redirect them")
                lines.append("    to the appropriate agent (mention the agent by name if possible).")
            lines.append("")

            lines.append("CONVERSATION BEHAVIOR:")
            lines.append("  - Be PROACTIVE: after your initial analysis, flag the most important finding")
            lines.append("    and ask if the engineer wants to explore it further.")
            lines.append("  - When the engineer pushes back or disagrees, acknowledge their point,")
            lines.append("    explain your reasoning with specific data, and offer alternatives.")
            lines.append("  - Keep follow-up answers coherent with prior turns — reference what was")
            lines.append("    already discussed, do not repeat your full initial analysis.")
            lines.append("  - If the engineer provides new information, incorporate it and update")
            lines.append("    your assessment accordingly.")
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
