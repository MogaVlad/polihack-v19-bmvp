"""Phase 2 engine pipeline tests.

Tests: tool integration, prompt quality, cache fallback, L2 vs L3 contrast.
Requires a valid GEMINI_API_KEY in .env for LLM tests; other tests work offline.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent_definition import AgentDefinition
from models.floor_plan import FloorPlan
from models.chat import AgentResult, ChatMessage
from engine.runner import AgentRunner
from engine.prompt_builder import PromptBuilder
from engine.conversation import ConversationManager
from engine.cache import ResponseCache, L2ResponseCache
from llm.gemini_client import GeminiClient
from tools.registry import ToolRegistry


def test_prompt_builder():
    """Test that PromptBuilder produces well-structured prompts."""
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")

    prompt = PromptBuilder.build_system_prompt(agent)
    assert "Egress Validator" in prompt
    assert "CONSTRAINTS" in prompt
    assert "EXPECTED OUTPUTS" in prompt
    assert "SCOPE BOUNDARIES" in prompt
    assert "CONVERSATION GUIDELINES" in prompt
    print("PASS: test_prompt_builder (system prompt)")

    tool_results = {"p118_validator": '[{"id": "V1", "rule": "corridor_width", "severity": "major"}]'}
    prompt_with_tools = PromptBuilder.build_system_prompt(agent, tool_results)
    assert "TOOL RESULTS" in prompt_with_tools
    assert "p118_validator" in prompt_with_tools
    assert "Cite the tool name" in prompt_with_tools
    assert "Do NOT invent violations" in prompt_with_tools
    print("PASS: test_prompt_builder (with tool results — improved instructions)")

    inputs = {"parsed_plan": '{"rooms": [{"id": "R1"}]}'}
    user_prompt = PromptBuilder.build_user_prompt(inputs)
    assert "[parsed_plan]" in user_prompt
    print("PASS: test_prompt_builder (user prompt)")


def test_tool_registry():
    """Test that all expected tools are registered."""
    registry = ToolRegistry()
    names = registry.list_tool_names()
    assert "p118_validator" in names
    assert "pathfinding" in names
    assert "structural_checker" in names
    assert "metrics" in names
    assert "gemini_vision" in names
    print(f"PASS: test_tool_registry ({len(names)} tools registered: {names})")


def test_tool_integration():
    """Test that runner executes tools and injects results into prompts."""
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    plan = FloorPlan.load_from_json("data/floor_plans/example_office.json")

    runner = AgentRunner()
    inputs = {"parsed_plan": json.dumps(plan.to_dict())}
    tool_input = runner._prepare_tool_input(inputs)

    assert "rooms" in tool_input
    assert "corridors" in tool_input
    print("PASS: test_tool_integration (input preparation)")

    statuses = []
    tool_results = runner._run_tools(agent, inputs, lambda s: statuses.append(s))

    assert "p118_validator" in tool_results
    assert "pathfinding" in tool_results
    assert "structural_checker" in tool_results
    print(f"PASS: test_tool_integration (3 tools ran, statuses: {statuses})")

    p118_data = json.loads(tool_results["p118_validator"])
    assert isinstance(p118_data, list)
    assert len(p118_data) > 0
    assert p118_data[0]["severity"] in ("critical", "major", "minor", "info")

    path_data = json.loads(tool_results["pathfinding"])
    assert isinstance(path_data, dict)
    assert "R1" in path_data

    structural_data = json.loads(tool_results["structural_checker"])
    assert isinstance(structural_data, list)
    print("PASS: test_tool_integration (tool output structure valid)")

    system_prompt = PromptBuilder.build_system_prompt(agent, tool_results)
    assert "p118_validator" in system_prompt
    assert "pathfinding" in system_prompt
    assert "structural_checker" in system_prompt
    assert "TOOL RESULTS" in system_prompt
    print("PASS: test_tool_integration (tool results injected into prompt)")


def test_agent_runner_offline():
    """Test AgentRunner output parsing with mock response."""
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    runner = AgentRunner()

    mock_response = '''Here are the violations found:

```json
[
  {"id": "V1", "rule": "corridor_width", "severity": "major", "location": "C2"}
]
```

The floor plan has 1 violation.'''

    outputs = runner._parse_outputs(mock_response, agent)
    assert "response" in outputs
    assert "violations" in outputs
    assert isinstance(outputs["violations"], list)
    print("PASS: test_agent_runner_offline (output parsing)")

    assert runner._is_error("[Error: API failed]")
    assert runner._is_error("")
    assert not runner._is_error("Here are the results...")
    print("PASS: test_agent_runner_offline (error detection)")


def test_cache_system():
    """Test cache save/load/fallback."""
    cache = ResponseCache()

    result = AgentResult(
        agent_id="test_agent",
        success=True,
        outputs={"response": "test output"},
        explanation="test explanation",
        tool_results={"test_tool": "test data"},
    )
    test_inputs = {"data": "test_data_value"}
    cache.save_result("test_agent", test_inputs, result, [
        {"question": "follow up question?", "response": "follow up answer"},
    ])

    loaded = cache.get_cached_result("test_agent", test_inputs)
    assert loaded is not None
    assert loaded.agent_id == "test_agent"
    assert loaded.success is True
    assert loaded.explanation == "test explanation"
    print("PASS: test_cache_system (save and load)")

    followup = cache.get_cached_followup("test_agent", test_inputs, "follow up question?")
    assert followup == "follow up answer"
    print("PASS: test_cache_system (followup retrieval)")

    fuzzy = cache.get_cached_followup("test_agent", test_inputs, "tell me the follow up question")
    assert fuzzy == "follow up answer"
    print("PASS: test_cache_system (fuzzy followup matching)")

    missing = cache.get_cached_result("nonexistent_agent", {"x": "y"})
    assert missing is None
    print("PASS: test_cache_system (missing cache returns None)")

    # Clean up test file
    import hashlib
    h = hashlib.md5(json.dumps(test_inputs, sort_keys=True).encode()).hexdigest()[:12]
    test_path = os.path.join(cache.cache_dir, f"test_agent_{h}.json")
    if os.path.exists(test_path):
        os.remove(test_path)


def test_prebuilt_caches():
    """Test that pre-built demo caches exist and are loadable."""
    cache = ResponseCache()

    plan = FloorPlan.load_from_json("data/floor_plans/example_office.json")
    inputs = {"parsed_plan": json.dumps(plan.to_dict())}
    cached = cache.get_cached_result("egress_validator", inputs)
    assert cached is not None
    assert cached.agent_id == "egress_validator"
    assert "violations" in cached.explanation.lower() or "violation" in cached.explanation.lower()
    print("PASS: test_prebuilt_caches (egress_validator office)")

    followup = cache.get_cached_followup("egress_validator", inputs, "Which violation is the most critical?")
    assert followup is not None
    assert len(followup) > 50
    print("PASS: test_prebuilt_caches (egress_validator followup)")

    for plan_name in ["example_hospital", "example_school"]:
        plan = FloorPlan.load_from_json(f"data/floor_plans/{plan_name}.json")
        inputs = {"parsed_plan": json.dumps(plan.to_dict())}
        cached = cache.get_cached_result("egress_validator", inputs)
        assert cached is not None, f"Missing cache for egress_validator + {plan_name}"
    print("PASS: test_prebuilt_caches (all egress_validator plans cached)")


def test_l2_cache():
    """Test L2 template response caching."""
    l2_cache = L2ResponseCache()

    plan = FloorPlan.load_from_json("data/floor_plans/example_office.json")
    data = json.dumps(plan.to_dict(), indent=2)
    cached = l2_cache.get_cached("v1_check_egress", data)
    assert cached is not None
    assert "violation" in cached.lower() or "exit" in cached.lower()
    print("PASS: test_l2_cache (v1_check_egress cached response)")


def test_conversation_manager_offline():
    """Test ConversationManager state management."""
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    cm = ConversationManager(agent)

    assert not cm.is_active
    assert cm.turn_count == 0

    cm.initialize(
        system_prompt="You are the Egress Validator agent.",
        initial_response="I found 3 violations in the floor plan.",
        tool_results={"p118_validator": "[]"},
        inputs={"parsed_plan": "{}"},
    )

    assert cm.is_active
    assert len(cm.get_history()) == 1
    assert cm.get_history()[0].role == "agent"
    print("PASS: test_conversation_manager_offline (initialization with inputs)")

    cm.clear()
    assert not cm.is_active
    assert cm.turn_count == 0
    print("PASS: test_conversation_manager_offline (clear)")


def test_l2_template():
    """Test L2 template loading and placeholder replacement."""
    template_path = "prompts/v1_check_egress.md"
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    assert "{{DATA}}" in template
    assert "L2 Artifact" in template
    assert "single-shot" in template.lower() or "cannot" in template.lower()
    replaced = template.replace("{{DATA}}", '{"rooms": []}')
    assert "{{DATA}}" not in replaced
    print("PASS: test_l2_template (template loading + L2 markers)")

    template_path2 = "prompts/v1_propose_fixes.md"
    with open(template_path2, "r", encoding="utf-8") as f:
        template2 = f.read()
    assert "{{DATA}}" in template2
    assert "{{VIOLATIONS}}" in template2
    print("PASS: test_l2_template (extra placeholders)")


def test_l2_vs_l3_contrast():
    """Verify structural differences between L2 and L3 approaches."""
    with open("prompts/v1_check_egress.md", "r", encoding="utf-8") as f:
        l2_template = f.read()

    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    l3_prompt = PromptBuilder.build_system_prompt(agent)

    assert "single-shot" in l2_template.lower() or "cannot ask" in l2_template.lower()
    assert "do not have access to computational tools" in l2_template.lower() or "cannot" in l2_template.lower()
    assert "do not use json" in l2_template.lower()

    assert "SCOPE BOUNDARIES" in l3_prompt
    assert "CONVERSATION GUIDELINES" in l3_prompt
    assert "CONVERSATION BEHAVIOR" in l3_prompt
    assert "CONSTRAINTS" in l3_prompt
    assert "EXPECTED OUTPUTS" in l3_prompt
    assert "```json" in l3_prompt.lower() or "json" in l3_prompt.lower()

    assert agent.conversational is True
    assert len(agent.tools) >= 2
    assert len(agent.constraints) >= 4

    print("PASS: test_l2_vs_l3_contrast (L2=plain-prose/no-tools, L3=structured-JSON/tools/conversational)")


def test_all_agents_have_valid_tools():
    """Verify every agent's tools exist in the registry."""
    registry = ToolRegistry()
    registered = set(registry.list_tool_names())

    agents = AgentDefinition.load_all_from_directory("data/agents")
    for agent in agents:
        for tool in agent.tools:
            assert tool in registered, f"Agent '{agent.id}' references unregistered tool '{tool}'"
    print(f"PASS: test_all_agents_have_valid_tools ({len(agents)} agents, all tools valid)")


def test_evacuation_diagnoser_uses_metrics():
    """Verify evacuation_diagnoser now uses metrics tool (not gemini_text)."""
    agent = AgentDefinition.load_from_json("data/agents/evacuation_diagnoser.json")
    assert "metrics" in agent.tools
    assert "gemini_text" not in agent.tools
    print("PASS: test_evacuation_diagnoser_uses_metrics")


def test_scope_boundaries():
    """Verify each agent's prompt contains explicit scope boundaries with redirects."""
    from engine.prompt_builder import AGENT_SCOPE_MAP

    agents = AgentDefinition.load_all_from_directory("data/agents")
    for agent in agents:
        prompt = PromptBuilder.build_system_prompt(agent)

        assert "SCOPE BOUNDARIES" in prompt, f"{agent.id} missing SCOPE BOUNDARIES"

        if agent.id in AGENT_SCOPE_MAP:
            scope = AGENT_SCOPE_MAP[agent.id]
            for item in scope["in_scope"]:
                assert item in prompt, f"{agent.id} missing in-scope: {item}"
            for topic, redirect_agent in scope["out_of_scope"].items():
                assert redirect_agent in prompt, f"{agent.id} missing redirect to {redirect_agent}"
            assert "OUT OF SCOPE" in prompt

    assert len(AGENT_SCOPE_MAP) == 4
    print(f"PASS: test_scope_boundaries ({len(agents)} agents with explicit scope + redirects)")


def test_conversation_behavior_instructions():
    """Verify L3 prompts include proactive flagging and pushback handling."""
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    prompt = PromptBuilder.build_system_prompt(agent)

    assert "CONVERSATION BEHAVIOR" in prompt
    assert "PROACTIVE" in prompt
    assert "pushes back" in prompt.lower() or "push back" in prompt.lower()
    assert "alternatives" in prompt.lower()
    assert "coherent" in prompt.lower()
    print("PASS: test_conversation_behavior_instructions")


def test_conversation_turn_limit():
    """Verify conversation manager enforces a turn limit."""
    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    cm = ConversationManager(agent)
    cm.initialize("system", "initial response", inputs={"x": "y"})

    assert cm.MAX_TURNS == 10

    for i in range(cm.MAX_TURNS):
        cm.history.append(ChatMessage(role="user", content=f"q{i}"))
        cm.history.append(ChatMessage(role="agent", content=f"a{i}"))

    assert cm.turn_count == cm.MAX_TURNS
    response = cm.followup("one more question")
    assert "limit" in response.lower()
    print("PASS: test_conversation_turn_limit")


def test_l2_templates_enforce_plain_text():
    """Verify all L2 templates explicitly forbid JSON/structured output."""
    import glob
    templates = glob.glob("prompts/v1_*.md")
    assert len(templates) >= 4

    for path in templates:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "do not use json" in content.lower(), f"{path} missing 'no JSON' instruction"
        assert "single-shot" in content.lower() or "cannot" in content.lower(), f"{path} missing L2 limitation"
    print(f"PASS: test_l2_templates_enforce_plain_text ({len(templates)} templates)")


def test_full_pipeline_with_llm():
    """Full pipeline test with actual LLM call. Requires valid API key."""
    import config
    if not config.GEMINI_API_KEY:
        print("SKIP: test_full_pipeline_with_llm (no API key)")
        return

    agent = AgentDefinition.load_from_json("data/agents/egress_validator.json")
    plan = FloorPlan.load_from_json("data/floor_plans/example_office.json")

    runner = AgentRunner()
    statuses = []

    result = runner.run_agent(
        agent,
        {"parsed_plan": json.dumps(plan.to_dict())},
        status_callback=lambda s: statuses.append(s),
    )

    assert isinstance(result, AgentResult)
    assert result.agent_id == "egress_validator"

    if not result.success and result.explanation.startswith("[Error"):
        if "cache" in str(statuses).lower():
            print("INFO: LLM failed but cache fallback was attempted")
        print(f"SKIP: test_full_pipeline_with_llm (API error — {result.explanation[:100]})")
        return

    assert result.success, f"Agent failed: {result.error or result.explanation[:200]}"
    assert "response" in result.outputs
    assert len(result.explanation) > 50
    assert len(result.tool_results) >= 2
    print(f"PASS: test_full_pipeline_with_llm")
    print(f"  Statuses: {statuses}")
    print(f"  Response length: {len(result.explanation)} chars")
    print(f"  Tool results: {list(result.tool_results.keys())}")

    cm = ConversationManager(agent, runner.client)
    inputs = {"parsed_plan": json.dumps(plan.to_dict())}
    system_prompt = PromptBuilder.build_system_prompt(agent, result.tool_results)
    cm.initialize(system_prompt, result.explanation, result.tool_results, inputs)

    followup_response = cm.followup("Which violation is the most critical and why?")
    assert len(followup_response) > 20
    assert cm.turn_count == 1
    print(f"PASS: test_full_pipeline_with_llm (conversation followup)")
    print(f"  Follow-up length: {len(followup_response)} chars")

    client = GeminiClient()
    l2_response = client.send_with_template(
        "prompts/v1_check_egress.md",
        json.dumps(plan.to_dict(), indent=2),
    )
    assert len(l2_response) > 20
    print(f"PASS: test_full_pipeline_with_llm (L2 template)")
    print(f"  L2 response length: {len(l2_response)} chars")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2 Engine + Tools Integration Tests")
    print("=" * 60)
    print()

    print("--- Offline Tests ---")
    print()
    test_prompt_builder()
    test_tool_registry()
    test_tool_integration()
    test_agent_runner_offline()
    test_cache_system()
    test_prebuilt_caches()
    test_l2_cache()
    test_conversation_manager_offline()
    test_l2_template()
    test_l2_vs_l3_contrast()
    test_all_agents_have_valid_tools()
    test_evacuation_diagnoser_uses_metrics()

    print()
    print("--- Phase 3 Tests (Person B) ---")
    print()
    test_scope_boundaries()
    test_conversation_behavior_instructions()
    test_conversation_turn_limit()
    test_l2_templates_enforce_plain_text()

    print()
    print("-" * 60)
    print("LLM Integration Tests (requires API key)")
    print("-" * 60)
    print()

    test_full_pipeline_with_llm()

    print()
    print("=" * 60)
    print("All Phase 2 + Phase 3 (Person B) tests passed!")
    print("=" * 60)
