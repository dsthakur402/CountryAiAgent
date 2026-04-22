"""Thin client for restcountries.com v3.1.

We only use the /name/{name} endpoint - it's enough for the assignment and
keeps the surface area small. If we ever need fuzzy matching we can add
the /alpha or /translation endpoints later.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from config import HTTP_TIMEOUT_S, REST_COUNTRIES_BASE

log = logging.getLogger(__name__)


# maps the vocabulary our Intent uses to the exact REST Countries field paths.
# NOTE: v3.1 uses `capital` (list), `currencies` (dict of code -> {name,symbol}),
# and `languages` (dict of code -> name), which is why synthesis has to
# flatten them in the prompt.
FIELD_MAP: dict[str, str] = {
    "population": "population",
    "capital": "capital",
    "currency": "currencies",
    "languages": "languages",
    "area": "area",
    "region": "region",
    "subregion": "subregion",
    "timezones": "timezones",
    "borders": "borders",
    "flag": "flags",
}

# Always fetched so answers always have a name to refer back to.
DEFAULT_FIELDS = ["name"]


class CountryNotFound(Exception):
    pass


class CountryAPIError(Exception):
    pass


def _api_fields(intent_fields: list[str]) -> list[str]:
    mapped = [FIELD_MAP[f] for f in intent_fields if f in FIELD_MAP]
    return DEFAULT_FIELDS + mapped


_cache: dict[tuple[str, tuple[str, ...]], list[dict[str, Any]]] = {}


def _request(name: str, fields_param: str) -> list[dict[str, Any]]:
    url = f"{REST_COUNTRIES_BASE}/name/{name}"
    params = {"fields": fields_param} if fields_param else {}

    # small retry loop. The API occasionally 503s under load; two quick
    # retries is usually enough and cheap.
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT_S) as client:
                resp = client.get(url, params=params)
            if resp.status_code == 404:
                raise CountryNotFound(name)
            resp.raise_for_status()
            return resp.json()
        except CountryNotFound:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            log.warning("restcountries request failed (attempt %d): %s", attempt + 1, exc)
            time.sleep(0.3 * (2**attempt))

    raise CountryAPIError(f"REST Countries unreachable: {last_exc}")


def _pick_best(results: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """REST Countries often returns multiple matches (e.g. "United" -> 3 countries).

    We prefer an exact case-insensitive match on common or official name,
    otherwise fall back to the first result.
    """
    target = name.strip().lower()
    for item in results:
        nm = item.get("name", {}) or {}
        if (nm.get("common", "") or "").lower() == target:
            return item
        if (nm.get("official", "") or "").lower() == target:
            return item
    return results[0]


def fetch_country(name: str, intent_fields: list[str]) -> dict[str, Any]:
    """Return one country dict for `name`, restricted to the fields we care about.

    Raises CountryNotFound / CountryAPIError.
    """
    name = name.strip()
    if not name:
        raise CountryNotFound("(empty)")

    fields = _api_fields(intent_fields)
    cache_key = (name.lower(), tuple(sorted(fields)))
    if cache_key in _cache:
        return _cache[cache_key][0]

    results = _request(name, ",".join(fields))
    if not results:
        raise CountryNotFound(name)

    best = _pick_best(results, name)
    _cache[cache_key] = [best]
    return best


def clear_cache() -> None:
    _cache.clear()
