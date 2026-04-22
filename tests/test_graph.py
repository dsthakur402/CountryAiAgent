from unittest.mock import MagicMock, patch

from agent import countries_api
from agent.graph import build_graph
from agent.schema import Intent


def _fake_llm_structured(intent: Intent):
    """Patch target for the intent LLM call."""
    m = MagicMock()
    m.invoke.return_value = intent
    return m


def _fake_llm_chat(text: str):
    """Patch target for the synthesis LLM call."""
    m = MagicMock()
    resp = MagicMock()
    resp.content = text
    m.invoke.return_value = resp
    return m


def setup_function(_):
    countries_api.clear_cache()


def test_happy_path_germany_population():
    intent = Intent(countries=["Germany"], fields=["population"])
    structured_llm = _fake_llm_structured(intent)
    chat_llm = _fake_llm_chat("Germany has a population of 83,000,000.")

    with patch("agent.nodes.get_llm") as get_llm, patch(
        "agent.countries_api.fetch_country"
    ) as fetch:
        base_llm = MagicMock()
        base_llm.with_structured_output.return_value = structured_llm
        get_llm.side_effect = lambda *a, **kw: (
            base_llm if kw.get("temperature", 0.2) == 0 else chat_llm
        )
        fetch.return_value = {"name": {"common": "Germany"}, "population": 83000000}

        graph = build_graph()
        final = graph.invoke({"question": "What is the population of Germany?"})

    assert "83,000,000" in final["answer"]
    assert final["intent"].countries == ["Germany"]


def test_unknown_country_short_circuits_synthesis():
    intent = Intent(countries=["Narnia"], fields=["population"])
    structured_llm = _fake_llm_structured(intent)

    with patch("agent.nodes.get_llm") as get_llm, patch(
        "agent.countries_api.fetch_country"
    ) as fetch:
        base_llm = MagicMock()
        base_llm.with_structured_output.return_value = structured_llm
        get_llm.return_value = base_llm
        fetch.side_effect = countries_api.CountryNotFound("Narnia")

        graph = build_graph()
        final = graph.invoke({"question": "What is the population of Narnia?"})

    assert "Narnia" in final["answer"]
    assert final["country_data"] == []
