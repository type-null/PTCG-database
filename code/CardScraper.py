"""
    Scrape card info

    April 23, 2024 by Weihang
"""

import re
import time
import requests
from tqdm import tqdm
from datetime import datetime

import logging

# Disable the logging from `connectionpool`
url_logger = logging.getLogger("urllib3")
url_logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class CardScraper:
    def __init__(self):
        pass

    # Statuses worth another attempt: transient server-side or throttling.
    RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
    MAX_ATTEMPTS = 3
    BACKOFF_SECONDS = (2, 5)
    TIMEOUT_SECONDS = 30

    def get_content(self, url):
        """
        Fetch a page, returning its decoded body, or None if it could not be
        fetched.

        Returns None rather than the old `[url, status_code]`: no caller
        anywhere in this codebase ever checked for that list, so every one of
        them passed it straight into a parser and died with a TypeError. A
        single transient 503 mid-run therefore killed the whole scrape and
        discarded its bookkeeping. Callers must treat None as "no page".
        """
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:68.0) Gecko/20100101 Firefox/68.0"
        )

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                response = requests.get(
                    url,
                    headers={"User-Agent": user_agent},
                    timeout=self.TIMEOUT_SECONDS,
                )
            except requests.RequestException as exc:
                logger.warning(f"Network error on {url} (attempt {attempt}): {exc}")
            else:
                if response.status_code == 200:
                    logger.debug(f"Got content from {url}")
                    return response.content.decode("utf-8")

                logger.warning(
                    f"Fail to get {url} (attempt {attempt}): {response.status_code}"
                )
                if response.status_code not in self.RETRY_STATUSES:
                    # 404 and friends are answers, not failures. Do not retry.
                    return None

            if attempt < self.MAX_ATTEMPTS:
                time.sleep(self.BACKOFF_SECONDS[attempt - 1])

        logger.error(f"Giving up on {url} after {self.MAX_ATTEMPTS} attempts")
        return None

    def read_attack_damage(self, damage_str):
        pattern = r"(?P<amount>\d+)(?P<suffix>\W?)"
        match = re.match(pattern, damage_str)

        if match:
            amount = int(match.group("amount"))
            suffix = match.group("suffix")
            return {"amount": amount, "suffix": suffix}
        else:
            return None

    def get_downloaded_set_list(self, lang="en"):
        downloaded_list = set()
        with open(f"logs/scraped_{lang}_set_list.txt", "r") as file:
            for line in file:
                downloaded_list.add(line.strip())
        return downloaded_list

    def get_downloaded_id_list(self, lang="jp"):
        downloaded_list = set()
        with open(f"logs/scraped_{lang}_id_list.txt", "r") as file:
            for line in file:
                downloaded_list.add(int(line.strip()))
        return downloaded_list

    def save_list_to_file(self, array, output_file):
        file_exists = True
        known_list = set()
        try:
            with open(output_file, "r") as file:
                for line in file:
                    known_list.add(line.strip())
        except FileNotFoundError:
            file_exists = False

        mode = "a" if file_exists else "w"
        with open(output_file, mode) as file:
            for card in array:
                if card not in known_list:
                    file.write(str(card) + "\n")

    def upadte_readme(self, last_id, lang="jp"):
        readme_path = "README.md"

        with open(readme_path, "r") as file:
            lines = file.readlines()

        if lang == "jp":
            date_pattern = re.compile(r"Last jp downloaded time: .+")
            card_id_pattern = re.compile(r"Last jp downloaded card_id: \d+")
        elif lang == "en":
            date_pattern = re.compile(r"Last en downloaded time: .+")
            card_id_pattern = re.compile(r"Last en downloaded card_id: \S+")
        elif lang == "tc":
            date_pattern = re.compile(r"Last tc downloaded time: .+")
            card_id_pattern = re.compile(r"Last tc downloaded card_id: \S+")
        elif lang == "pocket":
            date_pattern = re.compile(r"Last pocket downloaded time: .+")
            card_id_pattern = re.compile(r"Last pocket downloaded card_id: \S+")

        current_date = datetime.now().strftime("%B %d, %Y")

        with open(readme_path, "w") as file:
            for line in lines:
                if date_pattern.search(line):
                    line = f"\t\t- Last {lang} downloaded time: {current_date}\n"
                elif card_id_pattern.search(line):
                    line = f"\t\t- Last {lang} downloaded card_id: {last_id}\n"
                file.write(line)
