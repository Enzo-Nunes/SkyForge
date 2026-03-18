import logging
import time
from typing import Any

import requests

DEFAULT_HTTP_TIMEOUT = 15
HTTP_RETRIES = 3
HTTP_BACKOFF_SECONDS = 1.5
RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def request_with_retry(
    logger: logging.Logger,
    method: str,
    url: str,
    *,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
    retries: int = HTTP_RETRIES,
    backoff_seconds: float = HTTP_BACKOFF_SECONDS,
    retriable_status_codes: set[int] = RETRIABLE_STATUS_CODES,
    **kwargs: Any,
) -> requests.Response:
    for attempt in range(1, retries + 1):
        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
            if response.status_code in retriable_status_codes and attempt < retries:
                wait_seconds = backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    f"{method} {url} returned {response.status_code} "
                    f"(attempt {attempt}/{retries}), retrying in {wait_seconds:.1f}s..."
                )
                time.sleep(wait_seconds)
                continue
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            should_retry = status_code in retriable_status_codes
            if attempt >= retries or not should_retry:
                raise
            wait_seconds = backoff_seconds * (2 ** (attempt - 1))
            logger.warning(
                f"{method} {url} failed with HTTP {status_code} "
                f"(attempt {attempt}/{retries}), retrying in {wait_seconds:.1f}s..."
            )
            time.sleep(wait_seconds)
        except requests.exceptions.RequestException as e:
            if attempt >= retries:
                raise
            wait_seconds = backoff_seconds * (2 ** (attempt - 1))
            logger.warning(
                f"{method} {url} failed ({e}) (attempt {attempt}/{retries}), retrying in {wait_seconds:.1f}s..."
            )
            time.sleep(wait_seconds)

    raise RuntimeError("Unreachable")
