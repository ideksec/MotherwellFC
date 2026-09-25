"""Cache-first HTTP fetching.

Every fetch is keyed to a path under data/raw/ (gitignored). If the file
exists the network is never touched, which keeps runs reproducible and
request volume polite. Writes are atomic (tmp file + rename) so a crash
mid-download never leaves a truncated cache entry.
"""

import json
import os
import time
from pathlib import Path

import requests

DATA_RAW = Path("data/raw")
USER_AGENT = "steelmen (github.com/ideksec/MotherwellFC)"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3


class FetchError(RuntimeError):
    """A request failed after retries, or returned an unusable body."""


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _get_with_retries(
    url: str, *, params: dict | None, timeout: float, max_retries: int
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT}
            )
        except requests.RequestException as err:
            last_error = err
        else:
            if response.status_code < 400:
                return response
            if response.status_code < 500:
                raise FetchError(f"{response.status_code} for {response.url}")
            last_error = FetchError(f"{response.status_code} for {response.url}")
        if attempt < max_retries - 1:
            time.sleep(2**attempt)
    raise FetchError(f"Giving up on {url}: {last_error}")


def cached_get_text(
    url: str,
    *,
    params: dict | None = None,
    cache_path: Path,
    force: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> str:
    """Return the response body, from cache when available."""
    if cache_path.exists() and not force:
        return cache_path.read_text()
    response = _get_with_retries(url, params=params, timeout=timeout, max_retries=max_retries)
    _atomic_write_text(cache_path, response.text)
    return response.text


def cached_get_json(
    url: str,
    *,
    params: dict | None = None,
    cache_path: Path,
    force: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> dict:
    text = cached_get_text(
        url,
        params=params,
        cache_path=cache_path,
        force=force,
        timeout=timeout,
        max_retries=max_retries,
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError as err:
        cache_path.unlink(missing_ok=True)
        raise FetchError(f"Invalid JSON from {url}: {err}") from err
