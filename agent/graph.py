from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from .nodes import fetch_country, parse_intent, synthesize_answer
from .state import AgentState


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("parse_intent", parse_intent)
    g.add_node("fetch_country", fetch_country)
    g.add_node("synthesize_answer", synthesize_answer)

    g.add_edge(START, "parse_intent")
    g.add_edge("parse_intent", "fetch_country")
    g.add_edge("fetch_country", "synthesize_answer")
    g.add_edge("synthesize_answer", END)
    return g.compile()


@lru_cache(maxsize=1)
def _compiled():
    return build_graph()


def run(question: str) -> dict:
    """Convenience wrapper - invoke the graph on a single question and return the final state."""
    return _compiled().invoke({"question": question})
