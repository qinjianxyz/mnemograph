import json

import httpx

from mnemograph.llm.client import OpenAICompatibleLLMClient, render_structured_output
from mnemograph.llm.mock import MockLLMClient


def test_mock_llm_client_returns_schema_valid_payload():
    client = MockLLMClient(
        responses={
            "extract": {
                "entities": [],
                "claims": [],
            }
        }
    )

    result = client.generate_structured(
        operation="extract",
        prompt="Extract claims",
        required_keys=("entities", "claims"),
    )

    assert result == {"entities": [], "claims": []}


def test_mock_llm_client_supports_sequential_outputs():
    client = MockLLMClient(
        responses={
            "extract": [
                {"entities": [], "claims": []},
                {"entities": [{"entity_id": "Company:Acme"}], "claims": []},
            ]
        }
    )

    first = client.generate_structured("extract", "first", ("entities", "claims"))
    second = client.generate_structured("extract", "second", ("entities", "claims"))

    assert first == {"entities": [], "claims": []}
    assert second == {"entities": [{"entity_id": "Company:Acme"}], "claims": []}


def test_openai_compatible_client_reads_config_without_network(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    client = OpenAICompatibleLLMClient(model="gpt-5.4")

    assert client.model == "gpt-5.4"
    assert client.api_key == "test-key"


def test_openai_compatible_client_posts_structured_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert request.headers["Authorization"] == "Bearer test-key"
        assert request.url == httpx.URL("http://localhost:11434/v1/chat/completions")
        assert payload["model"] == "gpt-5.4"
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"entities": [], "claims": []}',
                        }
                    }
                ]
            },
        )

    client = OpenAICompatibleLLMClient(
        model="gpt-5.4",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.generate_structured(
        operation="extract",
        prompt="Extract claims",
        required_keys=("entities", "claims"),
    )

    assert result == {"entities": [], "claims": []}


def test_openai_compatible_client_retries_once_on_json_parse_failure(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(200, json={"response": "not json"})
        return httpx.Response(
            200,
            json={"response": '{"mode": "STRUCTURED_LOOKUP", "entities": []}'},
        )

    client = OpenAICompatibleLLMClient(
        model="qwen3.5:latest",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.generate_structured(
        operation="classify",
        prompt="Classify this query",
        required_keys=("mode", "entities"),
    )

    assert client.api_key == "ollama"
    assert calls["count"] == 2
    assert result["mode"] == "STRUCTURED_LOOKUP"


def test_openai_compatible_client_uses_native_ollama_for_local_models(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert request.url == httpx.URL("http://localhost:11434/api/generate")
        assert payload["model"] == "qwen3.5:latest"
        assert payload["format"] == "json"
        assert payload["think"] is False
        assert payload["options"]["temperature"] == 0
        return httpx.Response(
            200,
            json={"response": '{"entities": [], "claims": [], "evidence_spans": []}'},
        )

    client = OpenAICompatibleLLMClient(
        model="qwen3.5:latest",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.generate_structured(
        operation="extract",
        prompt="Extract claims",
        required_keys=("entities", "claims", "evidence_spans"),
    )

    assert result == {"entities": [], "claims": [], "evidence_spans": []}


def test_native_ollama_retry_asks_for_shorter_json_after_parse_failure(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    prompts: list[str] = []
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        payload = json.loads(request.content.decode("utf-8"))
        prompts.append(payload["prompt"])
        if calls["count"] == 1:
            return httpx.Response(200, json={"response": '{"entities": ['})
        return httpx.Response(
            200,
            json={"response": '{"entities": [], "claims": [], "evidence_spans": []}'},
        )

    client = OpenAICompatibleLLMClient(
        model="qwen3.5:latest",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    result = client.generate_structured(
        operation="extract",
        prompt="Extract claims",
        required_keys=("entities", "claims", "evidence_spans"),
    )

    assert result == {"entities": [], "claims": [], "evidence_spans": []}
    assert calls["count"] == 2
    assert prompts[0] != prompts[1]
    assert "Return a shorter JSON response" in prompts[1]


def test_extraction_and_retrieval_callers_can_share_the_same_interface(monkeypatch):
    mock_client = MockLLMClient(
        responses={
            "extract": {"entities": [], "claims": []},
            "classify": {"mode": "STRUCTURED_LOOKUP", "entities": ["Acme"]},
        }
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    openai_client = OpenAICompatibleLLMClient(model="gpt-5.4")

    assert render_structured_output(
        mock_client, "extract", "Extract", ("entities", "claims")
    ) == {"entities": [], "claims": []}
    assert render_structured_output(
        mock_client, "classify", "Classify", ("mode", "entities")
    ) == {"mode": "STRUCTURED_LOOKUP", "entities": ["Acme"]}
    assert openai_client.api_key == "test-key"
