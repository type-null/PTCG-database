"""
    Scrape card info

    April 23, 2024 by Weihang
"""

import bs4
import sys
import requests
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
            logging.warn(f"Fail to get card {url}")
            logging.warn(f"Error code: {response.status_code}")
            return [url, response.status_code]
