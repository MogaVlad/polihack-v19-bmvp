from typing import List, Dict
from models.violations import Violation


def validate_p118(inputs: Dict) -> List[dict]:
    violations = []
    violations.extend(_check_travel_distance(inputs))
    violations.extend(_check_exit_capacity(inputs))
    violations.extend(_check_door_widths(inputs))
    violations.extend(_check_corridor_widths(inputs))
    violations.extend(_check_dead_ends(inputs))
    violations.extend(_check_exit_count(inputs))
    return violations


def _check_travel_distance(inputs: Dict) -> List[dict]:
    return []


def _check_exit_capacity(inputs: Dict) -> List[dict]:
    return []


def _check_door_widths(inputs: Dict) -> List[dict]:
    return []


def _check_corridor_widths(inputs: Dict) -> List[dict]:
    return []


def _check_dead_ends(inputs: Dict) -> List[dict]:
    return []


def _check_exit_count(inputs: Dict) -> List[dict]:
    return []
