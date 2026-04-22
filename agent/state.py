from typing import Any, Optional, TypedDict

from .schema import Intent


class AgentState(TypedDict, total=False):
    question: str
    intent: Optional[Intent]
    country_data: list[dict[str, Any]]
    error: Optional[str]
    answer: str
