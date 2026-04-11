"""Mock LLM backend for deterministic tests."""

from dataclasses import dataclass
from copy import deepcopy


@dataclass
class MockLLMClient:
    responses: dict[str, dict | list[dict]]

    def generate_structured(
        self,
        operation: str,
        prompt: str,
        required_keys: tuple[str, ...],
    ) -> dict:
        response = self.responses[operation]
        if isinstance(response, list):
            if not response:
                raise ValueError(f"no mock responses remaining for operation: {operation}")
            response = response.pop(0)
        missing = [key for key in required_keys if key not in response]
        if missing:
            raise ValueError(f"missing required keys: {missing}")
        return deepcopy(response)
