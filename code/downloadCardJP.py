"""
    Scrape card info from pokemon-card.com

    A shortcut for `code/updateDatabase.py jp`; every option of that script
    works here too.

    April 23, 2024 by Weihang
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import updateDatabase

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "jp", *sys.argv[1:]]
    updateDatabase.main()
