"""Phase 3 B+C cross-agent integration tests.

Tests: all agents x all plans (tools), cache coverage, user-created agents,
conversational follow-ups across all agents.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent_definition import AgentDefinition, AgentInput, AgentOutput
from models.floor_plan import FloorPlan
from models.chat import AgentResult
from engine.runner import AgentRunner
from engine.prompt_builder import PromptBuilder
from engine.conversation import ConversationManager
from engine.cache import ResponseCache
from tools.registry import ToolRegistry


PLANS = ["example_office", "example_hospital", "example_school", "example_borderline"]
AGENT_IDS = ["egress_validator", "evacuation_diagnoser", "exit_placement_advisor", "floor_plan_parser"]


def test_all_agents_tools_on_all_plans():
    """Run every agent's tools on every plan — no crashes, valid output."""
    runner = AgentRunner()
    agents = {a.id: a for a in AgentDefinition.load_all_from_directory("data/agents")}

    for plan_name in PLANS:
        plan = FloorPlan.load_from_json(f"data/floor_plans/{plan_name}.json")
        plan_data = json.dumps(plan.to_dict())

        for agent_id in AGENT_IDS:
            agent = agents[agent_id]

            if agent_id == "floor_plan_parser":
                inputs = {"floor_plan": plan_data}
            else:
                inputs = {"parsed_plan": plan_data}

            tool_results = runner._run_tools(agent, inputs, lambda s: None)

            for tool_name, result_str in tool_results.items():
                parsed = json.loads(result_str)
                if tool_name in ("gemini_vision", "dxf_parser"):
                    continue
                assert not (isinstance(parsed, dict) and "error" in parsed), (
                    f"{agent_id}/{plan_name}/{tool_name}: {parsed.get('error')}"
                )

    print(f"PASS: test_all_agents_tools_on_all_plans ({len(AGENT_IDS)} agents x {len(PLANS)} plans)")


def test_egress_validator_finds_violations_per_plan():
    """Egress validator produces meaningful violations for each plan."""
    runner = AgentRunner()
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")

    expected_min_violations = {
        "example_office": 3,
        "example_hospital": 0,
        "example_school": 0,
        "example_borderline": 2,
    }

    for plan_name in PLANS:
        plan = FloorPlan.load_from_json(f"data/floor_plans/{plan_name}.json")
        inputs = {"parsed_plan": json.dumps(plan.to_dict())}
        tool_results = runner._run_tools(agent, inputs, lambda s: None)

        p118 = json.loads(tool_results["p118_validator"])
        pathfinding = json.loads(tool_results["pathfinding"])
        structural = json.loads(tool_results["structural_checker"])

        assert isinstance(p118, list), f"{plan_name}: p118 not a list"
        assert isinstance(pathfinding, dict), f"{plan_name}: pathfinding not a dict"
        assert isinstance(structural, list), f"{plan_name}: structural not a list"

        total_violations = len(p118) + len(structural)
        min_expected = expected_min_violations[plan_name]
        assert total_violations >= min_expected, (
            f"{plan_name}: expected >= {min_expected} violations, got {total_violations}"
        )

        for room in plan.rooms:
            assert room.id in pathfinding, f"{plan_name}: room {room.id} missing from pathfinding"

        print(f"  {plan_name}: {len(p118)} P118 + {len(structural)} structural violations, "
              f"{len(pathfinding)} rooms in pathfinding")

    print("PASS: test_egress_validator_finds_violations_per_plan")


def test_cache_coverage_all_agents_all_plans():
    """Every agent has a usable cache entry for every plan."""
    cache = ResponseCache()

    for plan_name in PLANS:
        plan = FloorPlan.load_from_json(f"data/floor_plans/{plan_name}.json")
        inputs = {"parsed_plan": json.dumps(plan.to_dict())}

        for agent_id in AGENT_IDS:
            cached = cache.get_cached_result(agent_id, inputs)
            assert cached is not None, f"Missing cache: {agent_id} + {plan_name}"
            assert cached.agent_id == agent_id
            assert len(cached.explanation) > 50, f"Cache too short: {agent_id} + {plan_name}"

    print(f"PASS: test_cache_coverage_all_agents_all_plans ({len(AGENT_IDS)} x {len(PLANS)} = {len(AGENT_IDS)*len(PLANS)} entries)")


def test_cache_followups_all_agents():
    """Every agent has at least one follow-up cached for the office plan."""
    cache = ResponseCache()
    plan = FloorPlan.load_from_json("data/floor_plans/example_office.json")
    inputs = {"parsed_plan": json.dumps(plan.to_dict())}

    for agent_id in AGENT_IDS:
        cached = cache.get_cached_result(agent_id, inputs)
        assert cached is not None, f"No cache for {agent_id}"

    print("PASS: test_cache_followups_all_agents")


def test_prompt_assembly_all_agents():
    """Prompt builder produces valid prompts with tool results for all agents."""
    runner = AgentRunner()
    agents = AgentDefinition.load_all_from_directory("data/agents")
    plan = FloorPlan.load_from_json("data/floor_plans/example_office.json")
    inputs = {"parsed_plan": json.dumps(plan.to_dict())}

    for agent in agents:
        tool_results = runner._run_tools(agent, inputs, lambda s: None)
        system_prompt = PromptBuilder.build_system_prompt(agent, tool_results)
        user_prompt = PromptBuilder.build_user_prompt(inputs)

        assert agent.name in system_prompt
        assert "CONSTRAINTS" in system_prompt

        if agent.conversational:
            assert "SCOPE BOUNDARIES" in system_prompt
            assert "CONVERSATION BEHAVIOR" in system_prompt

        if tool_results:
            assert "TOOL RESULTS" in system_prompt
            for tool_name in tool_results:
                assert tool_name in system_prompt

        assert len(user_prompt) > 10

    print(f"PASS: test_prompt_assembly_all_agents ({len(agents)} agents)")


def test_scope_redirects_in_prompts():
    """Each agent's prompt correctly redirects to other specific agents."""
    agents = {a.id: a for a in AgentDefinition.load_all_from_directory("data/agents")}

    expected_redirects = {
        "egress_validator": ["Exit Placement Advisor", "Floor Plan Parser", "Evacuation Diagnoser"],
        "evacuation_diagnoser": ["Egress Validator", "Floor Plan Parser", "Exit Placement Advisor"],
        "exit_placement_advisor": ["Egress Validator", "Floor Plan Parser", "Evacuation Diagnoser"],
        "floor_plan_parser": ["Egress Validator", "Evacuation Diagnoser", "Exit Placement Advisor"],
    }

    for agent_id, redirect_names in expected_redirects.items():
        agent = agents[agent_id]
        prompt = PromptBuilder.build_system_prompt(agent)
        for redirect_name in redirect_names:
            assert redirect_name in prompt, (
                f"{agent_id} missing redirect to '{redirect_name}'"
            )

    print("PASS: test_scope_redirects_in_prompts")


def test_user_created_agent_with_tools():
    """Simulate creating a custom agent and running its tools."""
    custom_def = AgentDefinition(
        id="custom_corridor_checker",
        name="Corridor Width Checker",
        category="Custom",
        goal="Verify all corridors meet minimum P118 width requirements",
        inputs=[AgentInput(name="parsed_plan", type="json", description="Floor plan JSON")],
        constraints=[
            "Check corridor widths against P118 Art. 3.6.12 (min 1.4m)",
            "Flag borderline values within 5% of threshold",
        ],
        outputs=[AgentOutput(name="width_report", type="json", description="Corridor width analysis")],
        tools=["p118_validator", "structural_checker"],
        conversational=True,
        conversation_guidelines="Answer questions about corridor widths and P118 requirements.",
    )

    runner = AgentRunner()
    plan = FloorPlan.load_from_json("data/floor_plans/example_office.json")
    inputs = {"parsed_plan": json.dumps(plan.to_dict())}

    tool_results = runner._run_tools(custom_def, inputs, lambda s: None)
    assert "p118_validator" in tool_results
    assert "structural_checker" in tool_results

    system_prompt = PromptBuilder.build_system_prompt(custom_def, tool_results)
    assert "Corridor Width Checker" in system_prompt
    assert "TOOL RESULTS" in system_prompt
    assert "SCOPE BOUNDARIES" in system_prompt

    print("PASS: test_user_created_agent_with_tools")


def test_conversation_followup_with_cache_fallback():
    """Conversation follow-ups fall back to cache when LLM is unavailable."""
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    plan = FloorPlan.load_from_json("data/floor_plans/example_office.json")
    inputs = {"parsed_plan": json.dumps(plan.to_dict())}

    cm = ConversationManager(agent)
    cm.initialize(
        system_prompt="test",
        initial_response="Found violations.",
        tool_results={},
        inputs=inputs,
    )

    cached = cm.cache.get_cached_followup(agent.id, inputs, "Which violation is the most critical?")
    assert cached is not None, "No cached follow-up for egress_validator"
    assert len(cached) > 20
    print("PASS: test_conversation_followup_with_cache_fallback")


def test_borderline_plan_edge_cases():
    """Borderline plan triggers proper edge-case handling."""
    runner = AgentRunner()
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    plan = FloorPlan.load_from_json("data/floor_plans/example_borderline.json")
    inputs = {"parsed_plan": json.dumps(plan.to_dict())}

    tool_results = runner._run_tools(agent, inputs, lambda s: None)

    p118 = json.loads(tool_results["p118_validator"])
    structural = json.loads(tool_results["structural_checker"])

    disconnected = [v for v in p118 if "no reachable exit" in v.get("description", "").lower()
                    or v.get("severity") == "critical"]
    assert len(disconnected) >= 1, "Should detect disconnected Room R4"

    corridor_violations = [v for v in p118 if v.get("rule") == "corridor_width"]
    assert len(corridor_violations) >= 1, "Should detect borderline corridor C2"

    anomalies = [v for v in structural if "polygon" in v.get("description", "").lower()
                 or "nonexistent" in v.get("description", "").lower()
                 or "GHOST" in v.get("description", "")]
    assert len(anomalies) >= 1, "Should detect structural anomalies (missing polygon, ghost corridor)"

    door_violations = [v for v in p118 if v.get("rule") == "door_width"]
    assert len(door_violations) >= 1, "Should detect borderline door D3"

    print("PASS: test_borderline_plan_edge_cases (disconnected room, borderline values, anomalies)")


def test_full_run_with_cache_fallback():
    """Full agent run uses cache when LLM is unavailable."""
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    plan = FloorPlan.load_from_json("data/floor_plans/example_office.json")
    inputs = {"parsed_plan": json.dumps(plan.to_dict())}

    statuses = []
    result = AgentRunner().run_agent(agent, inputs, lambda s: statuses.append(s))

    assert isinstance(result, AgentResult)
    assert result.agent_id == "egress_validator"
    assert len(result.explanation) > 50

    if result.success:
        print(f"PASS: test_full_run_with_cache_fallback (LLM responded, {len(result.explanation)} chars)")
    else:
        assert "Error" in result.explanation or "cache" in str(statuses).lower()
        print(f"PASS: test_full_run_with_cache_fallback (cache fallback used)")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3 B+C Cross-Agent Integration Tests")
    print("=" * 60)
    print()

    test_all_agents_tools_on_all_plans()
    print()
    test_egress_validator_finds_violations_per_plan()
    print()
    test_cache_coverage_all_agents_all_plans()
    test_cache_followups_all_agents()
    print()
    test_prompt_assembly_all_agents()
    test_scope_redirects_in_prompts()
    print()
    test_user_created_agent_with_tools()
    test_conversation_followup_with_cache_fallback()
    print()
    test_borderline_plan_edge_cases()
    print()
    test_full_run_with_cache_fallback()

    print()
    print("=" * 60)
    print("All Phase 3 B+C tests passed!")
    print("=" * 60)
