import json

import pytest
import requests

from steelmen.io import cache


class FakeResponse:
    def __init__(self, status_code: int, text: str = "", url: str = "http://x"):
        self.status_code = status_code
        self.text = text
        self.url = url


def test_cache_hit_never_touches_network(tmp_path, monkeypatch):
    path = tmp_path / "a.json"
    path.write_text('{"cached": true}')

    def boom(*args, **kwargs):
        raise AssertionError("network touched")

    monkeypatch.setattr(cache.requests, "get", boom)
    assert cache.cached_get_json("http://x", cache_path=path) == {"cached": True}


def test_force_refetches_and_writes(tmp_path, monkeypatch):
    path = tmp_path / "a.json"
    path.write_text('{"cached": true}')
    monkeypatch.setattr(cache.requests, "get", lambda *a, **k: FakeResponse(200, '{"fresh": 1}'))
    assert cache.cached_get_json("http://x", cache_path=path, force=True) == {"fresh": 1}
    assert json.loads(path.read_text()) == {"fresh": 1}


def test_user_agent_is_sent(tmp_path, monkeypatch):
    seen = {}

    def fake_get(url, params=None, timeout=None, headers=None):
        seen["headers"] = headers
        return FakeResponse(200, "{}")

    monkeypatch.setattr(cache.requests, "get", fake_get)
    cache.cached_get_json("http://x", cache_path=tmp_path / "a.json")
    assert seen["headers"]["User-Agent"] == cache.USER_AGENT


def test_4xx_fails_fast(tmp_path, monkeypatch):
    calls = []

    def fake_get(*a, **k):
        calls.append(1)
        return FakeResponse(404)

    monkeypatch.setattr(cache.requests, "get", fake_get)
    with pytest.raises(cache.FetchError):
        cache.cached_get_text("http://x", cache_path=tmp_path / "a.txt")
    assert len(calls) == 1


def test_5xx_retries_then_raises(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cache.time, "sleep", lambda s: None)

    def fake_get(*a, **k):
        calls.append(1)
        return FakeResponse(503)

    monkeypatch.setattr(cache.requests, "get", fake_get)
    with pytest.raises(cache.FetchError):
        cache.cached_get_text("http://x", cache_path=tmp_path / "a.txt", max_retries=3)
    assert len(calls) == 3


def test_network_error_retries(tmp_path, monkeypatch):
    monkeypatch.setattr(cache.time, "sleep", lambda s: None)
    attempts = iter([requests.ConnectionError("boom"), FakeResponse(200, "ok")])

    def fake_get(*a, **k):
        item = next(attempts)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(cache.requests, "get", fake_get)
    assert cache.cached_get_text("http://x", cache_path=tmp_path / "a.txt") == "ok"


def test_invalid_json_raises_and_clears_cache(tmp_path, monkeypatch):
    path = tmp_path / "a.json"
    monkeypatch.setattr(cache.requests, "get", lambda *a, **k: FakeResponse(200, "not json"))
    with pytest.raises(cache.FetchError):
        cache.cached_get_json("http://x", cache_path=path)
    assert not path.exists()
