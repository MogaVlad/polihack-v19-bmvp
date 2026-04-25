from dataclasses import dataclass, field
from typing import List, Optional
import json
import os


@dataclass
class AgentInput:
    name: str
    type: str
    description: str

    def to_dict(self) -> dict:
        return {"name": self.name, "type": self.type, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict) -> "AgentInput":
        return cls(
            name=data["name"],
            type=data["type"],
            description=data.get("description", ""),
        )


@dataclass
class AgentOutput:
    name: str
    type: str
    description: str

    def to_dict(self) -> dict:
        return {"name": self.name, "type": self.type, "description": self.description}

    @classmethod
    def from_dict(cls, data: dict) -> "AgentOutput":
        return cls(
            name=data["name"],
            type=data["type"],
            description=data.get("description", ""),
        )


@dataclass
class AgentDefinition:
    id: str
    name: str
    category: str
    goal: str
    inputs: List[AgentInput] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    outputs: List[AgentOutput] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    conversational: bool = True
    conversation_guidelines: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "goal": self.goal,
            "inputs": [i.to_dict() for i in self.inputs],
            "constraints": self.constraints,
            "outputs": [o.to_dict() for o in self.outputs],
            "tools": self.tools,
            "conversational": self.conversational,
            "conversation_guidelines": self.conversation_guidelines,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentDefinition":
        return cls(
            id=data["id"],
            name=data["name"],
            category=data.get("category", "Custom"),
            goal=data["goal"],
            inputs=[AgentInput.from_dict(i) for i in data.get("inputs", [])],
            constraints=data.get("constraints", []),
            outputs=[AgentOutput.from_dict(o) for o in data.get("outputs", [])],
            tools=data.get("tools", []),
            conversational=data.get("conversational", True),
            conversation_guidelines=data.get("conversation_guidelines", ""),
        )

    @classmethod
    def load_from_json(cls, filepath: str) -> "AgentDefinition":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_json(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_all_from_directory(cls, directory: str) -> List["AgentDefinition"]:
        agents = []
        if not os.path.isdir(directory):
            return agents
        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".json"):
                try:
                    agent = cls.load_from_json(os.path.join(directory, filename))
                    agents.append(agent)
                except (json.JSONDecodeError, KeyError):
                    continue
        return agents
