from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class AgentResult:
    agent_id: str
    success: bool
    outputs: dict = field(default_factory=dict)
    explanation: str = ""
    tool_results: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "agent_id": self.agent_id,
            "success": self.success,
            "outputs": self.outputs,
            "explanation": self.explanation,
            "tool_results": self.tool_results,
        }
        if self.error:
            d["error"] = self.error
        return d
