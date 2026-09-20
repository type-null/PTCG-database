"""
    Download card info from pkmncards.com

    A shortcut for `code/updateDatabase.py en`; every option of that script
    works here too.

    May 29, 2024 by Weihang
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import updateDatabase

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "en", *sys.argv[1:]]
    updateDatabase.main()
