from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from . import countries_api
from .llm import get_llm
from .prompts import INTENT_SYSTEM, SYNTH_SYSTEM
from .schema import SUPPORTED_FIELDS, Intent
from .state import AgentState

log = logging.getLogger(__name__)


# very loose fallback if the LLM's structured output call fails for any reason.
# It won't catch everything, but it keeps the graph alive.
_CAPWORD = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\b")


def _fallback_intent(question: str) -> Intent:
    candidates = _CAPWORD.findall(question)
    # drop obvious non-country starters
    stop = {"What", "Which", "Tell", "How", "Who", "Is", "Does", "The", "And"}
    countries = [c for c in candidates if c.split()[0] not in stop]
    return Intent(countries=countries[:3], fields=[])


def parse_intent(state: AgentState) -> dict[str, Any]:
    question = state["question"]
    t0 = time.perf_counter()

    try:
        llm = get_llm(temperature=0).with_structured_output(Intent)
        intent: Intent = llm.invoke(
            [SystemMessage(content=INTENT_SYSTEM), HumanMessage(content=question)]
        )
    except Exception as exc:
        log.warning("intent LLM call failed, using regex fallback: %s", exc)
        intent = _fallback_intent(question)

    intent.fields = [f for f in intent.fields if f in SUPPORTED_FIELDS]

    log.info(
        "parse_intent q=%r countries=%s fields=%s (%.2fs)",
        question,
        intent.countries,
        intent.fields,
        time.perf_counter() - t0,
    )
    return {"intent": intent}


def fetch_country(state: AgentState) -> dict[str, Any]:
    intent: Intent | None = state.get("intent")
    if intent is None or not intent.countries:
        return {
            "country_data": [],
            "error": "I couldn't tell which country you're asking about. "
            "Try naming it directly, e.g. 'What is the population of Japan?'",
        }

    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for name in intent.countries:
        try:
            results.append(countries_api.fetch_country(name, intent.fields))
        except countries_api.CountryNotFound:
            errors.append(f"No country matched '{name}'.")
        except countries_api.CountryAPIError as exc:
            errors.append(f"Lookup failed for '{name}': {exc}")

    log.info(
        "fetch_country hits=%d misses=%d", len(results), len(errors)
    )

    # Return whatever we got. Synthesis handles the partial-data case.
    err = " ".join(errors) if errors and not results else (" ".join(errors) or None)
    return {"country_data": results, "error": err}


def synthesize_answer(state: AgentState) -> dict[str, Any]:
    question = state["question"]
    data = state.get("country_data") or []
    error = state.get("error")

    if not data and error:
        # no point spending an LLM call on this - the error message is fine.
        return {"answer": error}

    payload = {
        "question": question,
        "countries": data,
        "note": error or "",
    }

    try:
        llm = get_llm(temperature=0.2)
        resp = llm.invoke(
            [
                SystemMessage(content=SYNTH_SYSTEM),
                HumanMessage(
                    content="Data:\n```json\n"
                    + json.dumps(payload, ensure_ascii=False, indent=2)
                    + "\n```\n\nAnswer the question."
                ),
            ]
        )
        answer = (resp.content or "").strip()
    except Exception as exc:
        log.exception("synthesis failed")
        answer = f"Sorry, I hit an error while writing the answer: {exc}"

    return {"answer": answer}
