from unittest.mock import patch

import httpx
import pytest

from agent import countries_api
from agent.countries_api import (
    CountryAPIError,
    CountryNotFound,
    _api_fields,
    _pick_best,
    fetch_country,
)


def setup_function(_):
    countries_api.clear_cache()


def test_api_fields_maps_intent_vocab():
    fields = _api_fields(["population", "currency", "flag", "bogus"])
    assert "name" in fields
    assert "population" in fields
    assert "currencies" in fields
    assert "flags" in fields
    assert "bogus" not in fields


def test_pick_best_prefers_exact_common_name_match():
    results = [
        {"name": {"common": "United States", "official": "United States of America"}},
        {"name": {"common": "United Kingdom", "official": "United Kingdom of GB"}},
    ]
    chosen = _pick_best(results, "united kingdom")
    assert chosen["name"]["common"] == "United Kingdom"


def test_pick_best_falls_back_to_first():
    results = [{"name": {"common": "A"}}, {"name": {"common": "B"}}]
    assert _pick_best(results, "zzz")["name"]["common"] == "A"


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=None)


def test_fetch_country_happy_path():
    payload = [{"name": {"common": "Germany"}, "population": 83000000}]

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            return _Resp(200, payload)

    with patch.object(countries_api.httpx, "Client", FakeClient):
        result = fetch_country("Germany", ["population"])
    assert result["population"] == 83000000


def test_fetch_country_404():
    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            return _Resp(404, {"status": 404})

    with patch.object(countries_api.httpx, "Client", FakeClient):
        with pytest.raises(CountryNotFound):
            fetch_country("Narnia", [])


def test_fetch_country_network_error_becomes_api_error():
    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            raise httpx.ConnectError("no network")

    with patch.object(countries_api.httpx, "Client", FakeClient), patch.object(
        countries_api.time, "sleep", lambda *_: None
    ):
        with pytest.raises(CountryAPIError):
            fetch_country("Germany", [])
