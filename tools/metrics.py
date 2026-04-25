"""
Metrics Calculator — computes violation statistics and compliance scoring.

Aggregates violations by severity, computes a compliance score,
and determines overall pass/fail status.
"""

from typing import Dict, List
from models.violations import MetricsReport


def compute_metrics(inputs: Dict) -> dict:
    """
    Compute a MetricsReport from a list of violations.

    Args:
        inputs: Dict with key "violations" containing a list of violation dicts.
                Each violation dict must have a "severity" field.
                Also accepts a raw list of violation dicts directly.

    Returns:
        MetricsReport as a dict with counts, compliance score, and pass/fail.
    """
    # Extract violations list from inputs
    if isinstance(inputs, list):
        violations = inputs
    elif isinstance(inputs, dict):
        violations = inputs.get("violations", [])
        if not violations and "severity" in inputs:
            # Single violation passed as dict
            violations = [inputs]
    else:
        violations = []

    critical = 0
    major = 0
    minor = 0
    info = 0

    for v in violations:
        severity = v.get("severity", "info") if isinstance(v, dict) else "info"
        if severity == "critical":
            critical += 1
        elif severity == "major":
            major += 1
        elif severity == "minor":
            minor += 1
        else:
            info += 1

    total = critical + major + minor + info

    # Compliance score: 100 minus weighted penalty per violation
    # Critical: -25, Major: -10, Minor: -3, Info: -1
    score = max(0.0, 100.0 - 25 * critical - 10 * major - 3 * minor - 1 * info)

    # Pass/fail: PASS only if no critical or major violations
    pass_fail = "PASS" if critical == 0 and major == 0 else "FAIL"

    report = MetricsReport(
        total_violations=total,
        critical_count=critical,
        major_count=major,
        minor_count=minor,
        info_count=info,
        compliance_score=round(score, 1),
        pass_fail=pass_fail,
    )
    return report.to_dict()
