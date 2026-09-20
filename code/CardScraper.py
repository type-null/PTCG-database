"""
    Scrape card info

    Shared HTTP plumbing and bookkeeping for every language scraper.

    April 23, 2024 by Weihang
"""

import json
import random
import re
import time
from datetime import datetime
from pathlib import Path

import bs4
import paths
import requests
from loguru import logger

#: Sent on every request. Some sources answer a stale browser string with an
#: anti-bot challenge page instead of the card, so keep this current.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8,zh-TW;q=0.7,ko;q=0.6",
    "Connection": "keep-alive",
}

#: Markers of an anti-bot interstitial served instead of the real page.
CHALLENGE_MARKERS = ("RunProofOfWork", "Checking your browser", "cf-browser-verification")

#: One source answers the modern user agent above with a proof-of-work page
#: but serves this older one normally, so it is worth falling back to.
ALT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:68.0) Gecko/20100101 Firefox/68.0"


class ScrapeError(Exception):
    """A page could not be fetched after every retry."""


class CardScraper:
    #: Seconds to wait between two requests, so a long run stays polite.
    delay = 1.0
    #: Extra random delay on top of `delay`, to avoid a machine-gun cadence.
    jitter = 0.4
    #: Attempts per URL before giving up.
    retries = 6
    timeout = 30

    #: Set by a scraper whose site insists on a particular user agent.
    user_agent = None

    def __init__(self, delay=None):
        if delay is not None:
            self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        if self.user_agent:
            self.session.headers["User-Agent"] = self.user_agent
        self._next_request_at = 0.0

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _wait_turn(self):
        """Sleep until this scraper is allowed to make its next request."""
        now = time.monotonic()
        if now < self._next_request_at:
            time.sleep(self._next_request_at - now)
        self._next_request_at = time.monotonic() + self.delay + random.uniform(0, self.jitter)

    def fetch(self, url, params=None):
        """Return the decoded body of `url`, or None if it is unreachable.

        Retries on timeouts, connection drops and server errors with a
        widening back-off, and honours `Retry-After` on 429.
        """
        for attempt in range(1, self.retries + 1):
            self._wait_turn()
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as error:
                logger.warning(f"{url} failed ({error.__class__.__name__}), attempt {attempt}")
                self._back_off(attempt)
                continue

            if response.status_code == 412 or any(
                marker in response.text for marker in CHALLENGE_MARKERS
            ):
                # The site wants a browser to prove itself. It accepts the
                # other user agent, so swap before trying again.
                logger.warning(f"{url} returned an anti-bot challenge, attempt {attempt}")
                self._swap_user_agent()
                self._back_off(attempt)
                continue

            if response.status_code == 200:
                logger.debug(f"Got content from {url}")
                return response.text

            if response.status_code == 429:
                pause = float(response.headers.get("Retry-After", 30))
                logger.warning(f"Rate limited on {url}; sleeping {pause:.0f}s")
                time.sleep(pause)
                continue

            if response.status_code >= 500 or response.status_code == 403:
                # 403 is how one of the sources throttles a burst of requests;
                # it clears on its own, so treat it as worth retrying.
                logger.warning(f"{url} returned {response.status_code}, attempt {attempt}")
                self._back_off(attempt)
                continue

            # 404 and friends are answers, not failures: the card is absent.
            logger.debug(f"{url} returned {response.status_code}")
            return None

        logger.error(f"Giving up on {url} after {self.retries} attempts")
        return None

    def _back_off(self, attempt):
        time.sleep(min(2**attempt, 60))

    def _swap_user_agent(self):
        """Move to the other user agent after an anti-bot challenge."""
        current = self.session.headers.get("User-Agent")
        self.session.headers["User-Agent"] = (
            ALT_USER_AGENT if current != ALT_USER_AGENT else HEADERS["User-Agent"]
        )

    def read_card_safely(self, identifier, default=None, **kwargs):
        """Read one card, turning an unexpected failure into a skipped card.

        A single card with markup nobody has seen before should cost that
        card, not the thousands still queued behind it.
        """
        try:
            return self.read_card(identifier, **kwargs)
        except Exception:
            logger.exception(f"Card {identifier} could not be read")
            return default

    def get_content(self, url):
        """Backwards-compatible alias of `fetch`."""
        return self.fetch(url)

    def get_soup(self, url, params=None):
        """Fetch `url` and parse it, or return None if it is unreachable."""
        content = self.fetch(url, params=params)
        if content is None:
            return None
        return bs4.BeautifulSoup(content, "html.parser")

    def get_json(self, url, params=None):
        """Fetch `url` and parse it as JSON, or return None."""
        content = self.fetch(url, params=params)
        if content is None:
            return None
        try:
            return json.loads(content)
        except ValueError:
            logger.error(f"{url} did not return JSON")
            return None

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def read_attack_damage(self, damage_str):
        """Split '80+' into its amount and suffix."""
        match = re.match(r"(?P<amount>\d+)(?P<suffix>\W?)", damage_str)
        if match:
            return {"amount": int(match.group("amount")), "suffix": match.group("suffix")}
        return None

    # ------------------------------------------------------------------
    # Bookkeeping
    # ------------------------------------------------------------------

    def get_downloaded_set_list(self, lang="en"):
        """Set names already scraped, according to the log."""
        path = paths.log_file(f"scraped_{lang}_set_list.txt")
        if not path.exists():
            return set()
        return {line.strip() for line in path.read_text().splitlines() if line.strip()}

    def get_downloaded_id_list(self, lang="jp"):
        """Card ids already scraped, according to the log."""
        path = paths.log_file(f"scraped_{lang}_id_list.txt")
        if not path.exists():
            return set()
        ids = set()
        for line in path.read_text().splitlines():
            line = line.strip()
            if line.isdigit():
                ids.add(int(line))
        return ids

    def save_list_to_file(self, array, output_file):
        """Append entries that are not in `output_file` yet."""
        path = paths.log_file(Path(output_file).name)
        known = set()
        if path.exists():
            known = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
        new = [str(item) for item in array if str(item) not in known]
        if not new:
            return
        with open(path, "a", encoding="utf-8") as file:
            file.writelines(item + "\n" for item in new)

    def update_readme(self, last_id, lang="jp"):
        """Stamp the README with this run's date and last card id."""
        if not paths.README.exists():
            return
        lines = paths.README.read_text(encoding="utf-8").splitlines(keepends=True)
        date_pattern = re.compile(rf"Last {lang} downloaded time: .+")
        id_pattern = re.compile(rf"Last {lang} downloaded card_id: \S+")
        today = datetime.now().strftime("%B %d, %Y")

        with open(paths.README, "w", encoding="utf-8") as file:
            for line in lines:
                if date_pattern.search(line):
                    line = f"\t\t- Last {lang} downloaded time: {today}\n"
                elif id_pattern.search(line):
                    line = f"\t\t- Last {lang} downloaded card_id: {last_id}\n"
                file.write(line)

    #: Kept so older scripts calling the misspelled name keep working.
    upadte_readme = update_readme
