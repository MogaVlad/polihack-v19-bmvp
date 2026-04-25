from typing import Dict, List
from models.violations import MetricsReport


def compute_metrics(inputs: Dict) -> dict:
    report = MetricsReport()
    return report.to_dict()
