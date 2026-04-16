"""
fetcher.py — HTTP session with Cloudflare bypass, caching, rate limiting, retry logic.

RealGM uses Cloudflare's managed JS challenge on some pages (e.g. player listings).
`cloudscraper` solves that challenge transparently — it's a drop-in for `requests`.
"""

import os
import time
import random
import hashlib
import logging

import cloudscraper

import config

logger = logging.getLogger(__name__)

# Additional browser-like headers on top of what cloudscraper sets by default
EXTRA_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://basketball.realgm.com/",
    "DNT": "1",
}


class Fetcher:
    def __init__(self):
        self._scraper = self._new_scraper()
        self._request_count = 0

    def _new_scraper(self):
        """
        cloudscraper.create_scraper() returns a requests.Session subclass that
        automatically handles Cloudflare IUAM / JS challenges.
        browser='chrome' instructs it to mimic Chrome's TLS fingerprint.
        """
        s = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "darwin",
                "mobile": False,
            }
        )
        s.headers.update(EXTRA_HEADERS)
        return s

    def _cache_path(self, url: str) -> str:
        """Map a URL to a local cache file path."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        if "/ncaa/players" in url and "/player/" not in url:
            subdir = config.RAW_LISTINGS
        else:
            subdir = config.RAW_PLAYERS
        os.makedirs(subdir, exist_ok=True)
        return os.path.join(subdir, f"{url_hash}.html")

    def _rate_limit(self):
        """Sleep between requests. Burst pause every N requests."""
        self._request_count += 1
        if self._request_count % config.BURST_EVERY == 0:
            pause = random.uniform(config.BURST_SLEEP_MIN, config.BURST_SLEEP_MAX)
            logger.info(f"Burst pause: sleeping {pause:.1f}s after {self._request_count} requests")
            time.sleep(pause)
        else:
            time.sleep(random.uniform(config.SLEEP_MIN, config.SLEEP_MAX))

    def get(self, url: str, use_cache: bool = True) -> str:
        """
        Fetch a URL and return HTML string.
        - Checks local cache first (skip request if cached)
        - Retries with exponential backoff on transient errors
        - Raises on permanent failure (403 after retry, 404)
        """
        cache_path = self._cache_path(url)

        # Return from cache if available
        if use_cache and os.path.exists(cache_path):
            logger.debug(f"Cache hit: {url}")
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()

        # Rate limit before making request
        self._rate_limit()

        sleep = config.RETRY_BASE_SLEEP
        last_error = None

        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                logger.info(f"GET {url} (attempt {attempt})")
                resp = self._scraper.get(url, timeout=30)

                if resp.status_code == 200:
                    html = resp.text
                    # Save to cache
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    return html

                elif resp.status_code == 404:
                    raise FileNotFoundError(f"404 Not Found: {url}")

                elif resp.status_code == 403:
                    logger.warning(f"403 Forbidden: {url} — refreshing scraper session")
                    self._scraper = self._new_scraper()
                    if attempt == config.MAX_RETRIES:
                        raise PermissionError(f"403 Forbidden after {attempt} attempts: {url}")

                elif resp.status_code in (429, 500, 502, 503, 504):
                    logger.warning(f"HTTP {resp.status_code}: {url} — backing off {sleep}s")

                else:
                    raise RuntimeError(f"Unexpected HTTP {resp.status_code}: {url}")

            except (cloudscraper.exceptions.CloudflareChallengeError,
                    cloudscraper.exceptions.CloudflareIUAMError) as e:
                logger.warning(f"Cloudflare challenge on {url}: {e} — backing off {sleep}s")
                last_error = e

            except Exception as e:
                # Catch requests.ConnectionError, Timeout, etc.
                cls = type(e).__name__
                if cls in ("ConnectionError", "Timeout", "ReadTimeout"):
                    logger.warning(f"Network error on {url}: {e} — backing off {sleep}s")
                    last_error = e
                else:
                    raise  # re-raise unexpected errors immediately

            # Exponential backoff before retry
            if attempt < config.MAX_RETRIES:
                time.sleep(sleep)
                sleep *= 2

        raise RuntimeError(f"Failed to fetch {url} after {config.MAX_RETRIES} attempts. Last error: {last_error}")


# Module-level singleton
_fetcher = None


def get(url: str, use_cache: bool = True) -> str:
    global _fetcher
    if _fetcher is None:
        _fetcher = Fetcher()
    return _fetcher.get(url, use_cache=use_cache)
