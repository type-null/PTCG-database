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

    def get_content(self, url):
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:68.0) Gecko/20100101 Firefox/68.0"
        )
        response = requests.get(url, headers={"User-Agent": user_agent})
        if response.status_code == 200:
            logging.debug(f"Got content from {url}")
            return response.content.decode("utf-8")
        else:
            logging.warning(f"Fail to get card {url}")
            logging.warning(f"Error code: {response.status_code}")
            return [url, response.status_code]

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
