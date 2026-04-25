import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.agent_definition import AgentDefinition, AgentInput, AgentOutput
from models.floor_plan import FloorPlan, Room, Door, Exit, Corridor
from models.violations import Violation, DiagnosisResult, FixProposal, MetricsReport
from models.chat import ChatMessage, AgentResult


def test_agent_definition_roundtrip():
    ad = AgentDefinition(
        id="test_agent",
        name="Test Agent",
        category="Test",
        goal="Do something",
        inputs=[AgentInput(name="data", type="json", description="Input data")],
        constraints=["Rule 1", "Rule 2"],
        outputs=[AgentOutput(name="result", type="json", description="Output data")],
        tools=["p118_validator"],
        conversational=True,
        conversation_guidelines="Be helpful.",
    )
    d = ad.to_dict()
    restored = AgentDefinition.from_dict(d)
    assert restored.id == "test_agent"
    assert restored.name == "Test Agent"
    assert len(restored.inputs) == 1
    assert len(restored.constraints) == 2
    assert len(restored.outputs) == 1
    assert restored.tools == ["p118_validator"]
    assert restored.conversational is True
    print("PASS: test_agent_definition_roundtrip")


def test_agent_load_from_json():
    agents = AgentDefinition.load_all_from_directory("data/agents")
    assert len(agents) >= 2
    names = [a.name for a in agents]
    assert "Floor Plan Parser" in names
    assert "Egress Validator" in names
    print(f"PASS: test_agent_load_from_json ({len(agents)} agents loaded)")


def test_floor_plan_roundtrip():
    fp = FloorPlan(
        id="test",
        name="Test Plan",
        rooms=[Room(id="R1", name="Room 1", type="office", polygon=[(0, 0), (10, 0), (10, 10), (0, 10)], area=100.0, occupancy=10)],
        corridors=[Corridor(id="C1", name="Corridor 1", width=1.5, length=20.0, connects=["R1"])],
        doors=[Door(id="D1", connects=["R1", "C1"], width=0.9, position=(5, 0))],
        exits=[Exit(id="E1", room_id="R1", position=(0, 5), width=1.2)],
    )
    d = fp.to_dict()
    restored = FloorPlan.from_dict(d)
    assert restored.id == "test"
    assert len(restored.rooms) == 1
    assert len(restored.corridors) == 1
    assert restored.total_occupancy() == 10
    assert restored.get_room("R1").name == "Room 1"
    print("PASS: test_floor_plan_roundtrip")


def test_floor_plan_load_from_json():
    fp = FloorPlan.load_from_json("data/floor_plans/example_office.json")
    assert fp.id == "office_floor1"
    assert len(fp.rooms) >= 5
    assert len(fp.exits) >= 1
    print(f"PASS: test_floor_plan_load_from_json ({len(fp.rooms)} rooms, {len(fp.exits)} exits)")


def test_violation_roundtrip():
    v = Violation(
        id="V1",
        rule="travel_distance",
        article="P118 Art. 3.2",
        severity="critical",
        location="R3",
        description="Travel distance exceeds 30m",
        measured_value=34.5,
        threshold_value=30.0,
    )
    d = v.to_dict()
    restored = Violation.from_dict(d)
    assert restored.severity == "critical"
    assert restored.measured_value == 34.5
    print("PASS: test_violation_roundtrip")


def test_chat_message():
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.timestamp != ""
    d = msg.to_dict()
    restored = ChatMessage.from_dict(d)
    assert restored.content == "Hello"
    print("PASS: test_chat_message")


def test_metrics_report():
    report = MetricsReport(
        total_violations=5,
        critical_count=1,
        major_count=3,
        minor_count=1,
        compliance_score=60.0,
        pass_fail="FAIL",
    )
    d = report.to_dict()
    restored = MetricsReport.from_dict(d)
    assert restored.total_violations == 5
    assert restored.pass_fail == "FAIL"
    print("PASS: test_metrics_report")


if __name__ == "__main__":
    test_agent_definition_roundtrip()
    test_agent_load_from_json()
    test_floor_plan_roundtrip()
    test_floor_plan_load_from_json()
    test_violation_roundtrip()
    test_chat_message()
    test_metrics_report()
    print("\nAll model tests passed!")
