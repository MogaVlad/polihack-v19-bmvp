from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Violation:
    id: str
    rule: str
    article: str
    severity: str
    location: str
    description: str
    measured_value: Optional[float] = None
    threshold_value: Optional[float] = None

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "rule": self.rule,
            "article": self.article,
            "severity": self.severity,
            "location": self.location,
            "description": self.description,
        }
        if self.measured_value is not None:
            d["measured_value"] = self.measured_value
        if self.threshold_value is not None:
            d["threshold_value"] = self.threshold_value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Violation":
        return cls(
            id=data.get("id", ""),
            rule=data.get("rule", ""),
            article=data.get("article", ""),
            severity=data.get("severity", "major"),
            location=data.get("location", ""),
            description=data.get("description", ""),
            measured_value=data.get("measured_value"),
            threshold_value=data.get("threshold_value"),
        )


@dataclass
class DiagnosisResult:
    violation_id: str
    explanation: str
    impact: str
    severity_rank: int
    affected_occupants: int = 0

    def to_dict(self) -> dict:
        return {
            "violation_id": self.violation_id,
            "explanation": self.explanation,
            "impact": self.impact,
            "severity_rank": self.severity_rank,
            "affected_occupants": self.affected_occupants,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DiagnosisResult":
        return cls(
            violation_id=data.get("violation_id", ""),
            explanation=data.get("explanation", ""),
            impact=data.get("impact", ""),
            severity_rank=data.get("severity_rank", 0),
            affected_occupants=data.get("affected_occupants", 0),
        )


@dataclass
class FixProposal:
    id: str
    target_violation: str
    description: str
    justification: str
    estimated_effort: str
    impact_score: float = 0.0
    resolves_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "target_violation": self.target_violation,
            "description": self.description,
            "justification": self.justification,
            "estimated_effort": self.estimated_effort,
            "impact_score": self.impact_score,
            "resolves_violations": self.resolves_violations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FixProposal":
        return cls(
            id=data.get("id", ""),
            target_violation=data.get("target_violation", ""),
            description=data.get("description", ""),
            justification=data.get("justification", ""),
            estimated_effort=data.get("estimated_effort", ""),
            impact_score=data.get("impact_score", 0.0),
            resolves_violations=data.get("resolves_violations", []),
        )


@dataclass
class MetricsReport:
    total_violations: int = 0
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    info_count: int = 0
    compliance_score: float = 0.0
    pass_fail: str = "FAIL"

    def to_dict(self) -> dict:
        return {
            "total_violations": self.total_violations,
            "critical_count": self.critical_count,
            "major_count": self.major_count,
            "minor_count": self.minor_count,
            "info_count": self.info_count,
            "compliance_score": self.compliance_score,
            "pass_fail": self.pass_fail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetricsReport":
        return cls(
            total_violations=data.get("total_violations", 0),
            critical_count=data.get("critical_count", 0),
            major_count=data.get("major_count", 0),
            minor_count=data.get("minor_count", 0),
            info_count=data.get("info_count", 0),
            compliance_score=data.get("compliance_score", 0.0),
            pass_fail=data.get("pass_fail", "FAIL"),
        )
