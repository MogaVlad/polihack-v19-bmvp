import hashlib
import json
import os
from typing import Dict, List, Optional, Tuple, Any

from models.chat import AgentResult

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")


class ResponseCache:
    """Cached/fallback response system for demo safety.

    Stores known-good LLM responses keyed by agent_id + input hash.
    Used when the API is unavailable (rate limits, outages).
    """

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _input_hash(self, inputs: Dict[str, str]) -> str:
        normalized = []
        for value in inputs.values():
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    normalized.append(json.dumps(parsed, sort_keys=True, separators=(",", ":")))
                except (json.JSONDecodeError, TypeError):
                    normalized.append(value)
            else:
                normalized.append(str(value))
        normalized.sort()
        serialized = "\0".join(normalized)
        return hashlib.md5(serialized.encode()).hexdigest()[:12]

    def _cache_path(self, agent_id: str, input_hash: str) -> str:
        return os.path.join(self.cache_dir, f"{agent_id}_{input_hash}.json")

    def get_cached_result(self, agent_id: str, inputs: Dict[str, str]) -> Optional[AgentResult]:
        input_hash = self._input_hash(inputs)
        path = self._cache_path(agent_id, input_hash)

        if not os.path.isfile(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            is_valid, _ = self.validate_cached_result_data(data)
            if not is_valid:
                return None
            return AgentResult(
                agent_id=data["agent_id"],
                success=True,
                outputs=data.get("outputs", {}),
                explanation=data.get("initial_response", ""),
                tool_results=data.get("tool_results", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return None

    def get_cached_followup(self, agent_id: str, inputs: Dict[str, str], question: str) -> Optional[str]:
        input_hash = self._input_hash(inputs)
        path = self._cache_path(agent_id, input_hash)

        if not os.path.isfile(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            is_valid, _ = self.validate_cached_result_data(data)
            if not is_valid:
                return None
            question_lower = question.lower().strip()
            for fu in data.get("followups", []):
                if self._fuzzy_match(question_lower, fu["question"].lower()):
                    return fu["response"]
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def save_result(
        self,
        agent_id: str,
        inputs: Dict[str, str],
        result: AgentResult,
        followups: Optional[List[dict]] = None,
    ):
        input_hash = self._input_hash(inputs)
        path = self._cache_path(agent_id, input_hash)

        data = {
            "agent_id": agent_id,
            "input_hash": input_hash,
            "initial_response": result.explanation,
            "outputs": result.outputs,
            "tool_results": result.tool_results,
            "followups": followups or [],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def validate_cached_result_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        issues: List[str] = []

        if not isinstance(data, dict):
            return False, ["cache payload must be a JSON object"]

        if not isinstance(data.get("agent_id"), str) or not data.get("agent_id"):
            issues.append("missing or invalid 'agent_id'")
        if not isinstance(data.get("input_hash"), str) or not data.get("input_hash"):
            issues.append("missing or invalid 'input_hash'")
        if not isinstance(data.get("initial_response", ""), str):
            issues.append("'initial_response' must be a string")
        if not isinstance(data.get("outputs", {}), dict):
            issues.append("'outputs' must be an object")
        if not isinstance(data.get("tool_results", {}), dict):
            issues.append("'tool_results' must be an object")

        followups = data.get("followups", [])
        if not isinstance(followups, list):
            issues.append("'followups' must be a list")
        else:
            for idx, fu in enumerate(followups):
                if not isinstance(fu, dict):
                    issues.append(f"followups[{idx}] must be an object")
                    continue
                if not isinstance(fu.get("question"), str) or not fu.get("question"):
                    issues.append(f"followups[{idx}] missing valid 'question'")
                if not isinstance(fu.get("response"), str) or not fu.get("response"):
                    issues.append(f"followups[{idx}] missing valid 'response'")

        return len(issues) == 0, issues

    def validate_all_cached_responses(self) -> Dict[str, Any]:
        report = {
            "valid": True,
            "checked_files": 0,
            "invalid_files": {},
            "l2": {},
        }

        if os.path.isdir(self.cache_dir):
            for fname in sorted(os.listdir(self.cache_dir)):
                if fname == "l2" or not fname.endswith(".json"):
                    continue
                report["checked_files"] += 1
                path = os.path.join(self.cache_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    is_valid, issues = self.validate_cached_result_data(data)
                    if not is_valid:
                        report["valid"] = False
                        report["invalid_files"][fname] = issues
                except Exception as exc:
                    report["valid"] = False
                    report["invalid_files"][fname] = [str(exc)]

        report["l2"] = L2ResponseCache(self.cache_dir).validate_all_cached_responses()
        if not report["l2"].get("valid", True):
            report["valid"] = False

        return report

    @staticmethod
    def _fuzzy_match(query: str, cached_question: str) -> bool:
        query_words = set(query.split())
        cached_words = set(cached_question.split())
        if not cached_words:
            return False
        overlap = len(query_words & cached_words)
        return overlap / len(cached_words) > 0.5


class L2ResponseCache:
    """Cached L2 template responses for demo safety."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = os.path.join(cache_dir, "l2")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_path(self, template_name: str, data_hash: str) -> str:
        return os.path.join(self.cache_dir, f"{template_name}_{data_hash}.json")

    def get_cached(self, template_name: str, data: str) -> Optional[str]:
        data_hash = hashlib.md5(data.encode()).hexdigest()[:12]
        path = self._cache_path(template_name, data_hash)

        if not os.path.isfile(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            is_valid, _ = self.validate_cached_response_data(cached)
            if not is_valid:
                return None
            return cached.get("response", None)
        except (json.JSONDecodeError, KeyError):
            return None

    def save_cached(self, template_name: str, data: str, response: str):
        data_hash = hashlib.md5(data.encode()).hexdigest()[:12]
        path = self._cache_path(template_name, data_hash)

        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "template": template_name,
                "data_hash": data_hash,
                "response": response,
            }, f, indent=2, ensure_ascii=False)

    def _find_by_template(self, template_name: str) -> Optional[str]:
        if not os.path.isdir(self.cache_dir):
            return None
        for fname in os.listdir(self.cache_dir):
            if fname.startswith(template_name) and fname.endswith(".json"):
                return os.path.join(self.cache_dir, fname)
        return None

    @staticmethod
    def validate_cached_response_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        issues: List[str] = []

        if not isinstance(data, dict):
            return False, ["cache payload must be a JSON object"]

        if not isinstance(data.get("template"), str) or not data.get("template"):
            issues.append("missing or invalid 'template'")
        if not isinstance(data.get("data_hash"), str) or not data.get("data_hash"):
            issues.append("missing or invalid 'data_hash'")
        if not isinstance(data.get("response"), str) or not data.get("response"):
            issues.append("missing or invalid 'response'")

        return len(issues) == 0, issues

    def validate_all_cached_responses(self) -> Dict[str, Any]:
        report = {
            "valid": True,
            "checked_files": 0,
            "invalid_files": {},
        }

        if not os.path.isdir(self.cache_dir):
            return report

        for fname in sorted(os.listdir(self.cache_dir)):
            if not fname.endswith(".json"):
                continue
            report["checked_files"] += 1
            path = os.path.join(self.cache_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                is_valid, issues = self.validate_cached_response_data(data)
                if not is_valid:
                    report["valid"] = False
                    report["invalid_files"][fname] = issues
            except Exception as exc:
                report["valid"] = False
                report["invalid_files"][fname] = [str(exc)]

        return report
