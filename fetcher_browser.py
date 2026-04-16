"""
fetcher_browser.py — Browser-based HTTP fetcher using Playwright to bypass Cloudflare.

This replaces cloudscraper with real browser automation.
Much slower but more reliable against Cloudflare challenges.
"""

import os
import time
import random
import hashlib
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

import config

logger = logging.getLogger(__name__)

# Additional browser-like behavior
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class BrowserFetcher:
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._request_count = 0
        self._init_browser()

    def _init_browser(self):
        """Initialize Playwright browser with stealth settings."""
        logger.info("Initializing browser...")
        self._playwright = sync_playwright().start()

        # Launch browser with realistic settings
        self._browser = self._playwright.chromium.launch(
            headless=True,  # Set to False to see browser (useful for debugging)
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        # Create context with realistic settings
        self._context = self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
        )

        # Add realistic headers
        self._context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://basketball.realgm.com/',
        })

        # Create page
        self._page = self._context.new_page()
        logger.info("Browser initialized successfully")

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
        """Sleep between requests with human-like randomness."""
        self._request_count += 1
        if self._request_count % config.BURST_EVERY == 0:
            pause = random.uniform(config.BURST_SLEEP_MIN, config.BURST_SLEEP_MAX)
            logger.info(f"Burst pause: sleeping {pause:.1f}s after {self._request_count} requests")
            time.sleep(pause)
        else:
            # Slightly longer delays for browser requests
            time.sleep(random.uniform(config.SLEEP_MIN + 1, config.SLEEP_MAX + 2))

    def _human_like_delay(self):
        """Add small random delays to mimic human behavior."""
        time.sleep(random.uniform(0.5, 1.5))

    def get(self, url: str, use_cache: bool = True) -> str:
        """
        Fetch a URL using browser automation and return HTML string.
        - Checks local cache first (skip request if cached)
        - Uses real browser to bypass Cloudflare
        - Retries with exponential backoff on transient errors
        - Raises on permanent failure
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
                logger.info(f"GET {url} (attempt {attempt}) [BROWSER]")

                # Navigate to page
                response = self._page.goto(url, timeout=60000, wait_until='domcontentloaded')

                if response is None:
                    raise RuntimeError(f"No response received for {url}")

                # Check status code
                if response.status == 404:
                    raise FileNotFoundError(f"404 Not Found: {url}")

                if response.status == 403:
                    logger.warning(f"403 Forbidden: {url} — waiting for Cloudflare challenge")
                    # Wait for Cloudflare challenge to resolve
                    self._human_like_delay()
                    # Try waiting for network to be idle (Cloudflare solved)
                    try:
                        self._page.wait_for_load_state('networkidle', timeout=30000)
                    except PlaywrightTimeout:
                        logger.warning("Timeout waiting for Cloudflare challenge, continuing anyway")

                    # Check if we're still on a challenge page
                    html = self._page.content()
                    if 'Just a moment' in html or 'cf-wrapper' in html:
                        if attempt == config.MAX_RETRIES:
                            raise PermissionError(f"403 Forbidden after {attempt} attempts: {url}")
                        logger.warning(f"Still on Cloudflare challenge page, retrying...")
                        time.sleep(sleep)
                        sleep *= 2
                        continue

                if response.status != 200:
                    logger.warning(f"HTTP {response.status}: {url}")
                    if response.status in (429, 500, 502, 503, 504):
                        if attempt < config.MAX_RETRIES:
                            logger.warning(f"Backing off {sleep}s")
                            time.sleep(sleep)
                            sleep *= 2
                            continue
                    else:
                        raise RuntimeError(f"Unexpected HTTP {response.status}: {url}")

                # Get page content
                html = self._page.content()

                # Check if we got actual content (not a Cloudflare challenge)
                if 'Just a moment' in html or len(html) < 1000:
                    logger.warning(f"Received Cloudflare challenge or minimal content")
                    if attempt < config.MAX_RETRIES:
                        time.sleep(sleep)
                        sleep *= 2
                        continue
                    else:
                        raise RuntimeError(f"Still blocked by Cloudflare after {config.MAX_RETRIES} attempts")

                # Success! Save to cache
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(html)

                logger.info(f"Successfully fetched {url} ({len(html)} bytes)")
                return html

            except PlaywrightTimeout as e:
                logger.warning(f"Timeout on {url}: {e}")
                last_error = e
                if attempt < config.MAX_RETRIES:
                    time.sleep(sleep)
                    sleep *= 2
                else:
                    raise RuntimeError(f"Timeout after {config.MAX_RETRIES} attempts: {url}")

            except Exception as e:
                cls = type(e).__name__
                if cls in ("Error", "TimeoutError"):
                    logger.warning(f"Browser error on {url}: {e}")
                    last_error = e
                    if attempt < config.MAX_RETRIES:
                        time.sleep(sleep)
                        sleep *= 2
                    else:
                        raise RuntimeError(f"Browser error after {config.MAX_RETRIES} attempts: {url}")
                else:
                    # Re-raise unexpected errors
                    raise

        raise RuntimeError(f"Failed to fetch {url} after {config.MAX_RETRIES} attempts. Last error: {last_error}")

    def get_paginated_listing(self, url: str, max_pages: int = 100) -> list:
        """
        Fetch a multi-page listing by clicking through pagination.
        Returns list of HTML strings, one per page.

        For JavaScript-based pagination where URL manipulation doesn't work.
        Clicks through pagination buttons to get all pages.
        """
        logger.info(f"Fetching paginated listing: {url} (up to {max_pages} pages)")

        # Rate limit before starting
        self._rate_limit()

        html_pages = []

        try:
            # Load first page
            logger.info(f"Loading page 1...")
            response = self._page.goto(url, timeout=60000, wait_until='domcontentloaded')

            if response and response.status != 200:
                logger.error(f"HTTP {response.status} for {url}")
                return html_pages

            # Wait for table to load
            try:
                self._page.wait_for_selector('table tbody', timeout=10000)
            except PlaywrightTimeout:
                logger.warning("Table didn't load, returning empty")
                return html_pages

            # Get page 1 HTML
            html_pages.append(self._page.content())
            logger.info(f"  Page 1: captured")

            # Check if pagination exists
            try:
                pagination = self._page.query_selector('ul.pagination')
                if not pagination:
                    logger.info("No pagination found, single page only")
                    return html_pages

                # Find max page number from pagination
                page_links = pagination.query_selector_all('a')
                page_numbers = []
                for link in page_links:
                    text = link.inner_text().strip()
                    if text.isdigit():
                        page_numbers.append(int(text))

                if not page_numbers:
                    logger.info("No page numbers found in pagination")
                    return html_pages

                actual_max = min(max(page_numbers), max_pages)
                logger.info(f"Found {actual_max} total pages")

                # Click through pages 2 to max
                for page_num in range(2, actual_max + 1):
                    try:
                        # Small delay between pages
                        time.sleep(random.uniform(1.5, 3.0))

                        logger.info(f"  Clicking page {page_num}...")

                        # Try to click the page number
                        # Look for link with exact text match
                        page_link = self._page.query_selector(f'ul.pagination a:has-text("{page_num}")')

                        if not page_link:
                            logger.warning(f"  Page {page_num} link not found, stopping")
                            break

                        # Click and wait for navigation/content update
                        page_link.click()

                        # Wait for table to update (small delay)
                        time.sleep(random.uniform(0.5, 1.0))

                        # Get the updated HTML
                        html = self._page.content()
                        html_pages.append(html)
                        logger.info(f"  Page {page_num}: captured")

                    except Exception as e:
                        logger.error(f"  Page {page_num} error: {e}")
                        break

            except Exception as e:
                logger.error(f"Pagination error: {e}")

        except Exception as e:
            logger.error(f"Failed to fetch paginated listing: {e}")

        logger.info(f"Fetched {len(html_pages)} pages total")
        return html_pages

    def close(self):
        """Clean up browser resources."""
        if self._page:
            self._page.close()
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("Browser closed")


# Module-level singleton
_fetcher = None


def get(url: str, use_cache: bool = True) -> str:
    global _fetcher
    if _fetcher is None:
        _fetcher = BrowserFetcher()
    return _fetcher.get(url, use_cache=use_cache)


def get_paginated_listing(url: str, max_pages: int = 100) -> list:
    """
    Get all pages of a paginated listing by clicking through pagination.
    Returns list of HTML strings, one per page.
    """
    global _fetcher
    if _fetcher is None:
        _fetcher = BrowserFetcher()
    return _fetcher.get_paginated_listing(url, max_pages=max_pages)


def close():
    """Close the browser fetcher."""
    global _fetcher
    if _fetcher is not None:
        _fetcher.close()
        _fetcher = None
