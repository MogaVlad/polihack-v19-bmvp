import hashlib
import json
import os
from typing import Dict, List, Optional

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
        serialized = json.dumps(inputs, sort_keys=True)
        return hashlib.md5(serialized.encode()).hexdigest()[:12]

    def _cache_path(self, agent_id: str, input_hash: str) -> str:
        return os.path.join(self.cache_dir, f"{agent_id}_{input_hash}.json")

    def get_cached_result(self, agent_id: str, inputs: Dict[str, str]) -> Optional[AgentResult]:
        input_hash = self._input_hash(inputs)
        path = self._cache_path(agent_id, input_hash)

        if not os.path.isfile(path):
            path = self._find_by_agent_id(agent_id)
            if not path:
                return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
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
            path = self._find_by_agent_id(agent_id)
            if not path:
                return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
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

    def _find_by_agent_id(self, agent_id: str) -> Optional[str]:
        """Find any cached file for this agent (fallback when exact hash doesn't match)."""
        if not os.path.isdir(self.cache_dir):
            return None
        for fname in os.listdir(self.cache_dir):
            if fname.startswith(agent_id) and fname.endswith(".json"):
                return os.path.join(self.cache_dir, fname)
        return None

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
            path = self._find_by_template(template_name)
            if not path:
                return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                cached = json.load(f)
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
